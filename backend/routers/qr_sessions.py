import io
import json

import qrcode
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse

from models.schemas import (
    QRSessionEndRequest,
    QRSessionResponse,
    QRSessionStart,
    QRValidateRequest,
    QRValidateResponse,
)
from services import qr_service

router = APIRouter(prefix="/qr-sessions", tags=["qr-sessions"])


@router.post("/start", response_model=QRSessionResponse)
async def start_session(data: QRSessionStart):
    """Teacher opens a class session; any previous session is auto-closed."""
    if not data.class_name.strip():
        raise HTTPException(status_code=400, detail="class_name is required")
    session = await qr_service.create_session(
        class_name=data.class_name.strip(),
        room=(data.room or None),
        created_by=data.created_by,
    )
    return session


@router.post("/end")
async def end_session(data: QRSessionEndRequest | None = None):
    """Teacher closes the class session; QR check-ins are refused afterwards."""
    session_id = data.session_id if data else None
    session = await qr_service.end_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active class session")
    return {
        "session_id": session["id"],
        "class_name": session["class_name"],
        "room": session["room"],
        "started_at": session["started_at"],
        "ended_at": session["ended_at"],
        "total_attendance": session["total_attendance"],
    }


@router.get("/active")
async def get_active_session():
    """Active session info for the dashboard (rotates the token if stale)."""
    session = await qr_service.current_token(rotate=True)
    if not session:
        return JSONResponse(content={"active": False})
    return {
        "active": True,
        "session_id": session["id"],
        "token": session["token"],
        "class_name": session["class_name"],
        "room": session["room"],
        "created_by": session["created_by"],
        "started_at": session["started_at"],
    }


@router.get("/active/token")
async def get_active_token():
    """Lightweight poll for the current rotating token."""
    session = await qr_service.current_token(rotate=True)
    if not session:
        return JSONResponse(content={"active": False, "token": None})
    return {
        "active": True,
        "session_id": session["id"],
        "token": session["token"],
        "class_name": session["class_name"],
        "room": session["room"],
    }


@router.get("/active/qr.png")
async def get_active_qr_png():
    """QR code image (PNG) of the current token, for the classroom LCD."""
    session = await qr_service.current_token(rotate=True)
    if not session:
        raise HTTPException(status_code=404, detail="No active class session")
    payload = json.dumps({
        "session_id": session["id"],
        "token": session["token"],
        "class_name": session["class_name"],
    })
    image = qrcode.make(payload, box_size=12, border=2)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/validate", response_model=QRValidateResponse)
async def validate_token(data: QRValidateRequest):
    """Mobile app validates a scanned QR token before opening the camera."""
    return await qr_service.validate_token(data.token)