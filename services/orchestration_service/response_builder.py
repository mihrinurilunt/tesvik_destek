from __future__ import annotations

from shared.constants import (
    DEFAULT_DISCLAIMER,
    GENERAL_INFO_MESSAGE,
    GREETING_MESSAGE,
    NO_MATCH_MESSAGE,
    NO_RAG_CONTEXT_MESSAGE,
    OUT_OF_SCOPE_MESSAGE,
    UNKNOWN_INTENT_MESSAGE,
)
from shared.enums import IntentType
from shared.models import MatchResult, Recommendation, SourceChunk, UserProfile
from shared.schemas import (
    ChatRequest,
    ChatResponse,
    IntentResult,
    RecommendationRequest,
    RecommendationResponse,
    RAGResponse,
)


def build_recommendation_response(
    request: RecommendationRequest,
    matches: list[MatchResult],
    rag_response: RAGResponse | None = None,
) -> RecommendationResponse:
    """
    /recommend endpointi için başarılı response üretir.

    Kullanım:
    Formdan gelen profil bilgisiyle önce matching çalışır.
    Match varsa RAG service bu matchleri açıklamalı öneriye çevirir.
    Bu fonksiyon da frontend'e tek bir RecommendationResponse döner.
    """

    recommendations = rag_response.recommendations if rag_response else []
    sources = rag_response.sources if rag_response else []
    answer = (
        rag_response.answer
        if rag_response and rag_response.answer
        else "Verdiğiniz bilgilere göre işletmeniz için uygun destekleri listeledim."
    )

    return RecommendationResponse(
        success=True,
        message="Recommendation generated successfully.",
        error=None,
        answer=answer,
        user_profile=request.user_profile,
        matches=matches,
        recommendations=recommendations,
        sources=sources,
        conversation_id=request.conversation_id,
        disclaimer=DEFAULT_DISCLAIMER,
    )


def build_no_match_response(
    request: RecommendationRequest,
) -> RecommendationResponse:
    """
    /recommend akışında matching service hiç uygun destek bulamazsa kullanılır.
    """

    return RecommendationResponse(
        success=True,
        message="No matching program found.",
        error=None,
        answer=NO_MATCH_MESSAGE,
        user_profile=request.user_profile,
        matches=[],
        recommendations=[],
        sources=[],
        conversation_id=request.conversation_id,
        disclaimer=DEFAULT_DISCLAIMER,
    )


def build_greeting_response(
    request: ChatRequest,
    intent: IntentResult,
) -> ChatResponse:
    """
    Kullanıcı sadece selam verdiğinde kullanılır.
    RAG veya matching çağrılmaz.
    """

    return ChatResponse(
        success=True,
        message="Greeting handled successfully.",
        error=None,
        answer=GREETING_MESSAGE,
        intent=intent,
        user_profile=request.user_profile,
        matches=request.current_matches,
        recommendations=request.current_recommendations,
        sources=[],
        conversation_id=request.conversation_id,
        disclaimer=DEFAULT_DISCLAIMER,
    )


def build_general_info_response(
    request: ChatRequest,
    intent: IntentResult,
) -> ChatResponse:
    """
    Kullanıcı sistemin ne işe yaradığını veya nasıl çalıştığını sorarsa kullanılır.
    """

    return ChatResponse(
        success=True,
        message="General info handled successfully.",
        error=None,
        answer=GENERAL_INFO_MESSAGE,
        intent=intent,
        user_profile=request.user_profile,
        matches=request.current_matches,
        recommendations=request.current_recommendations,
        sources=[],
        conversation_id=request.conversation_id,
        disclaimer=DEFAULT_DISCLAIMER,
    )


