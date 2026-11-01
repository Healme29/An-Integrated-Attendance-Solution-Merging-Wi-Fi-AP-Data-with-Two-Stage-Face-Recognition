"""Identity binding at check-in and single-face enrollment (decision D-003).

The hole these tests lock down: `POST /attendance/check` used to decide the
student purely from the face in the photo, so a friend in front of the camera
was recorded (and could be granted attendance) instead of the logged-in
student. Enrollment used to store every face in the frame, so a friend could
end up inside another student's profile.
"""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

import numpy as np
import pytest

from services.attendance import recognize_face
from services.face_detection import dedupe_faces, distinct_people


def face(bbox, confidence=0.9):
    return {"bbox": bbox, "confidence": confidence, "crop": None}


def add_student(client, name, nim, mac=None):
    response = client.post("/students/", json={"name": name, "nim": nim, "mac_address": mac})
    assert response.status_code == 200


def active_schedule_payload():
    now = datetime.now()
    return {
        "class_name": "Math 101",
        "day_of_week": now.weekday(),
        "start_time": (now - timedelta(minutes=5)).strftime("%H:%M"),
        "end_time": (now + timedelta(minutes=5)).strftime("%H:%M"),
        "room": "Room 201",
    }


def count_rows(test_db, table, where="", params=()):
    async def _count():
        db = await test_db()
        cursor = await db.execute(f"SELECT COUNT(*) FROM {table} {where}", params)
        value = (await cursor.fetchone())[0]
        await db.close()
        return value

    return asyncio.run(_count())


def post_check(client, student_id, fake_jpeg, schedule_id=1, check_type="start"):
    return client.post(
        f"/attendance/check?student_id={student_id}&schedule_id={schedule_id}"
        f"&check_type={check_type}",
        files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")},
    )


class TestCheckInIdentityBinding:
    def test_face_of_another_student_is_rejected(
        self, client, setup_test_db, test_db, fake_jpeg, mock_face_detection
    ):
        # Both students are enrolled (embeddings are mocked), but the face in
        # the photo matches Alice while Bob's account is signed in.
        add_student(client, "Alice", "12345", "aa:bb:cc:dd:ee:ff")
        add_student(client, "Bob", "67890", "11:22:33:44:55:66")
        client.post("/schedules/", json=active_schedule_payload())

        response = post_check(client, student_id=2, fake_jpeg=fake_jpeg)

        assert response.status_code == 403
        assert "Identity mismatch" in response.json()["detail"]
        assert count_rows(test_db, "attendance") == 0

    def test_unknown_student_is_rejected(
        self, client, setup_test_db, test_db, fake_jpeg
    ):
        client.post("/schedules/", json=active_schedule_payload())

        response = post_check(client, student_id=999, fake_jpeg=fake_jpeg)

        assert response.status_code == 404
        assert count_rows(test_db, "attendance") == 0

    def test_matching_face_records_attendance(
        self, client, setup_test_db, test_db, fake_jpeg
    ):
        add_student(client, "Alice", "12345", "aa:bb:cc:dd:ee:ff")
        client.post("/schedules/", json=active_schedule_payload())

        response = post_check(client, student_id=1, fake_jpeg=fake_jpeg)

        assert response.status_code == 200
        data = response.json()
        assert data["student_id"] == 1
        assert data["faces_detected"] == 1

        async def _row():
            db = await test_db()
            cursor = await db.execute("SELECT student_id, faces_detected FROM attendance")
            row = await cursor.fetchone()
            await db.close()
            return row

        row = asyncio.run(_row())
        assert row["student_id"] == 1
        assert row["faces_detected"] == 1

    def test_two_people_in_the_photo_are_rejected(
        self, client, setup_test_db, test_db, fake_jpeg, mock_face_detection
    ):
        _, m2, m3 = mock_face_detection
        # Two clearly different people (same size, non-overlapping boxes).
        two_people = [face((10, 10, 210, 210)), face((300, 10, 500, 210))]
        m2.return_value = two_people
        m3.return_value = two_people
        add_student(client, "Alice", "12345", "aa:bb:cc:dd:ee:ff")
        client.post("/schedules/", json=active_schedule_payload())

        response = post_check(client, student_id=1, fake_jpeg=fake_jpeg)

        assert response.status_code == 400
        assert "Multiple faces" in response.json()["detail"]
        assert count_rows(test_db, "attendance") == 0

    def test_nested_duplicate_boxes_are_one_person(
        self, client, setup_test_db, test_db, fake_jpeg, mock_face_detection
    ):
        _, m2, m3 = mock_face_detection
        # Two boxes for the same face: the smaller one is nested in the larger.
        duplicates = [face((10, 10, 210, 210), 0.62), face((30, 30, 190, 190), 0.95)]
        m2.return_value = duplicates
        m3.return_value = duplicates
        add_student(client, "Alice", "12345", "aa:bb:cc:dd:ee:ff")
        client.post("/schedules/", json=active_schedule_payload())

        response = post_check(client, student_id=1, fake_jpeg=fake_jpeg)

        assert response.status_code == 200
        # Both raw boxes are reported for audit, but only one person is used.
        assert response.json()["faces_detected"] == 2
        assert count_rows(test_db, "attendance") == 1

    def test_background_face_does_not_block_a_selfie(
        self, client, setup_test_db, test_db, fake_jpeg, mock_face_detection
    ):
        _, m2, m3 = mock_face_detection
        # A tiny face far behind (1% of the primary area) is not a second person.
        background = [face((10, 10, 210, 210)), face((300, 10, 320, 30))]
        m2.return_value = background
        m3.return_value = background
        add_student(client, "Alice", "12345", "aa:bb:cc:dd:ee:ff")
        client.post("/schedules/", json=active_schedule_payload())

        response = post_check(client, student_id=1, fake_jpeg=fake_jpeg)

        assert response.status_code == 200


