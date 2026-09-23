from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StudentCreate(BaseModel):
    name: str
    nim: str
    mac_address: Optional[str] = None


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


class AttendanceRequest(BaseModel):
    student_id: int
    schedule_id: int
    check_type: str


class AttendanceResponse(BaseModel):
    id: int
    student_id: int
    student_name: Optional[str] = None
    schedule_id: int
    check_type: str
    confidence: Optional[float]
    wifi_verified: bool
    status: str
    timestamp: datetime
    class_name: Optional[str] = None

    class Config:
        from_attributes = True


class RecognizeResponse(BaseModel):
    recognized: bool
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    confidence: float = 0.0


class ScheduleCreate(BaseModel):
    class_name: str
    day_of_week: int
    start_time: str
    end_time: str
    ap_bssid: Optional[str] = None
    room: Optional[str] = None


class ScheduleResponse(BaseModel):
    id: int
    class_name: str
    day_of_week: int
    start_time: str
    end_time: str
    ap_bssid: Optional[str]
    room: Optional[str]

    class Config:
        from_attributes = True


class WifiDevice(BaseModel):
    ip: str
    mac: str


class WifiScanResponse(BaseModel):
    devices: list[WifiDevice]
    subnet: str
    timestamp: datetime
