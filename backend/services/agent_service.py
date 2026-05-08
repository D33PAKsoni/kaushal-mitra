"""
Agent Service — Groq-powered Kannada interview agent.
3-layer prompt architecture:
  1. System persona (Kannada-first interviewer)
  2. Domain question bank (trade-specific)
  3. Turn-level instruction (state machine + answer quality)

State machine: background → l1_domain → l2_advanced → situational → closing
Max 8 turns total.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from groq import AsyncGroq
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class AgentTurnResponse(BaseModel):
    answer_quality: str          # "excellent" | "good" | "poor" | "no_answer"
    answer_score: int            # 0-10
    next_action: str             # "continue" | "probe_deeper" | "move_on" | "close"
    next_question_en: str
    next_question_kn: str
    next_question_primary: str   # question in candidate's preferred language
    current_stage: str
    turn_number: int
    is_complete: bool


STAGE_ORDER = ["background", "l1_domain", "l2_advanced", "situational", "closing"]
MAX_TURNS = 8

STAGE_MIN_TURNS = {
    "background": 1,
    "l1_domain": 2,
    "l2_advanced": 1,
    "situational": 1,
    "closing": 1,
}


def load_question_bank(trade: str) -> dict:
    """Load trade-specific question bank from JSON."""
    path = Path(__file__).parent.parent / "data" / "questions" / f"{trade}.json"
    if not path.exists():
        # Fallback to electrician if trade not found
        path = Path(__file__).parent.parent / "data" / "questions" / "electrician.json"
    with open(path) as f:
        return json.load(f)


def get_next_question(
    bank: dict,
    stage: str,
    used_ids: list[str],
) -> Optional[dict]:
    """Get next unused question for current stage."""
    questions = bank["questions"].get(stage, [])
    for q in questions:
        if q["id"] not in used_ids:
            return q
    return None


def determine_next_stage(
    current_stage: str,
    stage_turn_count: dict,
    answer_quality: str,
) -> str:
    """State machine: decide whether to stay or advance."""
    min_turns = STAGE_MIN_TURNS.get(current_stage, 1)
    current_count = stage_turn_count.get(current_stage, 0)

    # L2 is conditional — only if L1 was good
    if current_stage == "l1_domain" and current_count >= min_turns:
        if answer_quality in ["excellent", "good"]:
            return "l2_advanced"
        else:
            return "situational"  # Skip L2 for weak candidates

    if current_count >= min_turns:
        idx = STAGE_ORDER.index(current_stage)
        if idx < len(STAGE_ORDER) - 1:
            return STAGE_ORDER[idx + 1]

    return current_stage  # Stay in current stage


SYSTEM_PROMPT = """You are KaushalMitra (ಕೌಶಲ ಮಿತ್ರ), an expert AI interviewer for the Government of Karnataka's skill assessment program. You assess blue-collar workers for job readiness.

LANGUAGE RULES — STRICTLY FOLLOW:
- ALWAYS provide next_question_en in English
- If preferred_language is "kn": next_question_kn MUST be in Kannada script (ಕನ್ನಡ). NEVER use English in next_question_kn for kn.
- If preferred_language is "en": next_question_kn MUST be in English (same as next_question_en is fine)
- NEVER mix languages in a single field
- Be warm and respectful — this may be the candidate's first formal interview
- The candidate may answer in any language — accept all

YOUR TASK:
1. Evaluate the candidate's last answer for quality and domain knowledge
2. Decide the next interview action
3. Provide the next question in English AND in the candidate's preferred language

ANSWER QUALITY SCALE:
- excellent: Specific, correct technical knowledge, practical experience evident
- good: Mostly correct, some gaps but competent
- poor: Vague, incorrect, or very limited knowledge  
- no_answer: Candidate didn't answer or gave irrelevant response

