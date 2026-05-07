"""
Session Router — create and manage interview sessions.
Day 3 fix: saves session info to Redis so inline scoring can read
candidate name/district when writing to Supabase.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
from config import settings
import uuid, logging, json

router = APIRouter()
logger = logging.getLogger(__name__)

_sessions: dict = {}  # in-memory fallback


class SessionCreateRequest(BaseModel):
    candidate_name: str
    trade: Literal["electrician", "plumber"]
    district: str
    preferred_language: Literal["kn", "en"] = "kn"


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str
    message_kannada: str = "ಸೆಷನ್ ಪ್ರಾರಂಭವಾಗಿದೆ"


@router.post("/create", response_model=SessionCreateResponse)
async def create_session(body: SessionCreateRequest):
    session_id = str(uuid.uuid4())

    session_data = {
        "session_id": session_id,
        "candidate_name": body.candidate_name,
        "trade": body.trade,
        "district": body.district,
        "preferred_language": body.preferred_language,
        "status": "created",
    }

    # Save to Redis for scoring pipeline to read later
    try:
        from workers.scoring_worker import upstash_set
        await upstash_set(
            f"session_info:{session_id}",
            json.dumps(session_data),
            ex=86400,
        )
        logger.info(f"Session {session_id} saved to Redis")
    except Exception as e:
        logger.warning(f"Redis session save failed: {e}")

    # Also try Supabase
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            from supabase import create_client
            sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            sb.table("sessions").insert(session_data).execute()
        except Exception as e:
            logger.warning(f"Supabase session insert failed: {e}")

    # In-memory fallback
    _sessions[session_id] = session_data

    return SessionCreateResponse(
        session_id=session_id,
        status="created",
        message_kannada="ಸೆಷನ್ ಪ್ರಾರಂಭವಾಗಿದೆ",
    )


@router.post("/{session_id}/integrity")
async def save_integrity_events(session_id: str, payload: dict):
    """Store integrity events (called from frontend at interview end)."""
    try:
        from workers.scoring_worker import upstash_set, upstash_get
        import json
        existing = await upstash_get(f"integrity:{session_id}")
        events = json.loads(existing) if existing else []
        events.extend(payload.get("events", []))
        await upstash_set(f"integrity:{session_id}", json.dumps(events))
    except Exception as e:
        logger.warning(f"Integrity save failed: {e}")
    return {"ok": True}


@router.get("/{session_id}")
async def get_session(session_id: str):
    if session_id in _sessions:
        return _sessions[session_id]

    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            from supabase import create_client
            sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            result = sb.table("sessions").select("*").eq("session_id", session_id).execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            logger.error(f"Supabase fetch error: {e}")

    raise HTTPException(status_code=404, detail="Session not found")
