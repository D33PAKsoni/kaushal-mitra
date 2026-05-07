"""
Seed 20 demo candidates to Supabase.
Run: python scripts/seed_supabase.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from scripts.seed_data import SEEDED_CANDIDATES


def seed():
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        print("❌ SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)

    from supabase import create_client
    sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    print(f"Seeding {len(SEEDED_CANDIDATES)} candidates...")

    # Add required fields not in seed data
    for c in SEEDED_CANDIDATES:
        c.setdefault("is_shortlisted", c.get("is_shortlisted", False))

    try:
        # Upsert to avoid duplicates on re-run
        result = sb.table("candidates").upsert(
            SEEDED_CANDIDATES,
            on_conflict="session_id"
        ).execute()
        print(f"✅ Seeded {len(result.data)} candidates successfully")

        # Verify
        count = sb.table("candidates").select("session_id", count="exact").execute()
        print(f"📊 Total candidates in DB: {count.count}")

    except Exception as e:
        print(f"❌ Seed failed: {e}")
        print("Tip: Run day3_migration.sql in Supabase SQL Editor first")
        sys.exit(1)


if __name__ == "__main__":
    seed()
