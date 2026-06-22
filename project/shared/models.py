from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class UserProfile(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    sector: str = Field(..., min_length=2, max_length=100, description="Şirket sektörü")
    employee_count: int = Field(..., ge=0, description="Çalışan sayısı")
    annual_revenue: float = Field(..., ge=0, description="Yıllık ciro")
    needs: list[str] = Field(..., min_length=1, description="İhtiyaç alanları")
    city: str | None = Field(default=None, max_length=100, description="Şehir")
    company_type: str | None = Field(
        default=None,
        max_length=50,
        description="Şirket tipi (örn. Limited, Anonim, Şahıs)",
    )

    @field_validator("needs")
    @classmethod
    def validate_needs(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("needs alanı en az bir geçerli değer içermelidir.")
        return cleaned


class ProgramDocument(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    program_id: str = Field(..., min_length=1, max_length=100)
    program_name: str = Field(..., min_length=2, max_length=300)
    institution: str = Field(..., min_length=2, max_length=150)
    description: str = Field(..., min_length=10)
    application_url: HttpUrl

    sectors: list[str] = Field(..., min_length=1)
    needs: list[str] = Field(..., min_length=1)

    conditions: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    application_steps: list[str] = Field(default_factory=list)

    min_employee: int | None = Field(default=None, ge=0)
    max_employee: int | None = Field(default=None, ge=0)
    min_revenue: float | None = Field(default=None, ge=0)
    max_revenue: float | None = Field(default=None, ge=0)
    max_amount: float | None = Field(default=None, ge=0)

    supported_cities: list[str] = Field(default_factory=list)
    source_url: HttpUrl | None = None
    last_updated: str | None = Field(
        default=None,
        description="Kaynağın son güncellenme tarihi. Şimdilik string tutuldu.",
    )

    @field_validator("sectors", "needs", "conditions", "required_documents", "application_steps", "supported_cities")
    @classmethod
    def clean_string_lists(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]


class MatchResult(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    program_id: str = Field(..., min_length=1, max_length=100)
    program_name: str = Field(..., min_length=2, max_length=300)
    institution: str = Field(..., min_length=2, max_length=150)
    score: float = Field(..., ge=0, le=100)

    rule_score: float | None = Field(default=None, ge=0, le=100)
    semantic_score: float | None = Field(default=None, ge=0, le=100)
    match_reasons: list[str] = Field(default_factory=list)
    application_url: HttpUrl | None = None

    @field_validator("match_reasons")
    @classmethod
    def clean_match_reasons(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]


class Recommendation(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    program_id: str = Field(..., min_length=1, max_length=100)
    program_name: str = Field(..., min_length=2, max_length=300)
    institution: str = Field(..., min_length=2, max_length=150)
    score: float = Field(..., ge=0, le=100)

    summary: str = Field(..., min_length=10)
    why_matched: list[str] = Field(default_factory=list)
    application_steps: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)

    application_url: HttpUrl
    disclaimer: str = Field(..., min_length=10)
    source_urls: list[HttpUrl] = Field(default_factory=list)

    @field_validator("why_matched", "application_steps", "required_documents")
    @classmethod
    def clean_recommendation_lists(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]


class HealthCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str
    status: str
    version: str | None = None
    dependencies: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool = False
    error_code: str
    message: str
    details: dict[str, Any] | None = None