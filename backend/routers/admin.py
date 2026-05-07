"""
Admin Router — Govt-grade dashboard endpoints.
Designed for a 55-year-old IAS officer: clear, no jargon, bilingual.
"""

import json
import logging
import csv
import io
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

FITMENT_COLORS = {
    "job_ready": "green",
    "trainable": "yellow",
    "requires_training": "orange",
    "not_suitable": "red",
    "review_required": "red",
}

FITMENT_LABELS = {
    "job_ready":         {"en": "Job Ready ✅",         "kn": "ಕೆಲಸಕ್ಕೆ ಸಿದ್ಧ ✅"},
    "trainable":         {"en": "Trainable 🟡",          "kn": "ತರಬೇತಿ ಯೋಗ್ಯ 🟡"},
    "requires_training": {"en": "Requires Training 🟠",  "kn": "ತರಬೇತಿ ಅಗತ್ಯ 🟠"},
    "not_suitable":      {"en": "Not Suitable 🔴",       "kn": "ಸೂಕ್ತವಲ್ಲ 🔴"},
    "review_required":   {"en": "Review Required 🔍",    "kn": "ಪರಿಶೀಲನೆ ಅಗತ್ಯ 🔍"},
}


def _get_supabase():
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        return None
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.get("/candidates")
async def list_candidates(
    district: Optional[str] = Query(None),
    trade: Optional[str] = Query(None),
    fitment: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    flagged_only: bool = Query(False),
    shortlisted_only: bool = Query(False),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """
    List candidates with filtering. Powers admin dashboard table.
    Filters: district, trade, fitment category, language, flagged, shortlisted, name search.
    """
    sb = _get_supabase()
    if not sb:
        # Return seeded data if Supabase not configured
        from scripts.seed_data import SEEDED_CANDIDATES
        return {"candidates": SEEDED_CANDIDATES[:limit], "count": len(SEEDED_CANDIDATES), "source": "seed"}

    try:
        query = sb.table("candidates").select("*")

        if district:
            query = query.eq("district", district)
        if trade:
            query = query.eq("trade", trade)
        if fitment:
            query = query.eq("fitment_category", fitment)
        if language:
            query = query.eq("language", language)
        if flagged_only:
            query = query.eq("is_flagged", True)
        if shortlisted_only:
            query = query.eq("is_shortlisted", True)
        if search:
            query = query.ilike("name", f"%{search}%")

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        # Enrich with labels
        candidates = []
        for c in result.data:
            fc = c.get("fitment_category", "")
            c["fitment_label_en"] = FITMENT_LABELS.get(fc, {}).get("en", fc)
            c["fitment_label_kn"] = FITMENT_LABELS.get(fc, {}).get("kn", fc)
            c["fitment_color"] = FITMENT_COLORS.get(fc, "gray")
            candidates.append(c)

        return {"candidates": candidates, "count": len(candidates), "source": "supabase"}

    except Exception as e:
        logger.error(f"Admin list error: {e}")
        from scripts.seed_data import SEEDED_CANDIDATES
        return {"candidates": SEEDED_CANDIDATES[:limit], "count": len(SEEDED_CANDIDATES), "source": "seed_fallback"}


@router.get("/stats")
async def dashboard_stats():
    """Summary stats for dashboard header cards."""
    sb = _get_supabase()

    try:
        if sb:
            all_result = sb.table("candidates").select("fitment_category, is_flagged, is_shortlisted").execute()
            rows = all_result.data
        else:
            from scripts.seed_data import SEEDED_CANDIDATES
            rows = SEEDED_CANDIDATES

        total = len(rows)
        job_ready = sum(1 for r in rows if r.get("fitment_category") == "job_ready")
        trainable = sum(1 for r in rows if r.get("fitment_category") == "trainable")
        requires_training = sum(1 for r in rows if r.get("fitment_category") == "requires_training")
        not_suitable = sum(1 for r in rows if r.get("fitment_category") == "not_suitable")
        flagged = sum(1 for r in rows if r.get("is_flagged"))
        shortlisted = sum(1 for r in rows if r.get("is_shortlisted"))
        review_required = sum(1 for r in rows if r.get("fitment_category") == "review_required")

        return {
            "total": total,
            "job_ready": job_ready,
            "trainable": trainable,
            "requires_training": requires_training,
            "not_suitable": not_suitable,
            "review_required": review_required,
            "flagged": flagged,
            "shortlisted": shortlisted,
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"total": 0, "error": str(e)}


@router.post("/candidates/{session_id}/shortlist")
async def shortlist_candidate(session_id: str):
    """Shortlist a candidate (human override workflow)."""
    sb = _get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    try:
        sb.table("candidates").update({"is_shortlisted": True}).eq("session_id", session_id).execute()
        return {"session_id": session_id, "is_shortlisted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/candidates/{session_id}/unflag")
async def unflag_candidate(session_id: str, reason: str = "Manual review completed"):
    """Clear flag after human review (IAS override workflow)."""
    sb = _get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    try:
        sb.table("candidates").update({
            "is_flagged": False,
            "flag_reason": f"Cleared: {reason}",
        }).eq("session_id", session_id).execute()
        return {"session_id": session_id, "is_flagged": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/csv")
async def export_csv(
    district: Optional[str] = Query(None),
    trade: Optional[str] = Query(None),
    fitment: Optional[str] = Query(None),
):
    """Export filtered candidates as CSV for district officer."""
    sb = _get_supabase()

    try:
        if sb:
            query = sb.table("candidates").select("*")
            if district: query = query.eq("district", district)
            if trade: query = query.eq("trade", trade)
            if fitment: query = query.eq("fitment_category", fitment)
            rows = query.execute().data
        else:
            from scripts.seed_data import SEEDED_CANDIDATES
            rows = SEEDED_CANDIDATES

        output = io.StringIO()
        fieldnames = [
            "name", "trade", "district", "language",
            "fitment_category", "composite_score", "domain_score",
            "communication_score", "integrity_score",
            "is_flagged", "flag_reason", "is_shortlisted",
            "reason_card_en", "created_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

        output.seek(0)
        filename = f"kaushal_mitra_candidates_{district or 'all'}_{trade or 'all'}.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flagged")
async def get_flagged(limit: int = Query(20)):
    """Flagged review queue — shown prominently in admin dashboard."""
    sb = _get_supabase()
    try:
        if sb:
            result = sb.table("candidates").select("*").eq("is_flagged", True).limit(limit).execute()
            rows = result.data
        else:
            from scripts.seed_data import SEEDED_CANDIDATES
            rows = [r for r in SEEDED_CANDIDATES if r.get("is_flagged")]
        return {"flagged": rows, "count": len(rows)}
    except Exception as e:
        from scripts.seed_data import SEEDED_CANDIDATES
        rows = [r for r in SEEDED_CANDIDATES if r.get("is_flagged")]
        return {"flagged": rows, "count": len(rows)}