@pytest.mark.asyncio
class TestPrimaryFaceSelection:
    async def test_largest_face_is_used_not_the_most_confident(
        self, setup_test_db, test_db, fake_jpeg, mock_face_detection
    ):
        _, _, m3 = mock_face_detection
        # The person taking the selfie is close to the camera (large box) but
        # the detector is more confident about a small object in the background.
        m3.return_value = [
            face((10, 10, 210, 210), 0.55),
            face((300, 10, 320, 30), 0.99),
        ]
        db = await test_db()
        await db.execute(
            "INSERT INTO students (id, name, nim, mac_address) VALUES (?, ?, ?, ?)",
            (1, "Alice", "12345", "aa:bb:cc:dd:ee:ff"),
        )
        await db.commit()
        await db.close()

        with patch("services.attendance.get_embedding", return_value=np.zeros(512, dtype=np.float32)) as emb:
            result = await recognize_face(fake_jpeg)

        assert result["recognized"] is True
        assert result["faces_detected"] == 2
        assert emb.call_args[0][1] == (10, 10, 210, 210)


class TestEnrollmentSingleFace:
    def test_two_people_are_rejected(
        self, client, setup_test_db, test_db, fake_jpeg, mock_face_detection
    ):
        _, m2, _ = mock_face_detection
        m2.return_value = [face((10, 10, 210, 210)), face((300, 10, 500, 210))]
        add_student(client, "Alice", "12345")

        response = client.post(
            "/faces/enroll?student_id=1",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")},
        )

        assert response.status_code == 400
        assert "Multiple faces" in response.json()["detail"]
        assert count_rows(test_db, "faces") == 0

    def test_nested_duplicate_boxes_store_one_embedding(
        self, client, setup_test_db, test_db, fake_jpeg, mock_face_detection
    ):
        _, m2, _ = mock_face_detection
        m2.return_value = [face((10, 10, 210, 210), 0.62), face((30, 30, 190, 190), 0.95)]
        add_student(client, "Alice", "12345")

        response = client.post(
            "/faces/enroll?student_id=1",
            files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["face_count"] == 1
        assert data["faces_detected"] == 2
        assert count_rows(test_db, "faces") == 1

    def test_only_the_largest_face_is_enrolled(
        self, client, setup_test_db, test_db, fake_jpeg, mock_face_detection
    ):
        _, m2, _ = mock_face_detection
        m2.return_value = [face((10, 10, 210, 210)), face((300, 10, 320, 30))]
        add_student(client, "Alice", "12345")

        with patch("routers.faces.get_embedding", return_value=np.zeros(512, dtype=np.float32)) as emb:
            response = client.post(
                "/faces/enroll?student_id=1",
                files={"file": ("selfie.jpg", fake_jpeg, "image/jpeg")},
            )

        assert response.status_code == 200
        assert response.json()["face_count"] == 1
        assert emb.call_args[0][1] == (10, 10, 210, 210)
        assert count_rows(test_db, "faces") == 1


class TestFaceBoxHelpers:
    def test_dedupe_keeps_the_largest_box(self):
        boxes = [face((10, 10, 210, 210)), face((30, 30, 190, 190))]

        kept = dedupe_faces(boxes)

        assert len(kept) == 1
        assert kept[0]["bbox"] == (10, 10, 210, 210)

    def test_distinct_people_ignores_background_faces(self):
        boxes = dedupe_faces([face((10, 10, 210, 210)), face((300, 10, 320, 30))])

        assert len(distinct_people(boxes)) == 1

    def test_distinct_people_keeps_a_real_second_person(self):
        boxes = dedupe_faces([face((10, 10, 210, 210)), face((300, 10, 500, 210))])

        assert len(distinct_people(boxes)) == 2
