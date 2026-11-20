"""Teacher authentication (S5).

Minimal demo auth: one fixed teacher account. Issues a bearer token that must
be sent as `Authorization: Bearer <token>` on protected endpoints.

In production, replace with proper password hashing, JWT, and user management.
"""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.schemas import TeacherLogin, TeacherLoginResponse, TeacherVerify

router = APIRouter(prefix="/teachers", tags=["teachers"])

# Demo credentials (change in production)
DEMO_USERNAME = "teacher"
DEMO_PASSWORD = "attendance2026"

# In-memory token store: token -> {username, expires_at}
_tokens: dict[str, dict] = {}

security = HTTPBearer(auto_error=False)


def _make_token() -> str:
    return secrets.token_urlsafe(32)


@router.post("/login", response_model=TeacherLoginResponse)
async def login(data: TeacherLogin):
    if data.username != DEMO_USERNAME or data.password != DEMO_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = _make_token()
    _tokens[token] = {
        "username": data.username,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return TeacherLoginResponse(token=token, teacher=data.username)


@router.post("/verify")
async def verify(data: TeacherVerify):
    info = _tokens.get(data.token)
    if not info:
        return {"valid": False}
    if datetime.now(timezone.utc) > info["expires_at"]:
        _tokens.pop(data.token, None)
        return {"valid": False}
    return {"valid": True, "teacher": info["username"]}


async def get_current_teacher(
    credentials: HTTPAuthorizationCredentials | None = None,
) -> str | None:
    """Return the teacher username if a valid Bearer token is provided, else None."""
    if not credentials:
        return None
    info = _tokens.get(credentials.credentials)
    if not info:
        return None
    if datetime.now(timezone.utc) > info["expires_at"]:
        _tokens.pop(credentials.credentials, None)
        return None
    return info["username"]
