from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models.database import init_db
from routers import students, faces, attendance, schedules, wifi


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
    return {"message": "Face Attendance API is running", "docs": "/docs"}
