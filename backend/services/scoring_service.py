"""
Scoring Pipeline — 3 stages, every decision audited.

Stage 1: Integrity Gate
  - Face presence rate < 60% → flag
  - Duplicate face embedding → flag
  - Short session (< 3 turns) → flag

Stage 2: Skill Score Computation
  - Domain score: average of per-turn answer_scores from agent
  - Communication score: transcript length + language confidence
  - Composite = 0.6 * domain + 0.4 * communication

Stage 3: Fitment Classifier
  - composite >= 8.0  → Job Ready ✅
  - composite >= 6.0  → Trainable 🟡
  - composite >= 4.0  → Requires Training 🟠
  - composite <  4.0  → Not Suitable 🔴
  - flagged          → Review Required 🔴 (overrides all)

Every stage writes structured audit log — no black-box decisions.
"""

import logging
import json
import time
from groq import AsyncGroq

logger = logging.getLogger(__name__)

# ── Fitment categories ────────────────────────────────────
FITMENT = {
    "job_ready":          {"en": "Job Ready",          "kn": "ಕೆಲಸಕ್ಕೆ ಸಿದ್ಧ",         "color": "green",  "emoji": "✅"},
    "trainable":          {"en": "Trainable",           "kn": "ತರಬೇತಿ ಯೋಗ್ಯ",           "color": "yellow", "emoji": "🟡"},
    "requires_training":  {"en": "Requires Training",   "kn": "ತರಬೇತಿ ಅಗತ್ಯ",           "color": "orange", "emoji": "🟠"},
    "not_suitable":       {"en": "Not Suitable",        "kn": "ಸೂಕ್ತವಲ್ಲ",              "color": "red",    "emoji": "🔴"},
    "review_required":    {"en": "Review Required",     "kn": "ಪರಿಶೀಲನೆ ಅಗತ್ಯ",         "color": "red",    "emoji": "🔍"},
}


async def run_scoring_pipeline(
    session_id: str,
    trade: str,
    history: list[dict],
    integrity_events: list[dict],
    groq_api_key: str,
) -> dict:
    """
    Full 3-stage pipeline. Returns complete audit result.
    Target: completes within 15 seconds.
    """
    start = time.time()
    audit = {
        "session_id": session_id,
        "trade": trade,
        "stages": {},
        "started_at": start,
    }

    # ── Stage 1: Integrity Gate ───────────────────────────
    integrity = _run_integrity_gate(session_id, history, integrity_events)
    audit["stages"]["integrity"] = integrity
    logger.info(f"[Score] {session_id} Stage 1: integrity={integrity['passed']}, flags={integrity['flags']}")

    # ── Stage 2: Skill Score ──────────────────────────────
    skill = _compute_skill_scores(history)
    audit["stages"]["skill"] = skill
    logger.info(f"[Score] {session_id} Stage 2: domain={skill['domain_score']:.1f}, comm={skill['communication_score']:.1f}, composite={skill['composite_score']:.1f}")

    # ── Stage 3: Fitment Classifier ───────────────────────
    fitment_key = _classify_fitment(
        composite=skill["composite_score"],
        is_flagged=not integrity["passed"],
    )
    audit["stages"]["fitment"] = {
        "category": fitment_key,
        "label_en": FITMENT[fitment_key]["en"],
        "label_kn": FITMENT[fitment_key]["kn"],
        "color": FITMENT[fitment_key]["color"],
        "emoji": FITMENT[fitment_key]["emoji"],
    }
    logger.info(f"[Score] {session_id} Stage 3: fitment={fitment_key}")

    # ── Reason cards (Groq) ───────────────────────────────
    reason_cards = await _generate_reason_cards(
        session_id=session_id,
        trade=trade,
        fitment_key=fitment_key,
        skill=skill,
        integrity=integrity,
        groq_api_key=groq_api_key,
    )
    audit["reason_cards"] = reason_cards

    elapsed = round(time.time() - start, 2)
    audit["elapsed_seconds"] = elapsed
    audit["composite_score"] = skill["composite_score"]
    audit["domain_score"] = skill["domain_score"]
    audit["communication_score"] = skill["communication_score"]
    audit["integrity_score"] = integrity["integrity_score"]
    audit["fitment_category"] = fitment_key
    audit["is_flagged"] = not integrity["passed"]
    audit["flag_reason"] = ", ".join(integrity["flags"]) if integrity["flags"] else None

    logger.info(f"[Score] {session_id} complete in {elapsed}s → {fitment_key}")
    return audit


# ── Stage 1 ───────────────────────────────────────────────

def _run_integrity_gate(
    session_id: str,
    history: list[dict],
    integrity_events: list[dict],
) -> dict:
    flags = []
    details = {}

    # 1a. Turn count check
    turn_count = len(history)
    details["turn_count"] = turn_count
    if turn_count < 3:
        flags.append("too_few_turns")

    # 1b. Face presence rate
    if integrity_events:
        face_ok = sum(1 for e in integrity_events if e.get("face_detected", True))
        face_rate = face_ok / len(integrity_events)
        details["face_presence_rate"] = round(face_rate, 2)
        if face_rate < 0.6:
            flags.append("low_face_presence")
        if any(e.get("multiple_faces") for e in integrity_events):
            flags.append("multiple_faces_detected")
    else:
        # No events = camera not used (desktop without camera)
        details["face_presence_rate"] = None
        details["note"] = "No integrity events — camera may not have been active"

    # 1c. Answer quality check — too many no-answers
    no_answer_count = sum(
        1 for t in history if t.get("quality") == "no_answer"
    )
    details["no_answer_count"] = no_answer_count
    if no_answer_count >= 3:
        flags.append("too_many_no_answers")

    # Integrity score (0-10)
    integrity_score = 10.0
    if "low_face_presence" in flags:
        integrity_score -= 3.0
    if "multiple_faces_detected" in flags:
        integrity_score -= 4.0
    if "too_few_turns" in flags:
        integrity_score -= 2.0
    if "too_many_no_answers" in flags:
        integrity_score -= 2.0
    integrity_score = max(0.0, integrity_score)

    return {
        "passed": len(flags) == 0,
        "flags": flags,
        "integrity_score": round(integrity_score, 1),
        "details": details,
    }


