"""
KaushalMitra Backend — FastAPI Entry Point
Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routers import asr, session, admin
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("🚀 KaushalMitra backend starting...")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   ASR endpoint: {settings.HF_INDIC_WHISPER_URL[:50]}...")
    yield
    print("👋 KaushalMitra backend shutting down...")


app = FastAPI(
    title="KaushalMitra API",
    description="AI SkillFit: Video Assessment for Workforce Fitment — EDCS Karnataka",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────
# Allow Vercel frontend + localhost dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
        settings.FRONTEND_URL or "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────
app.include_router(asr.router, prefix="/asr", tags=["ASR"])
app.include_router(session.router, prefix="/session", tags=["Session"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/")
async def root():
    return {
        "service": "KaushalMitra API",
        "status": "running",
        "version": "1.0.0",
        "tagline": "ಕೌಶಲ ಮಿತ್ರ — Skill Companion",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
