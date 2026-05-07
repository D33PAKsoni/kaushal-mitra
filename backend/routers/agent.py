"""
Agent Router — POST /agent/turn
Day 3 fix: scoring runs inline (asyncio.create_task) when interview completes.
This ensures scoring happens even on HF Spaces where the worker process
is not separately running.
"""

import json
import logging
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from services.agent_service import run_agent_turn
from services.tts_service import synthesize_kannada
from workers.scoring_worker import upstash_push, upstash_get, upstash_set
from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class IntegrityEventPayload(BaseModel):
    timestamp_ms: Optional[int] = None
    event_type: Optional[str] = "face_ok"
    face_detected: bool = True
    multiple_faces: bool = False
    face_coverage: Optional[float] = 1.0


class TurnRequest(BaseModel):
    session_id: str
    trade: str
    transcript: str
    turn_number: int = 0
    preferred_language: str = "kn"
    integrity_events: Optional[List[IntegrityEventPayload]] = None


class TurnResponse(BaseModel):
    session_id: str
    turn_number: int
    answer_quality: str
    answer_score: int
    next_question_en: str
    next_question_kn: str
    next_question_primary: str
    current_stage: str
    is_complete: bool
    tts: dict
    processing_time_ms: int


async def get_session_state(session_id: str) -> dict:
    try:
        result = await upstash_get(f"session_state:{session_id}")
        if result:
            return json.loads(result)
    except Exception as e:
        logger.warning(f"Could not load session state: {e}")
    return {
        "turn_number": 0,
        "current_stage": "background",
        "stage_turn_counts": {},
        "used_question_ids": [],
        "history": [],
        "integrity_events": [],
    }


async def save_session_state(session_id: str, state: dict):
    try:
        await upstash_set(f"session_state:{session_id}", json.dumps(state))
    except Exception as e:
        logger.warning(f"Could not save session state: {e}")


async def _run_scoring_inline(session_id: str, trade: str, history: list, integrity_events: list):
    """
    Run the full scoring pipeline inline as a background task.
    This fires when the interview completes — no separate worker process needed.
    Works on HF Spaces where only uvicorn runs.
    """
    try:
        logger.info(f"[Inline Scoring] Starting for {session_id}")

        # Mark as processing immediately
        await upstash_set(f"score_status:{session_id}", "processing")

        from services.scoring_service import run_scoring_pipeline
        result = await run_scoring_pipeline(
            session_id=session_id,
            trade=trade,
            history=history,
            integrity_events=integrity_events,
            groq_api_key=settings.GROQ_API_KEY,
        )

        # Store result in Redis for frontend polling
        await upstash_set(
            f"score_result:{session_id}",
            json.dumps(result),
            ex=86400,
        )
        await upstash_set(f"score_status:{session_id}", "complete")
        logger.info(f"[Inline Scoring] ✅ {session_id} → {result['fitment_category']} ({result['composite_score']}/10)")

        # Write to Supabase (best-effort)
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
            try:
                from supabase import create_client
                sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

                # Get session info for name/district
                session_raw = await upstash_get(f"session_info:{session_id}")
                session_info = json.loads(session_raw) if session_raw else {}

                record = {
                    "session_id": session_id,
                    "name": session_info.get("candidate_name", "Unknown"),
                    "trade": trade,
                    "district": session_info.get("district", "Unknown"),
                    "language": session_info.get("preferred_language", "kn"),
                    "fitment_category": result["fitment_category"],
                    "composite_score": result["composite_score"],
                    "domain_score": result["domain_score"],
                    "communication_score": result["communication_score"],
                    "integrity_score": result["integrity_score"],
                    "is_flagged": result["is_flagged"],
                    "flag_reason": result.get("flag_reason"),
                    "reason_card_en": result["reason_cards"].get("summary_en"),
                    "reason_card_kn": result["reason_cards"].get("summary_kn"),
                    "is_shortlisted": False,
                }
                sb.table("candidates").upsert(record, on_conflict="session_id").execute()
                logger.info(f"[Inline Scoring] Supabase write OK for {session_id}")
            except Exception as e:
                logger.error(f"[Inline Scoring] Supabase write failed: {e}")

    except Exception as e:
        logger.error(f"[Inline Scoring] ❌ {session_id} failed: {e}")
        await upstash_set(f"score_status:{session_id}", "error")


@router.post("/turn", response_model=TurnResponse)
async def agent_turn(body: TurnRequest):
    import time
    start = time.time()

    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY not configured.")

    state = await get_session_state(body.session_id)
    history = state.get("history", [])

    # Accumulate integrity events
    all_integrity = state.get("integrity_events", [])
    if body.integrity_events:
        all_integrity.extend([e.dict() for e in body.integrity_events])

    agent_resp = await run_agent_turn(
        groq_api_key=settings.GROQ_API_KEY,
        trade=body.trade,
        transcript=body.transcript,
        history=history,
        session_state=state,
        preferred_language=body.preferred_language,
    )

    new_history = history + [{
        "candidate": body.transcript,
        "agent_en": agent_resp.next_question_en,
        "agent_kn": agent_resp.next_question_kn,
        "quality": agent_resp.answer_quality,
        "score": agent_resp.answer_score,
        "stage": agent_resp.current_stage,
        "answer": body.transcript,
    }]

    state["turn_number"] = agent_resp.turn_number
    state["current_stage"] = agent_resp.current_stage
    state["history"] = new_history
    state["integrity_events"] = all_integrity
    await save_session_state(body.session_id, state)

    tts_result = await synthesize_kannada(
        text=agent_resp.next_question_primary,
        bhashini_api_key=settings.BHASHINI_API_KEY,
        bhashini_user_id=settings.BHASHINI_USER_ID,
    )

    # On completion — fire inline scoring as background task
    # (no separate worker process needed — works on HF Spaces)
    if agent_resp.is_complete:
        asyncio.create_task(
            _run_scoring_inline(
                session_id=body.session_id,
                trade=body.trade,
                history=new_history,
                integrity_events=all_integrity,
            )
        )
        logger.info(f"[Agent] Interview complete — inline scoring task created for {body.session_id}")

    elapsed = int((time.time() - start) * 1000)

    return TurnResponse(
        session_id=body.session_id,
        turn_number=agent_resp.turn_number,
        answer_quality=agent_resp.answer_quality,
        answer_score=agent_resp.answer_score,
        next_question_en=agent_resp.next_question_en,
        next_question_kn=agent_resp.next_question_kn,
        next_question_primary=agent_resp.next_question_primary,
        current_stage=agent_resp.current_stage,
        is_complete=agent_resp.is_complete,
        tts=tts_result,
        processing_time_ms=elapsed,
    )


@router.get("/session/{session_id}/history")
async def get_history(session_id: str):
    state = await get_session_state(session_id)
    return {
        "session_id": session_id,
        "turn_number": state.get("turn_number", 0),
        "current_stage": state.get("current_stage", "background"),
        "history": state.get("history", []),
    }
