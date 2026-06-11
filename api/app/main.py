"""고고조 AI 러닝 코치 v2 — FastAPI 엔트리포인트."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import SessionLocal, init_db
from .routers import (
    availability, daily_plans, integrations, profile, today, weeks, workout_logs,
)
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with SessionLocal() as db:
        await seed(db)
    yield


app = FastAPI(title="Running Coach API", version="2.0.0", lifespan=lifespan)

# PWA(같은 오리진/nginx 프록시) 외에 Vite dev 서버·Expo에서 직접 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={
        "error": {"code": "INTERNAL", "message": str(exc)},
    })


@app.get("/api/health")
async def health():
    return {"status": "ok"}


app.include_router(profile.router)
app.include_router(availability.router)
app.include_router(today.router)
app.include_router(weeks.router)
app.include_router(daily_plans.router)
app.include_router(workout_logs.router)
app.include_router(integrations.router)