def build_out_of_scope_response(
    request: ChatRequest,
    intent: IntentResult,
) -> ChatResponse:
    """
    Kullanıcı proje kapsamı dışında bir şey sorarsa kullanılır.
    """

    return ChatResponse(
        success=True,
        message="Out of scope message handled successfully.",
        error=None,
        answer=OUT_OF_SCOPE_MESSAGE,
        intent=intent,
        user_profile=request.user_profile,
        matches=request.current_matches,
        recommendations=request.current_recommendations,
        sources=[],
        conversation_id=request.conversation_id,
        disclaimer=DEFAULT_DISCLAIMER,
    )


def build_unknown_intent_response(
    request: ChatRequest,
    intent: IntentResult,
) -> ChatResponse:
    """
    Intent Manager mesajın niyetinden emin olamazsa kullanılır.
    Kullanıcıya netleştirici soru sorulur.
    """

    return ChatResponse(
        success=True,
        message="Unknown intent handled successfully.",
        error=None,
        answer=UNKNOWN_INTENT_MESSAGE,
        intent=intent,
        user_profile=request.user_profile,
        matches=request.current_matches,
        recommendations=request.current_recommendations,
        sources=[],
        conversation_id=request.conversation_id,
        disclaimer=DEFAULT_DISCLAIMER,
    )


def build_missing_profile_response(
    request: ChatRequest,
    intent: IntentResult,
) -> ChatResponse:
    """
    Matching yapılması gerekiyor ama profil bilgileri eksikse kullanılır.

    Örneğin kullanıcı:
    'Bana uygun destekleri bul'

    ama user_profile yoksa sistem matching çalıştıramaz.
    """

    missing_fields_text = ", ".join(intent.missing_fields) if intent.missing_fields else "şirket bilgileri"

    answer = (
        "Size uygun teşvikleri bulabilmem için bazı bilgilere ihtiyacım var. "
        f"Eksik görünen alanlar: {missing_fields_text}. "
        "Lütfen sektör, çalışan sayısı, yıllık ciro ve ihtiyaç alanınızı paylaşın."
    )

    return ChatResponse(
        success=True,
        message="Missing profile information.",
        error=None,
        answer=answer,
        intent=intent,
        user_profile=request.user_profile,
        matches=request.current_matches,
        recommendations=request.current_recommendations,
        sources=[],
        conversation_id=request.conversation_id,
        disclaimer=DEFAULT_DISCLAIMER,
    )


def build_rag_answer_response(
    request: ChatRequest,
    intent: IntentResult,
    rag_response: RAGResponse,
) -> ChatResponse:
    """
    Chat mesajı RAG sorusuysa kullanılır.

    Örnek:
    'KOSGEB Ar-Ge desteği için hangi belgeler gerekiyor?'
    """

    answer = rag_response.answer or NO_RAG_CONTEXT_MESSAGE

    return ChatResponse(
        success=True,
        message="RAG answer generated successfully.",
        error=None,
        answer=answer,
        intent=intent,
        user_profile=request.user_profile,
        matches=request.current_matches,
        recommendations=rag_response.recommendations,
        sources=rag_response.sources,
        conversation_id=request.conversation_id,
        disclaimer=DEFAULT_DISCLAIMER,
    )


def build_chat_recommendation_response(
    request: ChatRequest,
    intent: IntentResult,
    matches: list[MatchResult],
    rag_response: RAGResponse | None = None,
) -> ChatResponse:
    """
    Chat içinden teşvik önerisi istendiğinde kullanılır.

    Akış:
    Chat message
    -> Intent: INCENTIVE_RECOMMENDATION
    -> Matching service
    -> RAG generate
    -> ChatResponse
    """

    if not matches:
        return ChatResponse(
            success=True,
            message="No matching program found.",
            error=None,
            answer=NO_MATCH_MESSAGE,
            intent=intent,
            user_profile=request.user_profile,
            matches=[],
            recommendations=[],
            sources=[],
            conversation_id=request.conversation_id,
            disclaimer=DEFAULT_DISCLAIMER,
        )

    recommendations = rag_response.recommendations if rag_response else []
    sources = rag_response.sources if rag_response else []
    answer = (
        rag_response.answer
        if rag_response and rag_response.answer
        else "Verdiğiniz bilgilere göre size uygun olabilecek destekleri listeledim."
    )

    return ChatResponse(
        success=True,
        message="Chat recommendation generated successfully.",
        error=None,
        answer=answer,
        intent=intent,
        user_profile=request.user_profile,
        matches=matches,
        recommendations=recommendations,
        sources=sources,
        conversation_id=request.conversation_id,
        disclaimer=DEFAULT_DISCLAIMER,
    )


