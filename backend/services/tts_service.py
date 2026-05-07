"""
TTS Service — Bhashini API (primary) + fallback signal for Web Speech API.

Architecture:
- Backend attempts Bhashini TTS → returns audio bytes
- If Bhashini fails/not configured → returns {"use_browser_tts": true}
- Frontend falls back to Web Speech API with lang=kn-IN

Bhashini API: https://bhashini.gov.in/ulca
"""

import httpx
import logging
import base64

logger = logging.getLogger(__name__)

BHASHINI_TTS_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

# Bhashini pipeline config for Kannada TTS
BHASHINI_PIPELINE = {
    "pipelineTasks": [
        {
            "taskType": "tts",
            "config": {
                "language": {"sourceLanguage": "kn"},
                "serviceId": "ai4bharat/indic-tts-coqui-kannada-gpu--t4",
                "gender": "female",
                "samplingRate": 8000,
            },
        }
    ]
}


async def synthesize_kannada(
    text: str,
    bhashini_api_key: str,
    bhashini_user_id: str,
) -> dict:
    """
    Synthesize Kannada text to speech.

    Returns:
      {"audio_base64": str, "source": "bhashini"} on success
      {"use_browser_tts": True, "text": str} on failure/not configured
    """
    if not bhashini_api_key or not bhashini_user_id:
        logger.info("Bhashini not configured — signalling browser TTS fallback")
        return {"use_browser_tts": True, "text": text}

    payload = {
        **BHASHINI_PIPELINE,
        "inputData": {
            "input": [{"source": text}]
        },
    }

    headers = {
        "userID": bhashini_user_id,
        "ulcaApiKey": bhashini_api_key,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(BHASHINI_TTS_URL, json=payload, headers=headers)

        if r.status_code != 200:
            logger.warning(f"Bhashini TTS failed: {r.status_code} — using browser fallback")
            return {"use_browser_tts": True, "text": text}

        data = r.json()
        # Extract audio from Bhashini response
        audio_content = (
            data.get("pipelineResponse", [{}])[0]
            .get("audio", [{}])[0]
            .get("audioContent", "")
        )

        if not audio_content:
            logger.warning("Bhashini returned empty audio — using browser fallback")
            return {"use_browser_tts": True, "text": text}

        logger.info(f"Bhashini TTS success: {len(audio_content)} chars base64")
        return {"audio_base64": audio_content, "source": "bhashini"}

    except Exception as e:
        logger.error(f"Bhashini TTS error: {e}")
        return {"use_browser_tts": True, "text": text}
