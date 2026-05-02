"""
Session Router — manage candidate interview sessions.
Day 1: create session + store to Supabase (or in-memory if Supabase not yet configured).
"""

from fastapi import APIRouter, HTTPException
from models.schemas import SessionCreateRequest, SessionCreateResponse
from config import settings
import uuid
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# ── In-memory fallback store (used when Supabase not yet configured) ──
_sessions: dict = {}


@router.post("/create", response_model=SessionCreateResponse)
async def create_session(body: SessionCreateRequest):
    """Create a new interview session for a candidate."""
    session_id = str(uuid.uuid4())

    session_data = {
        "session_id": session_id,
        "candidate_name": body.candidate_name,
        "trade": body.trade,
        "district": body.district,
        "preferred_language": body.preferred_language,
        "status": "created",
    }

    # Try Supabase; fall back to in-memory
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            from supabase import create_client
            sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            sb.table("sessions").insert(session_data).execute()
            logger.info(f"Session {session_id} saved to Supabase")
        except Exception as e:
            logger.warning(f"Supabase insert failed, using in-memory: {e}")
            _sessions[session_id] = session_data
    else:
        logger.info("Supabase not configured — using in-memory session store")
        _sessions[session_id] = session_data

    return SessionCreateResponse(
        session_id=session_id,
        status="created",
        message_kannada="ಸೆಷನ್ ಪ್ರಾರಂಭವಾಗಿದೆ",
    )


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get session details by ID."""
    # Check in-memory first
    if session_id in _sessions:
        return _sessions[session_id]

    # Try Supabase
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
