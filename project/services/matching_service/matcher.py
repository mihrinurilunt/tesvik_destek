"""
matcher.py — Matching Service iş mantığı.

Sorumluluklar:
  1. Kural tabanlı (rule-based) filtreleme: sektör, çalışan sayısı, ciro eşiği, ihtiyaç.
  2. Keyword tabanlı semantik skor (MVP — embedding olmadan).
  3. Toplam skoru birleştir ve MatchResult listesi döndür.
"""

from __future__ import annotations

from typing import Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from shared.config import settings
from shared.exceptions import MatchingException, RetrievalException
from shared.logger import get_logger
from shared.models import MatchResult, ProgramDocument, UserProfile

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Ağırlıklar
# ---------------------------------------------------------------------------
RULE_WEIGHT: float = 0.65
SEMANTIC_WEIGHT: float = 0.35

# Kural tabanlı skor bileşenleri
SECTOR_SCORE: float = 30.0
EMPLOYEE_SCORE: float = 20.0
REVENUE_SCORE: float = 20.0
NEEDS_SCORE: float = 30.0   # ihtiyaç artık skoru etkiliyor

PROGRAMS_COLLECTION = "tesvikler_v2"


class Matcher:
    def __init__(self) -> None:
        self._qdrant: Optional[AsyncQdrantClient] = None

    def _get_qdrant(self) -> AsyncQdrantClient:
        if self._qdrant is None:
            logger.info("Initialising Qdrant client", extra={"url": settings.QDRANT_URL})
            self._qdrant = AsyncQdrantClient(url=settings.QDRANT_URL)
        return self._qdrant

    # ------------------------------------------------------------------
    # Ana akış
    # ------------------------------------------------------------------

    async def find_matches(
        self,
        user_profile: UserProfile,
        top_k: int = 5,
    ) -> list[MatchResult]:
        logger.info("Starting find_matches", extra={"top_k": top_k})

        try:
            candidates = await self._fetch_candidate_programs(limit=min(top_k * 10, 150))
        except RetrievalException:
            raise
        except Exception as exc:
            logger.exception("Failed to fetch candidate programs")
            raise RetrievalException(
                message="Qdrant'tan program adayları alınamadı.",
                details={"error": str(exc)},
            ) from exc

        if not candidates:
            logger.warning("No candidate programs found in Qdrant")
            return []

        results: list[MatchResult] = []
        for program in candidates:
            rule_score, match_reasons, missing_criteria = self._apply_rules(user_profile, program)
            semantic_score = self._compute_keyword_score(user_profile, program)
            total_score = round(rule_score * RULE_WEIGHT + semantic_score * SEMANTIC_WEIGHT, 2)

            results.append(
                MatchResult(
                    program_id=program.program_id,
                    program_name=program.program_name,
                    institution=program.institution,
                    score=total_score,
                    rule_score=round(rule_score, 2),
                    semantic_score=round(semantic_score, 2),
                    match_reasons=match_reasons,
                    missing_criteria=missing_criteria,
                    application_url=program.application_url,
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        top_results = results[:top_k]

        logger.info("find_matches completed", extra={"returned": len(top_results)})
        return top_results

    # ------------------------------------------------------------------
    # Kural tabanlı skorlama
    # ------------------------------------------------------------------

    def _apply_rules(
        self,
        user_profile: UserProfile,
        program: ProgramDocument,
    ) -> tuple[float, list[str], list[str]]:
        score: float = 0.0
        match_reasons: list[str] = []
        missing_criteria: list[str] = []

        # 1. Sektör (30 puan)
        sector_result = self._score_sector(user_profile.sector, program.sectors)
        score += sector_result["score"]
        match_reasons.extend(sector_result["reasons"])
        missing_criteria.extend(sector_result["missing"])

        # 2. Çalışan sayısı (20 puan)
        emp_score, emp_reasons, emp_missing = self._check_employee_count(user_profile.employee_count, program)
        score += emp_score
        match_reasons.extend(emp_reasons)
        missing_criteria.extend(emp_missing)

        # 3. Ciro (20 puan)
        rev_score, rev_reasons, rev_missing = self._check_revenue(user_profile.annual_revenue, program)
        score += rev_score
        match_reasons.extend(rev_reasons)
        missing_criteria.extend(rev_missing)

        # 4. İhtiyaç (30 puan) — artık skoru etkiliyor
        need_result = self._score_needs(user_profile.needs, program.needs)
        score += need_result["score"]
        match_reasons.extend(need_result["reasons"])
        missing_criteria.extend(need_result["missing"])

        # 5. Şehir (bilgi amaçlı)
        if user_profile.city and program.supported_cities:
            if not self._check_city(user_profile.city, program.supported_cities):
                missing_criteria.append(f"Şehir kısıtı olabilir: {user_profile.city}")

        return min(score, 100.0), match_reasons, missing_criteria

    def _score_sector(self, user_sector: str, program_sectors: list[str]) -> dict:
        user_lower = user_sector.lower().strip()

        # Tam eşleşme
        exact = any(user_lower in s.lower() or s.lower() in user_lower for s in program_sectors)
        if exact:
            return {"score": SECTOR_SCORE, "reasons": [f"Sektör tam uyumlu: {user_sector}"], "missing": []}

        # "Genel" veya boş — kısmi puan
        if not program_sectors or all(s.lower() in ("genel", "diğer", "tüm sektörler") for s in program_sectors):
            return {"score": SECTOR_SCORE * 0.6, "reasons": ["Program tüm sektörlere açık."], "missing": []}

        # Kısmi keyword eşleşmesi
        user_words = set(user_lower.split())
        for s in program_sectors:
            if any(w in s.lower() for w in user_words):
                return {"score": SECTOR_SCORE * 0.7, "reasons": [f"Sektör kısmen uyumlu: {s}"], "missing": []}

        return {
            "score": 0.0,
            "reasons": [],
            "missing": [f"Sektör uyumsuz. Program sektörleri: {', '.join(program_sectors)}"],
        }

    def _score_needs(self, user_needs: list[str], program_needs: list[str]) -> dict:
        if not program_needs or all(n.lower() in ("genel destek", "genel") for n in program_needs):
            return {"score": NEEDS_SCORE * 0.5, "reasons": ["Program genel ihtiyaçlara yönelik."], "missing": []}

        user_lower = {n.lower().strip() for n in user_needs}
        matched = [
            pn for pn in program_needs
            if any(pn.lower() in un or un in pn.lower() for un in user_lower)
        ]

        if not matched:
            # Keyword bazlı kısmi kontrol
            user_words = {w for n in user_lower for w in n.split()}
            partial = [pn for pn in program_needs if any(w in pn.lower() for w in user_words)]
            if partial:
                return {
                    "score": NEEDS_SCORE * 0.4,
                    "reasons": [f"İhtiyaç kısmen örtüşüyor: {', '.join(partial)}"],
                    "missing": [],
                }
            return {
                "score": 0.0,
                "reasons": [],
                "missing": [f"İhtiyaç örtüşmüyor. Program: {', '.join(program_needs)}"],
            }

        ratio = len(matched) / max(len(user_needs), 1)
        score = min(NEEDS_SCORE * (0.5 + 0.5 * ratio), NEEDS_SCORE)
        return {
            "score": score,
            "reasons": [f"İhtiyaç alanları örtüşüyor: {', '.join(matched)}"],
            "missing": [],
        }

    def _check_employee_count(self, employee_count: int, program: ProgramDocument):
        reasons, missing = [], []
        min_emp, max_emp = program.min_employee, program.max_employee

        if min_emp is None and max_emp is None:
            reasons.append("Çalışan sayısı kısıtı yok; uygun.")
            return EMPLOYEE_SCORE, reasons, missing

        if min_emp is not None and employee_count < min_emp:
            missing.append(f"Çalışan sayısı ({employee_count}) min eşiğin ({min_emp}) altında.")
            return 0.0, reasons, missing

        if max_emp is not None and employee_count > max_emp:
            missing.append(f"Çalışan sayısı ({employee_count}) max eşiği ({max_emp}) aşıyor.")
            return 0.0, reasons, missing

        reasons.append(f"Çalışan sayısı ({employee_count}) uygun aralıkta.")
        return EMPLOYEE_SCORE, reasons, missing

    def _check_revenue(self, annual_revenue: float, program: ProgramDocument):
        reasons, missing = [], []
        min_rev, max_rev = program.min_revenue, program.max_revenue

        if min_rev is None and max_rev is None:
            reasons.append("Ciro kısıtı yok; uygun.")
            return REVENUE_SCORE, reasons, missing

        if min_rev is not None and annual_revenue < min_rev:
            missing.append(f"Ciro ({annual_revenue:,.0f} TL) min eşiğin ({min_rev:,.0f} TL) altında.")
            return 0.0, reasons, missing

        if max_rev is not None and annual_revenue > max_rev:
            missing.append(f"Ciro ({annual_revenue:,.0f} TL) max eşiği ({max_rev:,.0f} TL) aşıyor.")
            return 0.0, reasons, missing

        reasons.append(f"Ciro ({annual_revenue:,.0f} TL) uygun aralıkta.")
        return REVENUE_SCORE, reasons, missing

    def _check_city(self, user_city: str, supported_cities: list[str]) -> bool:
        user_lower = user_city.lower().strip()
        return any(user_lower in c.lower() or c.lower() in user_lower for c in supported_cities)

    # ------------------------------------------------------------------
    # Keyword tabanlı semantik skor (embedding olmadan, MVP)
    # ------------------------------------------------------------------

    def _compute_keyword_score(self, user_profile: UserProfile, program: ProgramDocument) -> float:
        """
        Kullanıcı profili ile program açıklaması arasında keyword örtüşmesi hesaplar.
        0-100 aralığında döner.
        """
        profile_text = " ".join([
            user_profile.sector,
            " ".join(user_profile.needs),
            user_profile.description or "",
            user_profile.company_type or "",
        ]).lower()

        program_text = " ".join([
            program.program_name,
            program.description,
            " ".join(program.sectors),
            " ".join(program.needs),
            " ".join(program.conditions),
        ]).lower()

        profile_words = set(w for w in profile_text.split() if len(w) > 3)
        program_words = set(w for w in program_text.split() if len(w) > 3)

        if not profile_words:
            return 0.0

        overlap = profile_words & program_words
        score = len(overlap) / len(profile_words) * 100
        return round(min(score, 100.0), 2)

    # ------------------------------------------------------------------
    # Qdrant'tan program çekme
    # ------------------------------------------------------------------


    async def _fetch_candidate_programs(self, limit: int = 100) -> list[ProgramDocument]:
        import json
        try:
            qdrant = self._get_qdrant()
            records, _ = await qdrant.scroll(
                collection_name=PROGRAMS_COLLECTION,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            programs: list[ProgramDocument] = []
            for record in records:
                payload = record.payload
                if not payload:
                    continue

                try:
                    # 1. 'description' eksikse veya boşsa döküman metninden elde edelim
                    if "description" not in payload or not payload.get("description"):
                        raw_text = payload.get("text")
                        if not raw_text and "_node_content" in payload:
                            try:
                                node_data = json.loads(payload["_node_content"])
                                raw_text = node_data.get("text", "")
                            except Exception:
                                raw_text = payload["_node_content"]
                        payload["description"] = raw_text or f"{payload.get('program_name')} programı resmi analiz dökümanıdır."

                    # Minimum 10 karakter sınırını garanti altına alalım
                    if len(str(payload["description"])) < 10:
                        payload["description"] = str(payload["description"]) + " (Detaylı döküman içeriği)"

                    # 2. URL validation hatalarını önlemek için geçersiz URL'leri temizleyelim
                    from pydantic import TypeAdapter, HttpUrl
                    for url_field in ["application_url", "source_url"]:
                        if url_field in payload and payload[url_field]:
                            try:
                                ta = TypeAdapter(HttpUrl)
                                ta.validate_python(payload[url_field])
                            except Exception:
                                payload[url_field] = None

                    # 3. Gerekli liste alanlarının varsayılan değerlerini atayalım
                    for list_field in ["sectors", "needs", "supported_cities", "conditions", "required_documents", "application_steps"]:
                        if list_field not in payload:
                            payload[list_field] = []

                    # 4. extra="forbid" kısıtı nedeniyle şemada olmayan alanları (text, _node_content vb.) temizleyelim
                    valid_keys = ProgramDocument.model_fields.keys()
                    filtered_payload = {k: v for k, v in payload.items() if k in valid_keys}

                    # 5. ProgramDocument modeline dönüştürelim
                    programs.append(ProgramDocument(**filtered_payload))

                except Exception as parse_exc:
                    logger.warning(
                        "Failed to parse ProgramDocument",
                        extra={"record_id": record.id, "error": str(parse_exc)},
                    )

            logger.info("Fetched programs from Qdrant", extra={"count": len(programs)})
            return programs

        except UnexpectedResponse as exc:
            raise RetrievalException(
                message="Qdrant programları döndüremedi.",
                details={"collection": PROGRAMS_COLLECTION, "error": str(exc)},
            ) from exc
