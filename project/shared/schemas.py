from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from shared.enums import IntentType, Language, TargetService
from shared.models import (
    MatchResult,
    Recommendation,
    SourceChunk,
    UserProfile,
)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class BaseAPIResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[ErrorDetail] = None


class HealthResponse(BaseModel):
    service: str
    status: str = "ok"


class IntentResult(BaseModel):
    intent: IntentType
    confidence: float = Field(..., ge=0, le=1)
    is_in_scope: bool
    needs_user_profile: bool = False
    target_service: TargetService = TargetService.NONE

    extracted_profile: Optional[UserProfile] = None
    missing_fields: List[str] = Field(default_factory=list)
    reason: Optional[str] = None


class RecommendationRequest(BaseModel):
    user_profile: UserProfile
    top_k: int = Field(default=5, ge=1, le=20)
    language: Language = Language.TR
    conversation_id: Optional[str] = None


class RecommendationResponse(BaseAPIResponse):
    answer: str
    user_profile: UserProfile

    matches: List[MatchResult] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list)
    sources: List[SourceChunk] = Field(default_factory=list)

    conversation_id: Optional[str] = None
    disclaimer: str = (
        "Bu öneriler bilgilendirme amaçlıdır; resmi uygunluk veya başvuru garantisi vermez."
    )


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)

    user_profile: Optional[UserProfile] = None
    current_matches: List[MatchResult] = Field(default_factory=list)
    current_recommendations: List[Recommendation] = Field(default_factory=list)

    conversation_id: Optional[str] = None
    language: Language = Language.TR


class ChatResponse(BaseAPIResponse):
    answer: str
    intent: Optional[IntentResult] = None

    user_profile: Optional[UserProfile] = None
    matches: List[MatchResult] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list)
    sources: List[SourceChunk] = Field(default_factory=list)

    conversation_id: Optional[str] = None
    disclaimer: str = (
        "Bu öneriler bilgilendirme amaçlıdır; resmi uygunluk veya başvuru garantisi vermez."
    )


class MatchRequest(BaseModel):
    user_profile: UserProfile
    top_k: int = Field(default=5, ge=1, le=20)


class MatchResponse(BaseAPIResponse):
    matches: List[MatchResult] = Field(default_factory=list)


class RAGGenerateRequest(BaseModel):
    user_profile: UserProfile
    matches: List[MatchResult] = Field(..., min_length=1)

    user_message: Optional[str] = None
    language: Language = Language.TR
    top_k_chunks: int = Field(default=5, ge=1, le=20)


class RAGAnswerRequest(BaseModel):
    user_message: str = Field(..., min_length=1)

    user_profile: Optional[UserProfile] = None
    current_matches: List[MatchResult] = Field(default_factory=list)

    language: Language = Language.TR
    top_k_chunks: int = Field(default=5, ge=1, le=20)


class RAGResponse(BaseAPIResponse):
    answer: str
    recommendations: List[Recommendation] = Field(default_factory=list)
    sources: List[SourceChunk] = Field(default_factory=list)


class IngestionResponse(BaseAPIResponse):
    inserted_program_count: int = 0
    inserted_chunk_count: int = 0
    skipped_program_count: int = 0
    failed_program_count: int = 0