NEXT ACTION OPTIONS:
- continue: Answer was good, proceed with next planned question
- probe_deeper: Answer needs more detail, ask a follow-up
- move_on: Answer was poor, move to next topic (don't dwell)
- close: Interview is complete

RESPOND ONLY IN THIS EXACT JSON FORMAT — no markdown, no extra text:
{
  "answer_quality": "good",
  "answer_score": 7,
  "next_action": "continue",
  "next_question_en": "Your next question in English",
  "next_question_kn": "ನಿಮ್ಮ ಮುಂದಿನ ಪ್ರಶ್ನೆ ಕನ್ನಡದಲ್ಲಿ",
  "reasoning": "Brief internal note on evaluation"
}"""


async def run_agent_turn(
    groq_api_key: str,
    trade: str,
    transcript: str,
    history: list[dict],
    session_state: dict,
    preferred_language: str = "kn",
) -> AgentTurnResponse:
    """
    Core agent turn function.

    session_state shape:
    {
        "turn_number": int,
        "current_stage": str,
        "stage_turn_counts": dict,
        "used_question_ids": list,
        "l1_score_avg": float,
    }
    """
    start = time.time()

    bank = load_question_bank(trade)

    turn_number = session_state.get("turn_number", 0) + 1
    current_stage = session_state.get("current_stage", "background")
    stage_turn_counts = session_state.get("stage_turn_counts", {})
    used_ids = session_state.get("used_question_ids", [])

    next_q = get_next_question(bank, current_stage, used_ids)
    if not next_q:
        for stage in STAGE_ORDER:
            next_q = get_next_question(bank, stage, used_ids)
            if next_q:
                current_stage = stage
                break

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    lang_instruction = {
        "kn": "MANDATORY: next_question_kn must be written in Kannada script (ಕನ್ನಡ). Do NOT use English for this field.",
        "en": "MANDATORY: next_question_kn must be in English.",
    }.get(preferred_language, "MANDATORY: next_question_kn must be in Kannada script.")

    context = f"""
INTERVIEW CONTEXT:
- Trade: {trade}
- Turn: {turn_number}/{MAX_TURNS}
- Current stage: {current_stage}
- Stage progress: {stage_turn_counts}
- Candidate preferred language: {preferred_language}
- LANGUAGE INSTRUCTION: {lang_instruction}

SUGGESTED NEXT QUESTION (use this or a natural variation):
EN: {next_q['en'] if next_q else 'Wrap up the interview gracefully'}
KN: {next_q['kn'] if next_q else 'ಸಂದರ್ಶನವನ್ನು ಮುಕ್ತಾಯಗೊಳಿಸಿ'}

CANDIDATE'S LATEST ANSWER:
"{transcript}"

Evaluate this answer and provide the next question JSON.
{"NOTE: This is the final turn — set next_action to 'close'" if turn_number >= MAX_TURNS else ""}
{"NOTE: This is turn 1 — no answer to evaluate yet, just start the interview" if turn_number == 1 else ""}
"""

    for turn in history[-4:]:
        messages.append({"role": "user", "content": turn.get("candidate", "")})
        messages.append({"role": "assistant", "content": turn.get("agent_raw", "{}")})

    messages.append({"role": "user", "content": context})

    # Call Groq
    try:
        client = AsyncGroq(api_key=groq_api_key)
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        data = json.loads(raw)

        answer_quality = data.get("answer_quality", "poor")

        stage_turn_counts[current_stage] = stage_turn_counts.get(current_stage, 0) + 1

        next_stage = determine_next_stage(
            current_stage, stage_turn_counts, answer_quality
        )

        if next_q:
            used_ids.append(next_q["id"])

        is_complete = (
            turn_number >= MAX_TURNS
            or data.get("next_action") == "close"
            or next_stage == "closing" and stage_turn_counts.get("closing", 0) >= 1
        )

        elapsed = int((time.time() - start) * 1000)
        logger.info(f"Agent turn {turn_number}: quality={answer_quality}, stage={current_stage}→{next_stage}, time={elapsed}ms")

        primary_q = data.get("next_question_kn", "ನಿಮ್ಮ ಸಮಯಕ್ಕೆ ಧನ್ಯವಾದ.")
        return AgentTurnResponse(
            answer_quality=answer_quality,
            answer_score=data.get("answer_score", 5),
            next_action=data.get("next_action", "continue"),
            next_question_en=data.get("next_question_en", "Thank you for your time."),
            next_question_kn=data.get("next_question_kn", "ನಿಮ್ಮ ಸಮಯಕ್ಕೆ ಧನ್ಯವಾದ."),
            next_question_primary=primary_q,
            current_stage=next_stage,
            turn_number=turn_number,
            is_complete=is_complete,
        )

    except json.JSONDecodeError as e:
        logger.error(f"Agent JSON parse error: {e}")
        fallback_q = next_q["kn"] if next_q else "ಧನ್ಯವಾದ, ನಾವು ಮುಗಿಸಿದ್ದೇವೆ."
        return AgentTurnResponse(
            answer_quality="poor",
            answer_score=3,
            next_action="continue",
            next_question_en=next_q["en"] if next_q else "Thank you, we are done.",
            next_question_kn=fallback_q,
            next_question_primary=fallback_q,
            current_stage=current_stage,
            turn_number=turn_number,
            is_complete=turn_number >= MAX_TURNS,
        )
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise
