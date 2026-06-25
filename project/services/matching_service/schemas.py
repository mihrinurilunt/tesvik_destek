from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Any


# ---------------------------------------------------------------------------
# Kullanıcı Profili (API girdisi)
# ---------------------------------------------------------------------------

class UserProfile(BaseModel):
    sector: str = Field(..., example="Yazılım")
    employee_count: int = Field(..., example=15)
    annual_revenue: float = Field(..., example=500000.0)
    needs: List[str] = Field(..., example=["AR-GE", "hibe", "vergi indirimi"])
    city: Optional[str] = Field(None, example="İstanbul")
    company_type: Optional[str] = Field(None, example="Limited")


# ---------------------------------------------------------------------------
# Program Verisi — output.json yapısına uygun
# ---------------------------------------------------------------------------

class Section(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    links: Optional[List[Any]] = None


class ProgramData(BaseModel):
    """output.json'dan gelen ham yapıyı temsil eder."""
    program_id: str = ""
    program_name: Optional[str] = None
    institution: str = ""
    url: Optional[str] = None
    source: Optional[str] = None
    scraped_at: Optional[str] = None
    sections: List[Section] = Field(default_factory=list)

    # Kural tabanlı scorer için opsiyonel alanlar (JSON'da yoksa None kalır)
    target_sectors: List[str] = Field(default_factory=list)
    min_revenue: Optional[float] = None
    max_revenue: Optional[float] = None
    min_employees: Optional[int] = None
    max_employees: Optional[int] = None

    @model_validator(mode="after")
    def fill_derived_fields(self):
        # program_id: url'den türet
        if not self.program_id and self.url:
            self.program_id = self.url.split("/")[-1] or self.url

        # institution: source'dan türet
        if not self.institution and self.source:
            SOURCE_LABELS = {
                "kosgeb": "KOSGEB",
                "tubitak": "TÜBİTAK",
                "teydeb": "TÜBİTAK TEYDEB",
                "tkdk": "TKDK",
            }
            self.institution = SOURCE_LABELS.get(self.source.lower(), self.source.upper())

        # program_name: None ise boş string yap
        if self.program_name is None:
            self.program_name = ""

        return self

    @property
    def purpose(self) -> str:
        """Semantik karşılaştırma için sections'tan amaç metnini çıkar."""
        PURPOSE_TITLES = {"programın amacı", "amaç", "programın amacı ve kapsamı",
                          "programın amacı ve gerekçesi", "programin kapsami ve amaci",
                          "amaç ve kapsam"}
        texts = []
        for s in self.sections:
            title = (s.title or "").strip().lower()
            if title in PURPOSE_TITLES and s.content:
                texts.append(s.content)
        # Amaç bölümü yoksa tüm section içeriklerini birleştir
        if not texts:
            texts = [s.content for s in self.sections if s.content]
        return " ".join(texts)

    @property
    def application_url(self) -> str:
        return self.url or ""


# ---------------------------------------------------------------------------
# API İstek / Yanıt modelleri
# ---------------------------------------------------------------------------

class MatchRequest(BaseModel):
    user_profile: UserProfile
    program_data: ProgramData


class MatchResult(BaseModel):
    program_id: str
    program_name: str
    institution: str
    score: float = Field(..., ge=0.0, le=1.0)
    rule_score: Optional[float] = None
    semantic_score: Optional[float] = None
    match_reasons: Optional[List[str]] = None
    application_url: Optional[str] = None