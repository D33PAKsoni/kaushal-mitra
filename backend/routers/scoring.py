"""
Scoring Router — GET /score/{session_id}/status, GET /score/{session_id}/result
Frontend polls these to show candidate waiting screen and final result.
"""

import json
import logging
from fastapi import APIRouter, HTTPException
from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


async def _redis_get(key: str):
    from workers.scoring_worker import upstash_get
    return await upstash_get(key)


@router.get("/{session_id}/status")
async def get_score_status(session_id: str):
    """
    Poll this endpoint after interview complete.
    Returns: processing | complete | error | not_started
    """
    status = await _redis_get(f"score_status:{session_id}")
    return {"session_id": session_id, "status": status or "not_started"}


@router.get("/{session_id}/result")
async def get_score_result(session_id: str):
    """Get full scoring result once status=complete."""
    result_raw = await _redis_get(f"score_result:{session_id}")
    if not result_raw:
        raise HTTPException(
            status_code=404,
            detail="Score result not found. Check status endpoint first.",
        )
    return json.loads(result_raw)


@router.get("/{session_id}/result/summary")
async def get_result_summary(session_id: str):
    """Lightweight summary for candidate result screen."""
    result_raw = await _redis_get(f"score_result:{session_id}")
    if not result_raw:
        raise HTTPException(status_code=404, detail="Result not ready")
    r = json.loads(result_raw)
    return {
        "session_id": session_id,
        "fitment_category": r["fitment_category"],
        "fitment_label_en": r["stages"]["fitment"]["label_en"],
        "fitment_label_kn": r["stages"]["fitment"]["label_kn"],
        "fitment_emoji": r["stages"]["fitment"]["emoji"],
        "composite_score": r["composite_score"],
        "domain_score": r["domain_score"],
        "communication_score": r["communication_score"],
        "is_flagged": r["is_flagged"],
        "reason_cards": r.get("reason_cards", {}),
    }
