from pydantic import BaseModel
from typing import Optional
from datetime import datetime


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
    class_name: str
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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class RecognizeResponse(BaseModel):
    recognized: bool
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    confidence: float = 0.0