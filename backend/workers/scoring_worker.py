"""
Async Scoring Worker — arq + Upstash Redis.
Day 1: scaffold with dummy job to verify Redis connection.
Day 3: full 3-stage scoring pipeline.

Run with: python -m workers.scoring_worker
"""

import asyncio
import logging
from arq import create_pool
from arq.connections import RedisSettings

from config import settings

logger = logging.getLogger(__name__)


async def dummy_score_job(ctx, session_id: str):
    """
    Day 1 dummy job — just verifies Redis queue works.
    Day 3: replace with real 3-stage scoring pipeline.
    """
    logger.info(f"[Worker] Dummy job received for session: {session_id}")
    await asyncio.sleep(1)  # Simulate work
    logger.info(f"[Worker] Dummy job complete for session: {session_id}")
    return {"session_id": session_id, "status": "processed"}


class WorkerSettings:
    functions = [dummy_score_job]
    redis_settings = RedisSettings.from_dsn(
        settings.UPSTASH_REDIS_REST_URL or "redis://localhost:6379"
    )
    max_jobs = 10
    job_timeout = 300  # 5 minutes


async def test_redis_connection():
    """Day 1 diagnostic — test Upstash Redis connection."""
    if not settings.UPSTASH_REDIS_REST_URL:
        print("⚠️  UPSTASH_REDIS_REST_URL not set — skipping Redis test")
        return False

    try:
        redis = await create_pool(
            RedisSettings.from_dsn(settings.UPSTASH_REDIS_REST_URL)
        )
        await redis.ping()
        print("✅ Redis connection successful")

        # Enqueue a test job
        job = await redis.enqueue_job("dummy_score_job", "test-session-001")
        print(f"✅ Test job enqueued: {job.job_id}")
        await redis.close()
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # python -m workers.scoring_worker test
        asyncio.run(test_redis_connection())
    else:
        # python -m workers.scoring_worker
        print("🔄 Starting KaushalMitra scoring worker...")
        from arq import run_worker
        run_worker(WorkerSettings)