def build_profile_update_response(
    request: ChatRequest,
    intent: IntentResult,
    updated_profile: UserProfile | None = None,
    matches: list[MatchResult] | None = None,
    rag_response: RAGResponse | None = None,
) -> ChatResponse:
    """
    Kullanıcı chat içinde profil bilgisini güncellediğinde kullanılır.

    İlk MVP'de profile extraction tam yapılmadıysa updated_profile None kalabilir.
    İleride mesajdan sektör, çalışan sayısı, şehir gibi alanlar çıkarılıp
    updated_profile olarak döndürülebilir.
    """

    final_profile = updated_profile or request.user_profile
    final_matches = matches or request.current_matches

    recommendations = (
        rag_response.recommendations
        if rag_response
        else request.current_recommendations
    )

    sources = rag_response.sources if rag_response else []

    answer = (
        rag_response.answer
        if rag_response and rag_response.answer
        else "Profil bilginizi aldım. Güncel bilgilerle destek önerilerini tekrar değerlendirebilirim."
    )

    return ChatResponse(
        success=True,
        message="Profile update handled successfully.",
        error=None,
        answer=answer,
        intent=intent,
        user_profile=final_profile,
        matches=final_matches,
        recommendations=recommendations,
        sources=sources,
        conversation_id=request.conversation_id,
        disclaimer=DEFAULT_DISCLAIMER,
    )


def build_eligibility_response(
    request: ChatRequest,
    intent: IntentResult,
    rag_response: RAGResponse,
    matches: list[MatchResult] | None = None,
) -> ChatResponse:
    """
    Kullanıcı uygunluk sorusu sorduğunda kullanılır.

    Örnek:
    'Bu desteğe uygun muyum?'
    '12 çalışanlı yazılım şirketi bu desteğe başvurabilir mi?'
    """

    answer = (
        rag_response.answer
        if rag_response and rag_response.answer
        else (
            "Verdiğiniz bilgilere göre uygunluk değerlendirmesi yapılabilir; "
            "ancak nihai karar resmi başvuru şartlarına ve kurum değerlendirmesine bağlıdır."
        )
    )

    return ChatResponse(
        success=True,
        message="Eligibility question handled successfully.",
        error=None,
        answer=answer,
        intent=intent,
        user_profile=request.user_profile,
        matches=matches or request.current_matches,
        recommendations=rag_response.recommendations,
        sources=rag_response.sources,
        conversation_id=request.conversation_id,
        disclaimer=DEFAULT_DISCLAIMER,
    )


def build_fallback_response(
    request: ChatRequest,
    intent: IntentResult | None = None,
) -> ChatResponse:
    """
    Beklenmeyen ama hata olmayan durumlarda güvenli cevap döner.
    """

    return ChatResponse(
        success=True,
        message="Fallback response returned.",
        error=None,
        answer=(
            "İsteğinizi tam olarak anlayamadım. İşletmenize uygun destekleri bulmamı mı "
            "istiyorsunuz, yoksa belirli bir destek hakkında bilgi mi almak istiyorsunuz?"
        ),
        intent=intent,
        user_profile=request.user_profile,
        matches=request.current_matches,
        recommendations=request.current_recommendations,
        sources=[],
        conversation_id=request.conversation_id,
        disclaimer=DEFAULT_DISCLAIMER,
    )