import io
import json

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse

from models.schemas import (
    QRSessionEndRequest,
    QRSessionPhase,
    QRSessionResponse,
    QRSessionStart,
    QRValidateRequest,
    QRValidateResponse,
)
from routers.teachers import require_teacher
from services import qr_service

router = APIRouter(prefix="/qr-sessions", tags=["qr-sessions"])


@router.post("/start", response_model=QRSessionResponse)
async def start_session(data: QRSessionStart, teacher: str = Depends(require_teacher)):
    try:
        return await qr_service.create_session(data.class_id, created_by=teacher)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/phase")
async def set_phase(data: QRSessionPhase, teacher: str = Depends(require_teacher)):
    session = await qr_service.get_active_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active class session")
    try:
        updated = await qr_service.set_phase(session["id"], data.phase, teacher)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=404, detail="No active class session")
    return {
        "session_id": updated["id"],
        "phase": updated["phase"],
        "spot_round": updated.get("spot_round", 0),
        "token": updated["token"],
        "class_name": updated["class_name"],
        "room": updated["room"],
    }


@router.post("/end")
async def end_session(data: QRSessionEndRequest | None = None, teacher: str = Depends(require_teacher)):
    session = await qr_service.end_session(data.session_id if data else None)
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


@router.get("/history")
async def session_history(limit: int = 10, teacher: str = Depends(require_teacher)):
    return await qr_service.list_sessions(limit)


@router.get("/active")
async def get_active_session():
    session = await qr_service.current_token(rotate=True)
    if not session:
        return JSONResponse(content={"active": False})
    return {
        "active": True,
        "session_id": session["id"],
        "class_id": session.get("class_id"),
        "token": session["token"],
        "class_name": session["class_name"],
        "room": session["room"],
        "created_by": session["created_by"],
        "started_at": session["started_at"],
        "phase": session.get("phase", "start"),
        "spot_round": session.get("spot_round", 0),
    }


@router.get("/active/token")
async def get_active_token():
    session = await qr_service.current_token(rotate=True)
    if not session:
        return JSONResponse(content={"active": False, "token": None})
    return {
        "active": True,
        "session_id": session["id"],
        "token": session["token"],
        "class_name": session["class_name"],
        "room": session["room"],
        "phase": session.get("phase", "start"),
        "spot_round": session.get("spot_round", 0),
    }


@router.get("/active/qr.png")
async def get_active_qr_png():
    session = await qr_service.current_token(rotate=True)
    if not session:
        raise HTTPException(status_code=404, detail="No active class session")
    payload = json.dumps({
        "session_id": session["id"],
        "token": session["token"],
        "class_name": session["class_name"],
        "phase": session.get("phase", "start"),
        "spot_round": session.get("spot_round", 0),
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
    return await qr_service.validate_token(data.token)
