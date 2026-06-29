from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class UserProfile(BaseModel):
    """
    Formdan veya chat içinden gelen şirket/kullanıcı bilgisidir.
    Matching service bu modeli kullanarak uygun destekleri bulur.
    RAG service de cevabı kişiselleştirmek için bu modeli kullanır.
    """

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
        description="Şirket tipi: Limited, Anonim, Şahıs vb.",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Kullanıcının serbest açıklaması veya proje ihtiyacı",
    )

    @field_validator("needs")
    @classmethod
    def validate_needs(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("needs alanı en az bir geçerli değer içermelidir.")
        return cleaned


class ProgramDocument(BaseModel):
    """
    Sisteme yüklenen teşvik/destek programının ana modelidir.
    Ingestion service bu modeli işler, chunklara böler ve Qdrant'a yükler.
    Matching service de bu alanlara göre kullanıcı profiliyle karşılaştırma yapabilir.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    program_id: str = Field(..., min_length=1, max_length=100)
    program_name: str = Field(..., min_length=2, max_length=300)
    institution: str = Field(..., min_length=2, max_length=150)
    description: str = Field(..., min_length=10)

    application_url: HttpUrl | None = None
    source_url: HttpUrl | None = None
    source_file: str | None = Field(default=None, max_length=300)

    sectors: list[str] = Field(default_factory=list)
    needs: list[str] = Field(default_factory=list)
    supported_cities: list[str] = Field(default_factory=list)

    conditions: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    application_steps: list[str] = Field(default_factory=list)

    min_employee: int | None = Field(default=None, ge=0)
    max_employee: int | None = Field(default=None, ge=0)
    min_revenue: float | None = Field(default=None, ge=0)
    max_revenue: float | None = Field(default=None, ge=0)
    max_amount: float | None = Field(default=None, ge=0)

    last_updated: str | None = Field(
        default=None,
        description="Kaynağın son güncellenme tarihi. MVP için string tutulabilir.",
    )

    @field_validator(
        "sectors",
        "needs",
        "supported_cities",
        "conditions",
        "required_documents",
        "application_steps",
    )
    @classmethod
    def clean_string_lists(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]

    @field_validator("max_employee")
    @classmethod
    def validate_employee_range(cls, value: int | None, info) -> int | None:
        min_employee = info.data.get("min_employee")
        if value is not None and min_employee is not None and value < min_employee:
            raise ValueError("max_employee, min_employee değerinden küçük olamaz.")
        return value

    @field_validator("max_revenue")
    @classmethod
    def validate_revenue_range(cls, value: float | None, info) -> float | None:
        min_revenue = info.data.get("min_revenue")
        if value is not None and min_revenue is not None and value < min_revenue:
            raise ValueError("max_revenue, min_revenue değerinden küçük olamaz.")
        return value


class ProgramChunk(BaseModel):
    """
    ProgramDocument içeriğinin RAG için bölünmüş küçük parçasıdır.
    Qdrant'a bu chunklar embedding ile yüklenir.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    chunk_id: str = Field(..., min_length=1, max_length=150)
    program_id: str = Field(..., min_length=1, max_length=100)
    program_name: str | None = Field(default=None, max_length=300)

    text: str = Field(..., min_length=10)
    source_file: str | None = Field(default=None, max_length=300)
    source_url: HttpUrl | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)


class MatchResult(BaseModel):
    """
    Matching service'in döndürdüğü teknik eşleşme sonucudur.
    Kullanıcıya gösterilecek son açıklama değildir.
    RAG service bu sonucu alıp açıklamalı Recommendation üretir.
    """

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
    missing_criteria: list[str] = Field(default_factory=list)

    application_url: HttpUrl | None = None

    @field_validator("match_reasons", "missing_criteria")
    @classmethod
    def clean_match_lists(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]


class SourceChunk(BaseModel):
    """
    RAG cevabının hangi chunklara dayandığını gösterir.
    Frontend kaynak göstermek isterse bu modeli kullanır.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    chunk_id: str = Field(..., min_length=1, max_length=150)
    program_id: str | None = Field(default=None, max_length=100)
    program_name: str | None = Field(default=None, max_length=300)

    text: str = Field(..., min_length=10)
    score: float | None = Field(default=None, ge=0)
    source_file: str | None = Field(default=None, max_length=300)
    source_url: HttpUrl | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)


class Recommendation(BaseModel):
    """
    Kullanıcıya gösterilecek nihai öneridir.
    Matching sonucu teknik skor verir; Recommendation ise RAG tarafından açıklanmış kullanıcı dostu sonuçtur.
    """

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
    eligibility_notes: list[str] = Field(default_factory=list)
    application_steps: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)

    application_url: HttpUrl | None = None
    source_urls: list[HttpUrl] = Field(default_factory=list)
    sources: list[SourceChunk] = Field(default_factory=list)

    disclaimer: str = Field(
        default="Bu öneriler bilgilendirme amaçlıdır; resmi uygunluk veya başvuru garantisi vermez.",
        min_length=10,
    )

    @field_validator(
        "why_matched",
        "eligibility_notes",
        "application_steps",
        "required_documents",
    )
    @classmethod
    def clean_recommendation_lists(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]