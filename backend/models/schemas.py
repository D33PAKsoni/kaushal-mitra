"""
Pydantic schemas for KaushalMitra API.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid



class TranscribeResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    transcript: str
    language: str  # "kn", "hi", "en"
    confidence: float = Field(ge=0.0, le=1.0)
    model_used: Literal["indic_whisper", "whisper_v3"]
    processing_time_ms: int


class ASRHealthResponse(BaseModel):
    status: str
    indic_whisper_available: bool
    fallback_available: bool



class SessionCreateRequest(BaseModel):
    candidate_name: str
    trade: Literal["electrician", "plumber"]
    district: str
    preferred_language: Literal["kn", "hi", "en"] = "kn"


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str
    message_kannada: str = "ಸೆಷನ್ ಪ್ರಾರಂಭವಾಗಿದೆ"



class CandidateRecord(BaseModel):
    id: str
    name: str
    trade: str
    district: str
    language: str
    session_id: str
    created_at: datetime
    fitment_category: Optional[str] = None
    composite_score: Optional[float] = None
    integrity_score: Optional[float] = None
    is_flagged: bool = False
    flag_reason: Optional[str] = None



class AdminCandidateRow(BaseModel):
    session_id: str
    name: str
    trade: str
    district: str
    language: str
    fitment_category: Optional[str]
    composite_score: Optional[float]
    integrity_score: Optional[float]
    is_flagged: bool
    created_at: str
