"""
ProgramMatcher — kural tabanlı ve semantik skorları birleştirerek
nihai MatchResult döndürür.

Ağırlıklar (sistem rolü gereksinimlerine göre):
    rule_score     → 40%
    semantic_score → 60%
"""

from __future__ import annotations

import json

from schemas import MatchRequest, MatchResult, ProgramData, UserProfile
from scoring import RuleBasedScorer, SemanticScorer

RULE_WEIGHT = 0.40
SEMANTIC_WEIGHT = 0.60


class ProgramMatcher:
    def __init__(self) -> None:
        self._rule_scorer = RuleBasedScorer()
        self._semantic_scorer = SemanticScorer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def match(self, request: MatchRequest) -> MatchResult:
        """Tek bir (profil, program) çifti için eşleştirme skoru üretir."""
        return self._compute(request.user_profile, request.program_data)

    def match_raw(self, user_profile: dict, program_data: dict) -> dict:
        """
        Ham dict girdisi kabul eder; dict olarak döner.
        Gateway / FastAPI endpoint'lerinden doğrudan çağrılabilir.
        """
        profile = UserProfile(**user_profile)
        program = ProgramData(**program_data)
        result = self._compute(profile, program)
        return result.model_dump()

    def match_json(self, user_profile: dict, program_data: dict) -> str:
        """Sistem rolü çıktı formatına uygun, sadece JSON string döner."""
        return json.dumps(self.match_raw(user_profile, program_data), ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _compute(self, profile: UserProfile, program: ProgramData) -> MatchResult:
        rule_score, rule_reasons = self._rule_scorer.score(profile, program)
        semantic_score, semantic_reasons = self._semantic_scorer.score(profile, program)

        combined_score = round(
            RULE_WEIGHT * rule_score + SEMANTIC_WEIGHT * semantic_score, 4
        )

        all_reasons = rule_reasons + semantic_reasons

        return MatchResult(
            program_id=program.program_id,
            program_name=program.program_name,
            institution=program.institution,
            score=combined_score,
            rule_score=rule_score,
            semantic_score=semantic_score,
            match_reasons=all_reasons,
            application_url=program.application_url,
        )