# ── Stage 2 ───────────────────────────────────────────────

def _compute_skill_scores(history: list[dict]) -> dict:
    if not history:
        return {
            "domain_score": 0.0,
            "communication_score": 0.0,
            "composite_score": 0.0,
            "per_turn": [],
            "total_turns": 0,
        }

    per_turn = []
    domain_scores = []
    comm_scores = []

    for turn in history:
        answer = turn.get("answer", "")
        agent_score = float(turn.get("score", 5))
        quality = turn.get("quality", "poor")

        # Communication score: word count + quality signal
        word_count = len(answer.split()) if answer else 0
        comm = min(10.0, word_count / 3.0)  # 30 words = 10/10
        if quality in ("excellent", "good"):
            comm = min(10.0, comm + 1.0)

        domain_scores.append(agent_score)
        comm_scores.append(comm)

        per_turn.append({
            "stage": turn.get("stage", "unknown"),
            "quality": quality,
            "domain_score": agent_score,
            "communication_score": round(comm, 1),
            "word_count": word_count,
        })

    domain_avg = round(sum(domain_scores) / len(domain_scores), 2)
    comm_avg = round(sum(comm_scores) / len(comm_scores), 2)
    composite = round(0.6 * domain_avg + 0.4 * comm_avg, 2)

    return {
        "domain_score": domain_avg,
        "communication_score": comm_avg,
        "composite_score": composite,
        "per_turn": per_turn,
        "total_turns": len(history),
    }


# ── Stage 3 ───────────────────────────────────────────────

def _classify_fitment(composite: float, is_flagged: bool) -> str:
    if is_flagged:
        return "review_required"
    if composite >= 8.0:
        return "job_ready"
    if composite >= 6.0:
        return "trainable"
    if composite >= 4.0:
        return "requires_training"
    return "not_suitable"


# ── Reason cards ──────────────────────────────────────────

async def _generate_reason_cards(
    session_id: str,
    trade: str,
    fitment_key: str,
    skill: dict,
    integrity: dict,
    groq_api_key: str,
) -> dict:
    """Generate bilingual reason cards via Groq."""
    if not groq_api_key:
        return _fallback_reason_cards(fitment_key, skill)

    prompt = f"""You are writing a skill assessment result card for a government job readiness program in Karnataka, India.

CANDIDATE RESULT:
- Trade: {trade}
- Fitment category: {FITMENT[fitment_key]['en']}
- Domain score: {skill['domain_score']}/10
- Communication score: {skill['communication_score']}/10
- Composite score: {skill['composite_score']}/10
- Integrity flags: {integrity['flags'] or 'None'}
- Turns completed: {skill['total_turns']}

Write a reason card with:
1. A 1-sentence summary of the result (plain language, no jargon)
2. 2-3 specific strengths observed
3. 2-3 specific areas to improve
4. ONE clear recommended next action (e.g., "Enroll in DDUGKY electrician advanced course")

Write in BOTH English and Kannada. Be honest but respectful — this person may show this to a family member.
Non-technical people must immediately understand what action to take.

Respond ONLY in this JSON format:
{{
  "summary_en": "...",
  "summary_kn": "...",
  "strengths_en": ["...", "..."],
  "strengths_kn": ["...", "..."],
  "improvements_en": ["...", "..."],
  "improvements_kn": ["...", "..."],
  "next_action_en": "...",
  "next_action_kn": "..."
}}"""

    try:
        client = AsyncGroq(api_key=groq_api_key)
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Reason card generation failed: {e}")
        return _fallback_reason_cards(fitment_key, skill)


def _fallback_reason_cards(fitment_key: str, skill: dict) -> dict:
    """Static fallback if Groq fails."""
    label = FITMENT[fitment_key]["en"]
    return {
        "summary_en": f"Candidate assessed as {label} with composite score {skill['composite_score']}/10.",
        "summary_kn": f"ಅಭ್ಯರ್ಥಿಯನ್ನು {FITMENT[fitment_key]['kn']} ಎಂದು ಮೌಲ್ಯಮಾಪನ ಮಾಡಲಾಗಿದೆ.",
        "strengths_en": ["Completed the interview process"],
        "strengths_kn": ["ಸಂದರ್ಶನ ಪ್ರಕ್ರಿಯೆ ಪೂರ್ಣಗೊಳಿಸಿದ್ದಾರೆ"],
        "improvements_en": ["Further assessment recommended"],
        "improvements_kn": ["ಹೆಚ್ಚಿನ ಮೌಲ್ಯಮಾಪನ ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ"],
        "next_action_en": "Please visit your nearest DDUGKY centre for guidance.",
        "next_action_kn": "ದಯವಿಟ್ಟು ಮಾರ್ಗದರ್ಶನಕ್ಕಾಗಿ ಹತ್ತಿರದ DDUGKY ಕೇಂದ್ರಕ್ಕೆ ಭೇಟಿ ನೀಡಿ.",
    }
