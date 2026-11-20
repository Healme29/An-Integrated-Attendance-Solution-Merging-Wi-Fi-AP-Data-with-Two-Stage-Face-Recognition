"""Small bearer-token teacher login used by dashboard actions.

This is intentionally simple for the local demo. Set TEACHER_USERNAME and
TEACHER_PASSWORD in the environment before a real deployment.
"""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import TEACHER_PASSWORD, TEACHER_TOKEN_HOURS, TEACHER_USERNAME
from models.schemas import TeacherLogin, TeacherLoginResponse, TeacherVerify

router = APIRouter(prefix="/teachers", tags=["teachers"])
security = HTTPBearer(auto_error=False)
_tokens: dict[str, dict] = {}


def _valid_teacher(token: str | None) -> str | None:
    info = _tokens.get(token or "")
    if not info:
        return None
    if datetime.now(timezone.utc) > info["expires_at"]:
        _tokens.pop(token, None)
        return None
    return info["username"]


async def require_teacher(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """FastAPI dependency protecting teacher-only endpoints."""
    teacher = _valid_teacher(credentials.credentials if credentials else None)
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Teacher login required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return teacher


@router.post("/login", response_model=TeacherLoginResponse)
async def login(data: TeacherLogin):
    if not secrets.compare_digest(data.username, TEACHER_USERNAME) or not secrets.compare_digest(
        data.password, TEACHER_PASSWORD
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = secrets.token_urlsafe(32)
    _tokens[token] = {
        "username": data.username,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=TEACHER_TOKEN_HOURS),
    }
    return TeacherLoginResponse(token=token, teacher=data.username)


@router.post("/verify")
async def verify(data: TeacherVerify):
    teacher = _valid_teacher(data.token)
    return {"valid": teacher is not None, "teacher": teacher}


@router.post("/logout")
async def logout(teacher: str = Depends(require_teacher), credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if credentials:
        _tokens.pop(credentials.credentials, None)
    return {"message": "Logged out"}
