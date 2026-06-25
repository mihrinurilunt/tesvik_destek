"""
tests/matching/test_matcher.py

Matching servisinin birim testleri.
Çalıştırmak için: pytest tests/matching/
"""

import json
import sys
import os

# Proje kökünü path'e ekle (docker/CI ortamında da çalışır)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.matching_service import ProgramMatcher
from services.matching_service.schemas import MatchRequest, ProgramData, UserProfile
from services.matching_service.scoring import RuleBasedScorer, SemanticScorer


# ---------------------------------------------------------------------------
# Fikstürler
# ---------------------------------------------------------------------------

SAMPLE_PROFILE = {
    "name": "Tekno Yazılım Ltd. Şti.",
    "sector": "Yazılım ve Bilişim",
    "employee_count": 25,
    "annual_revenue": 1500000.0,
    "city": "İstanbul",
    "company_type": None,
    "needs": [
        "Bulut tabanlı e-ticaret altyapısı geliştirme",
        "Ar-Ge desteği ve yazılım entegrasyonu"
    ]
}

SAMPLE_PROGRAM = {
    "program_id": "TUBITAK-1507",
    "program_name": "TÜBİTAK 1507 KOBİ Ar-Ge Başlangıç Destek Programı",
    "institution": "TÜBİTAK",
    "target_sectors": ["Yazılım", "Teknoloji", "Bilişim"],
    "min_revenue": None,
    "max_revenue": 50_000_000,
    "min_employees": 1,
    "max_employees": 250,
    "purpose": "KOBİ'lerin Ar-Ge proje kapasitesini artırmak, teknoloji tabanlı "
               "ürün geliştirme süreçlerini desteklemek ve yenilikçi yazılım "
               "çözümlerinin ticarileşmesine katkı sağlamak.",
    "application_url": "https://e-bideb.tubitak.gov.tr",
}


# ---------------------------------------------------------------------------
# Testler
# ---------------------------------------------------------------------------

class TestRuleBasedScorer:
    def setup_method(self):
        self.scorer = RuleBasedScorer()
        self.profile = UserProfile(**SAMPLE_PROFILE)
        self.program = ProgramData(**SAMPLE_PROGRAM)

    def test_score_range(self):
        score, _ = self.scorer.score(self.profile, self.program)
        assert 0.0 <= score <= 1.0

    def test_matching_sector_gives_score(self):
        score, reasons = self.scorer.score(self.profile, self.program)
        assert score > 0
        assert any("sektör" in r.lower() for r in reasons)

    def test_non_matching_sector_reduces_score(self):
        low_profile = UserProfile(**{**SAMPLE_PROFILE, "sector": "Tarım"})
        score_low, _ = self.scorer.score(low_profile, self.program)
        score_high, _ = self.scorer.score(self.profile, self.program)
        assert score_low < score_high

    def test_revenue_within_range(self):
        score, reasons = self.scorer.score(self.profile, self.program)
        assert any("ciro" in r.lower() for r in reasons)

    def test_revenue_out_of_range_reduces_score(self):
        rich_profile = UserProfile(**{**SAMPLE_PROFILE, "annual_revenue": 100_000_000})
        score_rich, _ = self.scorer.score(rich_profile, self.program)
        score_ok, _ = self.scorer.score(self.profile, self.program)
        assert score_rich < score_ok


class TestSemanticScorer:
    def setup_method(self):
        self.scorer = SemanticScorer()
        self.profile = UserProfile(**SAMPLE_PROFILE)
        self.program = ProgramData(**SAMPLE_PROGRAM)

    def test_score_range(self):
        score, _ = self.scorer.score(self.profile, self.program)
        assert 0.0 <= score <= 1.0

    def test_similar_texts_give_higher_score(self):
        related_profile = UserProfile(
            **{
                **SAMPLE_PROFILE,
                "needs": "Ar-Ge hibe desteği, teknoloji geliştirme, yazılım projesi",
            }
        )
        unrelated_profile = UserProfile(
            **{**SAMPLE_PROFILE, "needs": "Tarım sulama sistemi kurulum desteği"}
        )
        score_related, _ = self.scorer.score(related_profile, self.program)
        score_unrelated, _ = self.scorer.score(unrelated_profile, self.program)
        assert score_related > score_unrelated

    def test_returns_reason_string(self):
        _, reasons = self.scorer.score(self.profile, self.program)
        assert len(reasons) == 1
        assert isinstance(reasons[0], str)


class TestProgramMatcher:
    def setup_method(self):
        self.matcher = ProgramMatcher()

    def test_match_returns_valid_result(self):
        result = self.matcher.match_raw(SAMPLE_PROFILE, SAMPLE_PROGRAM)
        assert "score" in result
        assert 0.0 <= result["score"] <= 1.0
        assert result["program_id"] == "TUBITAK-1507"

    def test_match_json_is_valid_json(self):
        json_str = self.matcher.match_json(SAMPLE_PROFILE, SAMPLE_PROGRAM)
        parsed = json.loads(json_str)
        assert parsed["program_id"] == "TUBITAK-1507"
        assert isinstance(parsed["match_reasons"], list)

    def test_score_weights(self):
        """Combined score = 0.4 * rule + 0.6 * semantic kontrolü."""
        result = self.matcher.match_raw(SAMPLE_PROFILE, SAMPLE_PROGRAM)
        expected = round(0.4 * result["rule_score"] + 0.6 * result["semantic_score"], 4)
        assert abs(result["score"] - expected) < 1e-6

    def test_output_keys_match_schema(self):
        required_keys = {
            "program_id", "program_name", "institution",
            "score", "rule_score", "semantic_score",
            "match_reasons", "application_url",
        }
        result = self.matcher.match_raw(SAMPLE_PROFILE, SAMPLE_PROGRAM)
        assert required_keys.issubset(result.keys())

    def test_match_reasons_non_empty(self):
        result = self.matcher.match_raw(SAMPLE_PROFILE, SAMPLE_PROGRAM)
        assert len(result["match_reasons"]) > 0