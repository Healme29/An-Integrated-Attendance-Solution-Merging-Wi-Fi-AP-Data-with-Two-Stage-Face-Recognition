"""Capture-replay guard for check-in photos (first line of defense).

Stores a per-day SHA-256 fingerprint of every ACCEPTED check-in photo and
rejects the two easiest cheating attempts without touching any recognition
logic or attendance rule:

  - two different students submitting the exact same image file:
    one person checked in twice, under two NIMs (identity swap);
  - the same exact file being submitted again on the same day
    (copy-forward of a saved selfie instead of looking into the camera).

Cross-day reuse or a genuinely re-captured (re-encoded) frame always passes:
the guard compares file bytes, so every live capture is a new fingerprint.

Guard state is process-local by design — attendance rows in the database
remain the source of truth; this is only a lightweight tripwire that resets
when the server restarts (a known limitation, acceptable for the pilot).
"""
import hashlib

from config import now_local

# sha256 -> (date, student_id, schedule_id, check_type)
_used: dict[str, tuple] = {}


def fingerprint(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def assert_not_replayed(sha: str, student_id: int) -> None:
    """Reject an exact image file already accepted today.

    Start and end attendance must use two fresh captures, so reuse is blocked
    for the same student as well as for identity swaps between students.
    """
    record = _used.get(sha)
    if record and record[0] == now_local().strftime("%Y-%m-%d"):
        raise ValueError("photo_replay")


def record(sha: str, student_id: int, schedule_id: int, check_type: str) -> None:
    """Remember an accepted capture (called only after a successful check-in)."""
    _used[sha] = (now_local().strftime("%Y-%m-%d"), student_id, schedule_id, check_type)


def reset() -> None:
    """Testing helper."""
    _used.clear()


def used_count() -> int:
    return len(_used)
