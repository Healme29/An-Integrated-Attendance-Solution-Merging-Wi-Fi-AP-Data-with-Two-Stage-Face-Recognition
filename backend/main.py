import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Allow both `uvicorn backend.main:app` (repo root) and
# `cd backend && uvicorn main:app` to resolve the top-level imports below.
_BACKEND_DIR = str(Path(__file__).resolve().parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from models.database import init_db
from routers import students, faces, attendance, schedules, wifi
from config import CORS_ORIGINS

DASHBOARD_FILE = Path(__file__).resolve().parent / "static" / "dashboard.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Face Attendance API",
    description="Integrated attendance system with face recognition and Wi-Fi AP verification",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials="*" not in CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students.router)
app.include_router(faces.router)
app.include_router(attendance.router)
app.include_router(schedules.router)
app.include_router(wifi.router)


@app.get("/")
async def root():
    return {"message": "Face Attendance API is running", "docs": "/docs", "dashboard": "/dashboard"}


@app.get("/health")
async def health():
    from fastapi.responses import JSONResponse
    from models.database import get_db

    try:
        db = await get_db()
        try:
            cursor = await db.execute("SELECT 1")
            await cursor.fetchone()
        finally:
            await db.close()
        return {"status": "ok", "database": "ok"}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": f"{type(exc).__name__}: {exc}"}
        )


@app.get("/dashboard", include_in_schema=False)
async def dashboard():
    return FileResponse(DASHBOARD_FILE, media_type="text/html")
