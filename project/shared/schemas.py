from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from shared.models import (
    UserProfile,
    ProgramDocument,
    ProgramChunk,
    MatchResult,
    Recommendation,
)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class BaseAPIResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[ErrorDetail] = None


class MatchRequest(BaseModel):
    user_profile: UserProfile
    top_k: int = Field(default=5, ge=1, le=20)


class MatchResponse(BaseAPIResponse):
    matches: List[MatchResult] = Field(default_factory=list)


class RAGRequest(BaseModel):
    user_profile: UserProfile
    matches: List[MatchResult] = Field(..., min_length=1)
    language: str = Field(default="tr")
    top_k_chunks: int = Field(default=5, ge=1, le=20)


class RAGResponse(BaseAPIResponse):
    recommendations: List[Recommendation] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    user_profile: UserProfile
    top_k: int = Field(default=5, ge=1, le=20)


class RecommendationResponse(BaseAPIResponse):
    recommendations: List[Recommendation] = Field(default_factory=list)
    

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    program_name: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)


class IngestionProgramRequest(BaseModel):
    programs: List[ProgramDocument]


class IngestionProgramResponse(BaseAPIResponse):
    inserted_program_count: int = 0
    inserted_chunk_count: int = 0


class ChunkUploadRequest(BaseModel):
    chunks: List[ProgramChunk]


class ChunkUploadResponse(BaseAPIResponse):
    inserted_chunk_count: int = 0


class HealthResponse(BaseModel):
    service: str
    status: str = "ok"