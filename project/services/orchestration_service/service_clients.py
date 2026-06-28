from __future__ import annotations

import httpx
from pydantic import ValidationError

from shared.config import settings
from shared.constants import MATCH_PATH, RAG_ANSWER_PATH, RAG_GENERATE_PATH
from shared.exceptions import MatchingException, RAGException
from shared.logger import get_logger
from shared.schemas import (
    MatchRequest,
    MatchResponse,
    RAGAnswerRequest,
    RAGGenerateRequest,
    RAGResponse,
)

logger = get_logger(__name__)


async def call_matching_service(request: MatchRequest) -> MatchResponse:
    """
    matching_service /match endpointini çağırır.

    Orchestration service şunu gönderir:
        MatchRequest(user_profile=..., top_k=...)

    Matching service şunu döner:
        MatchResponse(success=True, matches=[...])
    """

    url = f"{settings.MATCHING_SERVICE_URL}{MATCH_PATH}"

    logger.info(f"Calling matching service: {url}")

    try:
        async with httpx.AsyncClient(timeout=settings.SERVICE_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                json=request.model_dump(mode="json"),
            )

        response.raise_for_status()
        data = response.json()

        match_response = MatchResponse.model_validate(data)

        if not match_response.success:
            raise MatchingException(
                message=match_response.message or "Matching service başarısız response döndü.",
                details={
                    "service": "matching_service",
                    "error": match_response.error.model_dump() if match_response.error else None,
                },
            )

        return match_response

    except httpx.TimeoutException as exc:
        logger.error("Matching service timeout")
        raise MatchingException(
            message="Matching service zaman aşımına uğradı.",
            details={"url": url},
        ) from exc

    except httpx.HTTPStatusError as exc:
        logger.error(f"Matching service HTTP error: {exc.response.status_code}")
        raise MatchingException(
            message="Matching service HTTP hatası döndürdü.",
            details={
                "url": url,
                "status_code": exc.response.status_code,
                "response": exc.response.text,
            },
        ) from exc

    except httpx.RequestError as exc:
        logger.error(f"Matching service request error: {str(exc)}")
        raise MatchingException(
            message="Matching service bağlantısı kurulamadı.",
            details={"url": url, "error": str(exc)},
        ) from exc

    except ValidationError as exc:
        logger.error("Matching service response validation error")
        raise MatchingException(
            message="Matching service beklenen response formatında veri döndürmedi.",
            details={"validation_error": str(exc)},
        ) from exc


async def call_rag_generate(request: RAGGenerateRequest) -> RAGResponse:
    """
    rag_service /rag/generate endpointini çağırır.

    Kullanım yeri:
        - /recommend akışı
        - Chat içinde incentive_recommendation intent'i
        - Matching sonucu açıklamalı öneriye çevrilecekse

    Orchestration service şunu gönderir:
        RAGGenerateRequest(user_profile=..., matches=[...])

    RAG service şunu döner:
        RAGResponse(answer=..., recommendations=[...], sources=[...])
    """

    url = f"{settings.RAG_SERVICE_URL}{RAG_GENERATE_PATH}"

    logger.info(f"Calling RAG generate service: {url}")

    try:
        async with httpx.AsyncClient(timeout=settings.SERVICE_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                json=request.model_dump(mode="json"),
            )

        response.raise_for_status()
        data = response.json()

        rag_response = RAGResponse.model_validate(data)

        if not rag_response.success:
            raise RAGException(
                message=rag_response.message or "RAG generate service başarısız response döndü.",
                details={
                    "service": "rag_service",
                    "endpoint": RAG_GENERATE_PATH,
                    "error": rag_response.error.model_dump() if rag_response.error else None,
                },
            )

        return rag_response

    except httpx.TimeoutException as exc:
        logger.error("RAG generate service timeout")
        raise RAGException(
            message="RAG generate service zaman aşımına uğradı.",
            details={"url": url},
        ) from exc

    except httpx.HTTPStatusError as exc:
        logger.error(f"RAG generate HTTP error: {exc.response.status_code}")
        raise RAGException(
            message="RAG generate service HTTP hatası döndürdü.",
            details={
                "url": url,
                "status_code": exc.response.status_code,
                "response": exc.response.text,
            },
        ) from exc

    except httpx.RequestError as exc:
        logger.error(f"RAG generate request error: {str(exc)}")
        raise RAGException(
            message="RAG generate service bağlantısı kurulamadı.",
            details={"url": url, "error": str(exc)},
        ) from exc

    except ValidationError as exc:
        logger.error("RAG generate response validation error")
        raise RAGException(
            message="RAG generate service beklenen response formatında veri döndürmedi.",
            details={"validation_error": str(exc)},
        ) from exc


async def call_rag_answer(request: RAGAnswerRequest) -> RAGResponse:
    """
    rag_service /rag/answer endpointini çağırır.

    Kullanım yeri:
        - Chat içinde rag_question intent'i
        - Kullanıcı belirli destek, belge, şart veya başvuru süreci sorarsa

    Orchestration service şunu gönderir:
        RAGAnswerRequest(user_message=..., user_profile=..., current_matches=[...])

    RAG service şunu döner:
        RAGResponse(answer=..., sources=[...])
    """

    url = f"{settings.RAG_SERVICE_URL}{RAG_ANSWER_PATH}"

    logger.info(f"Calling RAG answer service: {url}")

    try:
        async with httpx.AsyncClient(timeout=settings.SERVICE_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                json=request.model_dump(mode="json"),
            )

        response.raise_for_status()
        data = response.json()

        rag_response = RAGResponse.model_validate(data)

        if not rag_response.success:
            raise RAGException(
                message=rag_response.message or "RAG answer service başarısız response döndü.",
                details={
                    "service": "rag_service",
                    "endpoint": RAG_ANSWER_PATH,
                    "error": rag_response.error.model_dump() if rag_response.error else None,
                },
            )

        return rag_response

    except httpx.TimeoutException as exc:
        logger.error("RAG answer service timeout")
        raise RAGException(
            message="RAG answer service zaman aşımına uğradı.",
            details={"url": url},
        ) from exc

    except httpx.HTTPStatusError as exc:
        logger.error(f"RAG answer HTTP error: {exc.response.status_code}")
        raise RAGException(
            message="RAG answer service HTTP hatası döndürdü.",
            details={
                "url": url,
                "status_code": exc.response.status_code,
                "response": exc.response.text,
            },
        ) from exc

    except httpx.RequestError as exc:
        logger.error(f"RAG answer request error: {str(exc)}")
        raise RAGException(
            message="RAG answer service bağlantısı kurulamadı.",
            details={"url": url, "error": str(exc)},
        ) from exc

    except ValidationError as exc:
        logger.error("RAG answer response validation error")
        raise RAGException(
            message="RAG answer service beklenen response formatında veri döndürmedi.",
            details={"validation_error": str(exc)},
        ) from exc