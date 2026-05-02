"""
Admin Router — GET /admin/candidates with filtering.
Day 1: returns seeded/in-memory data. Day 3: full Supabase integration.
"""

from fastapi import APIRouter, Query
from typing import Optional
from config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/candidates")
async def list_candidates(
    district: Optional[str] = Query(None),
    trade: Optional[str] = Query(None),
    fitment: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    """
    List candidates with optional filters.
    Used by admin dashboard (Day 3 full implementation).
    Day 1: returns empty list — Supabase integration added Day 3.
    """
    filters = {k: v for k, v in {
        "district": district, "trade": trade,
        "fitment_category": fitment, "language": language,
    }.items() if v}

    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            from supabase import create_client
            sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            query = sb.table("candidates").select("*").limit(limit)
            for col, val in filters.items():
                query = query.eq(col, val)
            result = query.execute()
            return {"candidates": result.data, "count": len(result.data)}
        except Exception as e:
            logger.error(f"Supabase error: {e}")

    return {"candidates": [], "count": 0, "note": "Supabase not configured yet"}


@router.get("/stats")
async def dashboard_stats():
    """Summary stats for admin dashboard header."""
    return {
        "total_candidates": 0,
        "job_ready": 0,
        "requires_training": 0,
        "flagged": 0,
        "note": "Day 3 implementation — seeded data coming",
    }
