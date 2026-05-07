"""
Database setup script — creates Supabase tables for KaushalMitra.
Run once: python scripts/setup_db.py

Tables created:
  - candidates
  - sessions
  - integrity_events
  - scores
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import supabase

from config import settings


SCHEMA_SQL = """
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── candidates ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candidates (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id        TEXT UNIQUE NOT NULL,
    name              TEXT NOT NULL,
    trade             TEXT NOT NULL,
    district          TEXT NOT NULL,
    language          TEXT NOT NULL DEFAULT 'kn',
    fitment_category  TEXT,
    composite_score   NUMERIC(5,2),
    integrity_score   NUMERIC(5,2),
    domain_score      NUMERIC(5,2),
    communication_score NUMERIC(5,2),
    is_flagged        BOOLEAN DEFAULT FALSE,
    flag_reason       TEXT,
    reason_card_en    TEXT,
    reason_card_kn    TEXT,
    face_embedding_hash TEXT,
    duplicate_similarity NUMERIC(4,3),
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ── sessions ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id        TEXT UNIQUE NOT NULL,
    candidate_name    TEXT NOT NULL,
    trade             TEXT NOT NULL,
    district          TEXT NOT NULL,
    preferred_language TEXT DEFAULT 'kn',
    status            TEXT DEFAULT 'created',
    turn_count        INT DEFAULT 0,
    transcript_json   JSONB,
    audio_storage_path TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ── integrity_events ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS integrity_events (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id        TEXT NOT NULL REFERENCES sessions(session_id),
    timestamp_ms      INT NOT NULL,
    event_type        TEXT NOT NULL,
    face_detected     BOOLEAN,
    multiple_faces    BOOLEAN,
    face_coverage     NUMERIC(4,3),
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ── scores ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scores (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id        TEXT NOT NULL REFERENCES sessions(session_id),
    stage             INT NOT NULL,
    score_data        JSONB NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ── Row Level Security ────────────────────────────────────
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE integrity_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE scores ENABLE ROW LEVEL SECURITY;

-- Policy: service role has full access (backend uses service role key)
CREATE POLICY IF NOT EXISTS "service_role_all" ON candidates
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY IF NOT EXISTS "service_role_all" ON sessions
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY IF NOT EXISTS "service_role_all" ON integrity_events
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY IF NOT EXISTS "service_role_all" ON scores
    FOR ALL USING (auth.role() = 'service_role');

-- Index for admin dashboard queries
CREATE INDEX IF NOT EXISTS idx_candidates_district ON candidates(district);
CREATE INDEX IF NOT EXISTS idx_candidates_trade ON candidates(trade);
CREATE INDEX IF NOT EXISTS idx_candidates_fitment ON candidates(fitment_category);
"""


def setup():
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        print("❌ SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        print("   Get them from: Supabase Dashboard → Settings → API")
        sys.exit(1)

    try:
        from supabase import create_client
        sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

        # Execute schema via Supabase's SQL editor (rpc)
        # Note: For initial setup, you can also paste SCHEMA_SQL directly into
        # Supabase Dashboard → SQL Editor
        print("ℹ️  Schema SQL generated. Choose how to apply:")
        print()
        print("  Option A (Recommended): Paste the SQL into Supabase Dashboard")
        print("  → https://supabase.com/dashboard → your project → SQL Editor")
        print()
        print("  Option B: Use psycopg2 with direct connection string")
        print("  → Settings → Database → Connection string → Direct")
        print()
        print("─" * 60)
        print(SCHEMA_SQL)
        print("─" * 60)
        print()
        print("✅ Copy the SQL above into Supabase SQL Editor and run it.")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    setup()
