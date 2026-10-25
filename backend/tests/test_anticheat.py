"""Anti-cheat guards:
- one MAC address belongs to exactly one student (no "borrowed device" Wi-Fi),
- a check-in photo file can be accepted at most once per day (replay guard).
"""
from datetime import timedelta

from config import now_local
from services import photo_guard


def create(client, name, nim, mac):
    return client.post("/students/", json={"name": name, "nim": nim, "mac_address": mac})


class TestMacUniqueness:
    def test_create_duplicate_mac_rejected(self, client, setup_test_db):
        assert create(client, "Alice", "1001", "aa:bb:cc:dd:ee:01").status_code == 200
        # Literal-normalized copy (uppercase, dashes) must be caught too.
        response = create(client, "Bob", "1002", "AA-BB-CC-DD-EE-01")
        assert response.status_code == 409
        assert "already registered to Alice" in response.json()["detail"]

    def test_update_mac_to_owned_mac_rejected(self, client, setup_test_db):
        assert create(client, "Alice", "1001", "aa:bb:cc:dd:ee:01").status_code == 200
        assert create(client, "Bob", "1002", "11:22:33:44:55:66").status_code == 200
        response = client.put("/students/2/mac?mac_address=aa%3Abb%3Acc%3Add%3Aee%3A01")
        assert response.status_code == 409

    def test_update_mac_free_mac_ok(self, client, setup_test_db):
        assert create(client, "Alice", "1001", "aa:bb:cc:dd:ee:01").status_code == 200
        response = client.put("/students/1/mac?mac_address=de%3Aad%3Abe%3Aef%3A00%3A02")
        assert response.status_code == 200

    def test_update_mac_missing_student(self, client, setup_test_db):
        response = client.put("/students/999/mac?mac_address=aa:bb:cc:dd:ee:01")
        assert response.status_code == 404

    def test_same_mac_after_owner_deleted_is_free(self, client, setup_test_db):
        assert create(client, "Alice", "1001", "aa:bb:cc:dd:ee:01").status_code == 200
        sid = client.get("/students/", params={"nim": "1001"}).json()[0]["id"]
        client.delete(f"/students/{sid}")
        assert create(client, "Bob", "1002", "aa:bb:cc:dd:ee:01").status_code == 200


class TestPhotoReplayGuard:
    def test_same_file_by_another_student_rejected(self):
        photo_guard.reset()
        sha = photo_guard.fingerprint(b"friend-shared-selfie")
        photo_guard.record(sha, student_id=1, schedule_id=1, check_type="start")
        try:
            photo_guard.assert_not_replayed(sha, student_id=2)
        except ValueError:
            pass
        else:
            raise AssertionError("cross-student reuse must be rejected")

    def test_same_student_same_file_passes(self):
        photo_guard.reset()
        sha = photo_guard.fingerprint(b"my-own-second-stage")
        photo_guard.record(sha, student_id=7, schedule_id=1, check_type="start")
        photo_guard.assert_not_replayed(sha, student_id=7)

    def test_fresh_capture_passes(self):
        photo_guard.reset()
        sha = photo_guard.fingerprint(b"new-frame")
        photo_guard.record(sha, 1, 1, "start")
        photo_guard.assert_not_replayed(photo_guard.fingerprint(b"another-frame"), 2)

    def test_cross_day_reuse_passes(self):
        photo_guard.reset()
        sha = photo_guard.fingerprint(b"yesterday-selfie")
        photo_guard.record(sha, 1, 1, "start")
        yesterday = (now_local() - timedelta(days=1)).strftime("%Y-%m-%d")
        photo_guard._used[sha] = (yesterday, 1, 1, "start")
        photo_guard.assert_not_replayed(sha, 2)
