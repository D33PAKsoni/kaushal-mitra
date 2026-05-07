"""
ASR Service — IndicWhisper + Whisper v3 fallback with confidence router.

Architecture:
  1. Audio bytes arrive (5-second chunk, WebM/WAV)
  2. Try IndicWhisper (HF Inference API) — primary for Kannada
  3. If language_confidence < 0.75 or error → fall back to Whisper large-v3
  4. Return transcript + language tag + confidence + model used

Day 1 Critical Check:
  Test cold-start latency of IndicWhisper immediately.
  Cold starts can be 30–60 seconds on free HF inference.
  If unacceptable, flip PRIMARY_MODEL to whisper_v3.
"""

import httpx
import time
import io
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Language confidence threshold — below this, route to fallback
CONFIDENCE_THRESHOLD = 0.75

# Timeout settings (seconds)
INDIC_WHISPER_TIMEOUT = 30.0   # HF cold start can be slow
FALLBACK_TIMEOUT = 20.0


async def transcribe_audio(
    audio_bytes: bytes,
    audio_mime: str,
    hf_token: str,
    indic_url: str,
    fallback_url: str,
    preferred_language: str = "kn",
) -> dict:
    """
    Main entry point. Returns:
    {
        "transcript": str,
        "language": "kn" | "hi" | "en",
        "confidence": float,
        "model_used": "indic_whisper" | "whisper_v3",
        "processing_time_ms": int,
    }

    IMPORTANT — language routing:
    vasista22/whisper-kannada-medium is a Kannada-ONLY fine-tune.
    When fed English/Hindi audio it hallucinates in Arabic/Urdu script.
    For preferred_language != "kn", skip IndicWhisper entirely and use
    Whisper large-v3 which handles multilingual audio correctly.
    """
    start = time.time()

    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": audio_mime,
    }

    # ── Language-aware routing ───────────────────────────
    # For non-Kannada, bypass IndicWhisper (Kannada-only model).
    if preferred_language in ("en", "hi"):
        logger.info(f"preferred_language={preferred_language} — using Whisper v3 directly")
        transcript, language, confidence, model = await _call_hf_asr(
            audio_bytes=audio_bytes,
            url=fallback_url,
            headers=headers,
            timeout=FALLBACK_TIMEOUT,
            model_name="whisper_v3",
        )
    else:
        # ── Attempt 1: IndicWhisper (Kannada) ──────────────────────────
        transcript, language, confidence, model = await _call_hf_asr(
            audio_bytes=audio_bytes,
            url=indic_url,
            headers=headers,
            timeout=INDIC_WHISPER_TIMEOUT,
            model_name="indic_whisper",
        )

        # ── Confidence Router ────────────────────────────────
        if transcript and confidence >= CONFIDENCE_THRESHOLD:
            logger.info(f"IndicWhisper success: lang={language}, conf={confidence:.2f}")
        else:
            reason = "low_confidence" if transcript else "error"
            logger.warning(
                f"IndicWhisper {reason} (conf={confidence:.2f}) — routing to Whisper v3"
            )
            transcript, language, confidence, model = await _call_hf_asr(
                audio_bytes=audio_bytes,
                url=fallback_url,
                headers=headers,
                timeout=FALLBACK_TIMEOUT,
                model_name="whisper_v3",
            )

    elapsed_ms = int((time.time() - start) * 1000)
    logger.info(f"ASR complete: model={model}, time={elapsed_ms}ms, lang={language}")

    return {
        "transcript": transcript or "",
        "language": language or preferred_language,
        "confidence": confidence,
        "model_used": model,
        "processing_time_ms": elapsed_ms,
    }


async def _call_hf_asr(
    audio_bytes: bytes,
    url: str,
    headers: dict,
    timeout: float,
    model_name: str,
) -> Tuple[str, str, float, str]:
    """
    Call a HuggingFace Inference API ASR endpoint.
    Returns: (transcript, language, confidence, model_name)
    On error returns ("", "kn", 0.0, model_name).
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, content=audio_bytes, headers=headers)

        if response.status_code == 503:
            # Model loading (cold start) — inform caller
            logger.warning(f"{model_name}: Model loading (503), cold start in progress")
            return "", "kn", 0.0, model_name

        if response.status_code != 200:
            logger.error(f"{model_name}: HTTP {response.status_code}: {response.text[:200]}")
            return "", "kn", 0.0, model_name

        data = response.json()

        # HF Whisper response format: {"text": "...", "chunks": [...]}
        transcript = data.get("text", "").strip()

        # Attempt language detection from response
        # IndicWhisper returns language in chunks[0].language if available
        language = "kn"
        confidence = 1.0

        chunks = data.get("chunks", [])
        if chunks and isinstance(chunks[0], dict):
            lang_tag = chunks[0].get("language", "kn")
            language = _normalize_language(lang_tag)

        # Estimate confidence from transcript quality
        # (HF free tier doesn't always return log_probs)
        if not transcript:
            confidence = 0.0
        elif len(transcript) < 3:
            confidence = 0.5  # Very short — uncertain

        return transcript, language, confidence, model_name

    except httpx.TimeoutException:
        logger.error(f"{model_name}: Request timed out after {timeout}s")
        return "", "kn", 0.0, model_name
    except Exception as e:
        logger.error(f"{model_name}: Unexpected error: {e}")
        return "", "kn", 0.0, model_name


def _normalize_language(lang_tag: str) -> str:
    """Normalise HF language tags to our 2-letter codes."""
    mapping = {
        "kannada": "kn",
        "kn": "kn",
        "hindi": "hi",
        "hi": "hi",
        "english": "en",
        "en": "en",
    }
    return mapping.get(lang_tag.lower(), "kn")


async def check_hf_availability(
    hf_token: str, indic_url: str, fallback_url: str
) -> dict:
    """Health check — test both endpoints with a tiny payload."""
    headers = {"Authorization": f"Bearer {hf_token}"}
    results = {}

    for name, url in [("indic_whisper", indic_url), ("whisper_v3", fallback_url)]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(url, headers=headers)
            results[name] = r.status_code != 401  # 503 = loading but auth OK
        except Exception:
            results[name] = False

    return results
