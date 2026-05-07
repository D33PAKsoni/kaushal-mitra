-- KaushalMitra Day 3 — Supabase Migration
-- Run this in Supabase Dashboard → SQL Editor

-- 1. Add shortlisted column to candidates
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS is_shortlisted BOOLEAN DEFAULT FALSE;

-- 2. Update candidates table policy for service role
DROP POLICY IF EXISTS "service_role_all" ON candidates;
CREATE POLICY "service_role_all" ON candidates
  FOR ALL USING (auth.role() = 'service_role');

-- 3. Seed 20 demo candidates (paste seed_data values here if needed)
-- Or run: python backend/scripts/seed_supabase.py

-- 4. Verify tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
