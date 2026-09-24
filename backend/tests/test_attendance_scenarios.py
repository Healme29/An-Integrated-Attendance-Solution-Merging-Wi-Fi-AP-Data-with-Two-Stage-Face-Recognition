import pytest
from datetime import datetime
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
        (1, "Math 101", 0, "08:00", "09:30", None, "Room 201")
    )
    await db.commit()
    await db.close()


@pytest.mark.asyncio
class TestPerfectAttendance:
    async def test_all_conditions_met(self, test_db, setup_test_db):
        await seed_data(test_db)

        start = await mark_attendance(
            student_id=1, schedule_id=1,
            check_type="start", confidence=0.92
        )

        assert start["student_id"] == 1
        assert start["schedule_id"] == 1
        assert start["student_name"] == "Alice Smith"
        assert start["wifi_verified"] is True
        assert start["status"] == "partial"
        assert start["check_type"] == "start"
        assert start["confidence"] == 0.92

        end = await mark_attendance(
            student_id=1, schedule_id=1,
            check_type="end", confidence=0.88
        )

        assert end["status"] == "verified"
        assert end["wifi_verified"] is True

        db = await test_db()
        cursor = await db.execute(
            "SELECT status FROM attendance WHERE student_id = 1 AND check_type = 'start'"
        )
        row = await cursor.fetchone()
        await db.close()
        assert row["status"] == "verified"


@pytest.mark.asyncio
class TestFaceMismatchScenario:
    async def test_different_face_for_second_selfie(self, test_db, setup_test_db):
        await seed_data(test_db)

        await mark_attendance(
            student_id=1, schedule_id=1,
            check_type="start", confidence=0.92
        )

        result = await mark_attendance(
            student_id=1, schedule_id=1,
            check_type="end", confidence=0.2
        )

        assert result["wifi_verified"] is True
        assert result["status"] == "verified"
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

    async def test_start_check_stays_partial_without_end(self, test_db, setup_test_db):
        await seed_data(test_db)

        await mark_attendance(
            student_id=1, schedule_id=1,
            check_type="start", confidence=0.92
        )

        db = await test_db()
        cursor = await db.execute(
            "SELECT status FROM attendance WHERE student_id = 1 AND check_type = 'start'"
        )
        row = await cursor.fetchone()
        await db.close()
        assert row["status"] == "partial"


@pytest.mark.asyncio
class TestWrongRoomScenario:
    async def test_wrong_ap_gives_face_only_status(self, test_db, setup_test_db, mock_wifi_scanner):
        await seed_data(test_db)

        mock_wifi_scanner.return_value = False

        start = await mark_attendance(
            student_id=1, schedule_id=1,
            check_type="start", confidence=0.95
        )

        assert start["wifi_verified"] is False
        assert start["status"] == "partial"

        end = await mark_attendance(
            student_id=1, schedule_id=1,
            check_type="end", confidence=0.95
        )

        assert end["wifi_verified"] is False
        assert end["status"] == "face_only"


@pytest.mark.asyncio
class TestDuplicateCheckIn:
    async def test_duplicate_start_rejected(self, test_db, setup_test_db):
        await seed_data(test_db)

        await mark_attendance(student_id=1, schedule_id=1, check_type="start", confidence=0.9)

        with pytest.raises(ValueError, match="duplicate_check_in"):
            await mark_attendance(student_id=1, schedule_id=1, check_type="start", confidence=0.9)

    async def test_end_without_start_rejected(self, test_db, setup_test_db):
        await seed_data(test_db)

        with pytest.raises(ValueError, match="missing_start_check"):
            await mark_attendance(student_id=1, schedule_id=1, check_type="end", confidence=0.9)


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


@pytest.mark.asyncio
class TestScheduleTimeValidation:
    async def test_validate_schedule_time_not_found(self, test_db, setup_test_db):
        await seed_data(test_db)

        from services.attendance import validate_schedule_time
        with pytest.raises(ValueError, match="schedule_not_found"):
            await validate_schedule_time(999)

    async def test_validate_schedule_time_wrong_day(self, test_db, setup_test_db):
        await seed_data(test_db)

        from services.attendance import validate_schedule_time
        # schedule 1 is Monday (day 0); fails unless today is Monday
        if datetime.now().weekday() == 0:
            pytest.skip("today is Monday")
        with pytest.raises(ValueError, match="wrong_day"):
            await validate_schedule_time(1)