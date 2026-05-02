"""
ASR Router — POST /asr/transcribe
Accepts audio file upload, returns Kannada transcript.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
import logging

from services.asr_service import transcribe_audio, check_hf_availability
from models.schemas import TranscribeResponse, ASRHealthResponse
from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Allowed audio MIME types from MediaRecorder
ALLOWED_MIME_TYPES = {
    "audio/webm",
    "audio/webm;codecs=opus",
    "audio/ogg",
    "audio/ogg;codecs=opus",
    "audio/wav",
    "audio/mpeg",
    "audio/mp4",
    "application/octet-stream",  # Some browsers send this
}

# Max audio chunk size: 5 seconds at 128kbps ≈ 80KB, allow up to 2MB
MAX_AUDIO_BYTES = 2 * 1024 * 1024


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    audio: UploadFile = File(..., description="5-second audio chunk from MediaRecorder"),
):
    """
    Transcribe an audio chunk using IndicWhisper (Kannada) with Whisper v3 fallback.

    - Accepts WebM, OGG, WAV audio (5-second chunks from MediaRecorder)
    - Uses IndicWhisper for Kannada; falls back to Whisper v3 for Hindi/English or low confidence
    - Returns transcript, detected language, confidence, and model used
    """
    if not settings.HF_API_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="HF_API_TOKEN not configured. Add it to your .env file.",
        )

    # Validate content type
    content_type = audio.content_type or "application/octet-stream"
    # Strip quality parameters like ;codecs=opus for basic check
    base_type = content_type.split(";")[0].strip()
    if base_type not in {m.split(";")[0] for m in ALLOWED_MIME_TYPES}:
        logger.warning(f"Unexpected MIME type received: {content_type} — proceeding anyway")

    # Read audio bytes
    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file received.")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Audio too large ({len(audio_bytes)} bytes). Max 2MB per chunk.",
        )

    logger.info(
        f"ASR request: {len(audio_bytes)} bytes, mime={content_type}, file={audio.filename}"
    )

    result = await transcribe_audio(
        audio_bytes=audio_bytes,
        audio_mime=content_type,
        hf_token=settings.HF_API_TOKEN,
        indic_url=settings.HF_INDIC_WHISPER_URL,
        fallback_url=settings.HF_WHISPER_FALLBACK_URL,
    )

    return TranscribeResponse(
        transcript=result["transcript"],
        language=result["language"],
        confidence=result["confidence"],
        model_used=result["model_used"],
        processing_time_ms=result["processing_time_ms"],
    )


@router.get("/health", response_model=ASRHealthResponse)
async def asr_health():
    """
    Check availability of ASR endpoints.
    Day 1 critical: use this to measure IndicWhisper cold-start latency.
    """
    if not settings.HF_API_TOKEN:
        return ASRHealthResponse(
            status="degraded — HF_API_TOKEN missing",
            indic_whisper_available=False,
            fallback_available=False,
        )

    availability = await check_hf_availability(
        hf_token=settings.HF_API_TOKEN,
        indic_url=settings.HF_INDIC_WHISPER_URL,
        fallback_url=settings.HF_WHISPER_FALLBACK_URL,
    )

    all_ok = all(availability.values())
    return ASRHealthResponse(
        status="ok" if all_ok else "partial",
        indic_whisper_available=availability.get("indic_whisper", False),
        fallback_available=availability.get("whisper_v3", False),
    )


@router.post("/test-latency")
async def test_latency():
    """
    Day 1 diagnostic: measure raw cold-start latency of IndicWhisper.
    Call this first thing on Day 1 morning before anything else.
    """
    import time, httpx

    if not settings.HF_API_TOKEN:
        raise HTTPException(status_code=503, detail="HF_API_TOKEN not set")

    # Minimal silent WAV (44 bytes — valid but empty audio)
    silent_wav = bytes([
        0x52, 0x49, 0x46, 0x46, 0x24, 0x00, 0x00, 0x00,  # RIFF header
        0x57, 0x41, 0x56, 0x45, 0x66, 0x6D, 0x74, 0x20,  # WAVE fmt
        0x10, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,  # PCM, mono
        0x44, 0xAC, 0x00, 0x00, 0x88, 0x58, 0x01, 0x00,  # 44100 Hz
        0x02, 0x00, 0x10, 0x00, 0x64, 0x61, 0x74, 0x61,  # 16-bit
        0x00, 0x00, 0x00, 0x00,                          # data chunk
    ])

    results = {}
    for model_name, url in [
        ("indic_whisper", settings.HF_INDIC_WHISPER_URL),
        ("whisper_v3", settings.HF_WHISPER_FALLBACK_URL),
    ]:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                r = await client.post(
                    url,
                    content=silent_wav,
                    headers={
                        "Authorization": f"Bearer {settings.HF_API_TOKEN}",
                        "Content-Type": "audio/wav",
                    },
                )
            elapsed = int((time.time() - start) * 1000)
            results[model_name] = {
                "status_code": r.status_code,
                "latency_ms": elapsed,
                "note": "Model loading" if r.status_code == 503 else "Available",
            }
        except Exception as e:
            results[model_name] = {"error": str(e)}

    recommendation = (
        "✅ IndicWhisper is fast — use as primary"
        if results.get("indic_whisper", {}).get("latency_ms", 9999) < 5000
        else "⚠️  IndicWhisper cold start slow — consider Whisper v3 as primary for demo day"
    )

    return {"latency_results": results, "recommendation": recommendation}
