"""
Scoring Worker — reads jobs from Upstash Redis queue, runs 3-stage pipeline,
writes results to Supabase. Target: < 15 seconds per job.

Run with: python -m workers.scoring_worker
"""

import asyncio
import logging
import httpx
import json
import urllib.parse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from services.scoring_service import run_scoring_pipeline

logger = logging.getLogger(__name__)

QUEUE_KEY = "km:scoring_jobs"
POLL_INTERVAL = 3  # seconds



async def upstash_push(job_data: dict) -> bool:
    if not settings.UPSTASH_REDIS_REST_URL:
        logger.warning("Upstash not configured — job dropped")
        return False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{settings.UPSTASH_REDIS_REST_URL}/rpush/{QUEUE_KEY}",
                headers={"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"},
                json=[json.dumps(job_data)],
                timeout=10,
            )
        return r.status_code == 200
    except Exception as e:
        logger.error(f"upstash_push error: {e}")
        return False


async def upstash_pop() -> dict | None:
    if not settings.UPSTASH_REDIS_REST_URL:
        return None
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{settings.UPSTASH_REDIS_REST_URL}/lpop/{QUEUE_KEY}",
                headers={"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"},
                timeout=10,
            )
        data = r.json()
        if data.get("result"):
            return json.loads(data["result"])
        return None
    except Exception as e:
        logger.error(f"upstash_pop error: {e}")
        return None


async def upstash_get(key: str):
    if not settings.UPSTASH_REDIS_REST_URL:
        return None
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{settings.UPSTASH_REDIS_REST_URL}/get/{key}",
                headers={"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"},
                timeout=10,
            )
        return r.json().get("result")
    except Exception as e:
        logger.error(f"upstash_get error: {e}")
        return None


async def upstash_set(key: str, value: str, ex: int = 86400) -> bool:
    if not settings.UPSTASH_REDIS_REST_URL:
        return False
    try:
        encoded = urllib.parse.quote(value, safe="")
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{settings.UPSTASH_REDIS_REST_URL}/set/{key}/{encoded}?ex={ex}",
                headers={"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"},
                timeout=10,
            )
        return r.status_code == 200
    except Exception as e:
        logger.error(f"upstash_set error: {e}")
        return False


async def upstash_ping() -> bool:
    if not settings.UPSTASH_REDIS_REST_URL:
        return False
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{settings.UPSTASH_REDIS_REST_URL}/ping",
                headers={"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"},
                timeout=5,
            )
        return r.json().get("result") == "PONG"
    except Exception as e:
        logger.error(f"upstash_ping error: {e}")
        return False



async def write_result_to_supabase(session_id: str, result: dict):
    """Write scoring result to Supabase candidates table."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase not configured — result stored in Redis only")
        return

    try:
        from supabase import create_client
        sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

        record = {
            "session_id": session_id,
            "fitment_category": result["fitment_category"],
            "composite_score": result["composite_score"],
            "domain_score": result["domain_score"],
            "communication_score": result["communication_score"],
            "integrity_score": result["integrity_score"],
            "is_flagged": result["is_flagged"],
            "flag_reason": result.get("flag_reason"),
            "reason_card_en": result["reason_cards"].get("summary_en"),
            "reason_card_kn": result["reason_cards"].get("summary_kn"),
        }

        sb.table("candidates").upsert(record, on_conflict="session_id").execute()
        logger.info(f"Result written to Supabase for {session_id}")

        # Also write scores audit table
        sb.table("scores").insert({
            "session_id": session_id,
            "stage": 3,
            "score_data": json.dumps(result["stages"]),
        }).execute()

    except Exception as e:
        logger.error(f"Supabase write error for {session_id}: {e}")



async def process_scoring_job(job: dict):
    """Process a single scoring job from the queue."""
    session_id = job.get("session_id", "unknown")
    trade = job.get("trade", "electrician")
    history = job.get("history", [])
    integrity_events = job.get("integrity_events", [])

    logger.info(f"[Worker] Scoring session {session_id}: {len(history)} turns, {len(integrity_events)} integrity events")

    await upstash_set(f"score_status:{session_id}", "processing")

    try:
        result = await run_scoring_pipeline(
            session_id=session_id,
            trade=trade,
            history=history,
            integrity_events=integrity_events,
            groq_api_key=settings.GROQ_API_KEY,
        )

        await upstash_set(
            f"score_result:{session_id}",
            json.dumps(result),
            ex=86400,  # 24 hours
        )
        await upstash_set(f"score_status:{session_id}", "complete")

        await write_result_to_supabase(session_id, result)

        logger.info(f"[Worker] ✅ {session_id} → {result['fitment_category']} ({result['composite_score']}/10) in {result['elapsed_seconds']}s")

    except Exception as e:
        logger.error(f"[Worker] ❌ {session_id} failed: {e}")
        await upstash_set(f"score_status:{session_id}", "error")



async def run_worker_loop():
    print("🔄 Starting KaushalMitra scoring worker...")

    if not settings.UPSTASH_REDIS_REST_URL:
        print("⚠️  UPSTASH_REDIS_REST_URL not set — worker will idle")
    else:
        ok = await upstash_ping()
        print(f"{'✅' if ok else '❌'} Upstash Redis {'connected' if ok else 'connection failed'}")

    if not settings.GROQ_API_KEY:
        print("⚠️  GROQ_API_KEY not set — reason cards will use fallback text")

    print(f"   Polling every {POLL_INTERVAL}s ... (Ctrl+C to stop)\n")

    while True:
        try:
            job = await upstash_pop()
            if job:
                await process_scoring_job(job)
            else:
                await asyncio.sleep(POLL_INTERVAL)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(POLL_INTERVAL)



async def test_connection():
    print("Testing Upstash + scoring pipeline...")
    ok = await upstash_ping()
    print(f"Upstash ping: {'✅' if ok else '❌'}")

    if ok:
        test_job = {
            "session_id": "test-score-001",
            "trade": "electrician",
            "history": [
                {"answer": "I have 5 years experience", "score": 7, "quality": "good", "stage": "background"},
                {"answer": "Single phase is 230V, three phase is 415V", "score": 8, "quality": "excellent", "stage": "l1_domain"},
                {"answer": "I always earth the panel first", "score": 9, "quality": "excellent", "stage": "l1_domain"},
            ],
            "integrity_events": [
                {"face_detected": True, "multiple_faces": False},
                {"face_detected": True, "multiple_faces": False},
                {"face_detected": True, "multiple_faces": False},
            ],
        }
        pushed = await upstash_push(test_job)
        print(f"Test job pushed: {'✅' if pushed else '❌'}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_connection())
    else:
        asyncio.run(run_worker_loop())
