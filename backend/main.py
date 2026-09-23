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
    allow_origins=["*"],
    allow_credentials=True,
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


@app.get("/dashboard", include_in_schema=False)
async def dashboard():
    return FileResponse(DASHBOARD_FILE, media_type="text/html")
