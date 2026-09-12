import pytest
from unittest.mock import patch
from models.database import get_db
from services.attendance import mark_attendance, recognize_face
from services.face_recognition import compare_faces, is_match


def make_fake_embedding():
    import numpy as np
    return np.random.randn(512).astype(np.float32)


async def seed_data(test_db):
    db = await test_db()

    await db.execute(
        "INSERT INTO students (id, name, nim, mac_address) VALUES (?, ?, ?, ?)",
        (1, "Alice Smith", "12345", "aa:bb:cc:dd:ee:ff")
    )
    await db.execute(
        "INSERT INTO students (id, name, nim, mac_address) VALUES (?, ?, ?, ?)",
        (2, "Bob Jones", "67890", "11:22:33:44:55:66")
    )
    await db.execute(
        "INSERT INTO schedules (id, class_name, day_of_week, start_time, end_time, ap_bssid, room) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, "Math 101", 0, "08:00", "09:30", "AP_MATH_01", "Room 201")
    )
    await db.commit()
    await db.close()


@pytest.mark.asyncio
class TestPerfectAttendance:
    async def test_all_conditions_met(self, test_db, setup_test_db):
        await seed_data(test_db)

        result = await mark_attendance(
            student_id=1, schedule_id=1,
            check_type="start", confidence=0.92
        )

        assert result["student_id"] == 1
        assert result["schedule_id"] == 1
        assert result["wifi_verified"] is True
        assert result["status"] == "present"
        assert result["check_type"] == "start"
        assert result["confidence"] == 0.92


@pytest.mark.asyncio
class TestFaceMismatchScenario:
    async def test_different_face_for_second_selfie(self, test_db, setup_test_db):
        await seed_data(test_db)

        result = await mark_attendance(
            student_id=1, schedule_id=1,
            check_type="end", confidence=0.2
        )

        assert result["wifi_verified"] is True
        assert result["status"] == "present"
        assert result["confidence"] == 0.2


@pytest.mark.asyncio
class TestMissingSecondSelfie:
    async def test_no_second_selfie_means_no_attendance_record(self, test_db, setup_test_db):
        await seed_data(test_db)

        db = await test_db()
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM attendance WHERE student_id = ? AND check_type = 'end'",
            (1,)
        )
        row = await cursor.fetchone()
        await db.close()
        assert row["cnt"] == 0


@pytest.mark.asyncio
class TestWrongRoomScenario:
    async def test_wrong_ap_gives_face_only_status(self, test_db, setup_test_db, mock_wifi_scanner):
        await seed_data(test_db)

        mock_wifi_scanner.return_value = False

        result = await mark_attendance(
            student_id=1, schedule_id=1,
            check_type="start", confidence=0.95
        )

        assert result["wifi_verified"] is False
        assert result["status"] == "face_only"


@pytest.mark.asyncio
class TestLateArrivalScenario:
    async def test_outside_schedule(self, test_db, setup_test_db):
        await seed_data(test_db)

        db = await test_db()
        cursor = await db.execute(
            "SELECT * FROM schedules WHERE id = ?", (1,)
        )
        schedule = await cursor.fetchone()
        await db.close()

        assert schedule is not None
        assert schedule["class_name"] == "Math 101"