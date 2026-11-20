from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ---------------------------------------------------------------------------
# Teacher auth (S5 — simple token/session)
# ---------------------------------------------------------------------------

class TeacherLogin(BaseModel):
    username: str
    password: str


class TeacherLoginResponse(BaseModel):
    token: str
    teacher: str


class TeacherVerify(BaseModel):
    token: str


# ---------------------------------------------------------------------------
# Classes & Enrollment (S3)
# ---------------------------------------------------------------------------

class ClassCreate(BaseModel):
    class_name: str
    room: Optional[str] = None


class ClassResponse(BaseModel):
    id: int
    class_name: str
    room: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ClassStudentAdd(BaseModel):
    student_id: int


class ClassStudentResponse(BaseModel):
    id: int
    student_id: int
    student_name: str
    student_nim: str
    added_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------

class StudentCreate(BaseModel):
    name: str
    nim: str
    mac_address: Optional[str] = None  # kept for backward compatibility, unused


class StudentResponse(BaseModel):
    id: int
    name: str
    nim: str
    mac_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class FaceEnrollRequest(BaseModel):
    student_id: int


class FaceEnrollResponse(BaseModel):
    message: str
    student_id: int
    face_count: int
    faces_detected: int = 0
    total_embeddings: int = 0


class QRSessionStart(BaseModel):
    class_id: int
    class_name: Optional[str] = None  # legacy fallback; class_id is canonical
    room: Optional[str] = None
    created_by: Optional[str] = None


class QRSessionResponse(BaseModel):
    id: int
    token: str
    class_name: str
    room: Optional[str] = None
    created_by: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    is_active: bool
    phase: Optional[str] = "start"
    class_id: Optional[int] = None
    spot_round: int = 0

    class Config:
        from_attributes = True


class QRSessionPhase(BaseModel):
    phase: str  # 'start' | 'end' | 'closed'


class QRSessionEndRequest(BaseModel):
    session_id: int


class QRValidateRequest(BaseModel):
    token: str


class QRValidateResponse(BaseModel):
    valid: bool
    session_id: Optional[int] = None
    class_name: Optional[str] = None
    room: Optional[str] = None
    message: Optional[str] = None
    phase: Optional[str] = None
    spot_round: int = 0


class AttendanceResponse(BaseModel):
    id: int
    student_id: int
    student_name: Optional[str] = None
    qr_session_id: int
    confidence: Optional[float]
    ip_address: Optional[str] = None
    status: str
    timestamp: datetime
    class_name: Optional[str] = None
    room: Optional[str] = None
    # Raw YOLO box count at check-in. Kept for audit: a value > 1 means the
    # detector saw more than one box, even when it was one face duplicated.
    faces_detected: int = 0
    check_type: Optional[str] = None
    spot_round: int = 0

    class Config:
        from_attributes = True


class RecognizeResponse(BaseModel):
    recognized: bool
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# Roster: one row per student in a class (S3)
# ---------------------------------------------------------------------------

class RosterStudent(BaseModel):
    id: int
    student_id: int
    student_name: str
    student_nim: str
    status: str = "pending"      # pending / partial / verified / absent
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    start_confidence: Optional[float] = None
    end_confidence: Optional[float] = None
    faces_detected_start: int = 0
    faces_detected_end: int = 0
    manual: bool = False
    spot_checks: int = 0


# ---------------------------------------------------------------------------
# Manual attendance (S6)
# ---------------------------------------------------------------------------

class ManualAttendanceRequest(BaseModel):
    student_id: int
    qr_session_id: int
    reason: Optional[str] = None