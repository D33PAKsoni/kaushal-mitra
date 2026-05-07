"""
KaushalMitra Backend — Day 3
Added: scoring router, updated admin router
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routers import asr, session, agent, scoring
from routers import admin as admin_router
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 KaushalMitra backend starting — Day 3")
    print(f"   Groq: {'✅' if settings.GROQ_API_KEY else '❌'}")
    print(f"   Supabase: {'✅' if settings.SUPABASE_URL else '⚠️  seed data mode'}")
    print(f"   Redis: {'✅' if settings.UPSTASH_REDIS_REST_URL else '❌'}")
    yield
    print("👋 Shutting down...")


app = FastAPI(
    title="KaushalMitra API",
    description="AI SkillFit: Video Assessment for Workforce Fitment — EDCS Karnataka",
    version="3.0.0",
    lifespan=lifespan,
)

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

app.include_router(asr.router,          prefix="/asr",     tags=["ASR"])
app.include_router(session.router,      prefix="/session", tags=["Session"])
app.include_router(agent.router,        prefix="/agent",   tags=["Agent"])
app.include_router(scoring.router,      prefix="/score",   tags=["Scoring"])
app.include_router(admin_router.router, prefix="/admin",   tags=["Admin"])


@app.get("/")
async def root():
    return {
        "service": "KaushalMitra API",
        "version": "3.0.0",
        "day": 3,
        "tagline": "ಕೌಶಲ ಮಿತ್ರ — Skill Companion",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
