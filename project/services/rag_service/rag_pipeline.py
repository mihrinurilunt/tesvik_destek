from shared.models import Recommendation
from shared.schemas import RAGAnswerRequest, RAGGenerateRequest, RAGResponse

from services.rag_service.llm_client import generate_llm_answer
from services.rag_service.prompt_builder import build_answer_prompt, build_generate_prompt
from services.rag_service.retrieval import retrieve_chunks, retrieve_chunks_for_matches


async def generate_recommendations(request: RAGGenerateRequest) -> RAGResponse:
    chunks = await retrieve_chunks_for_matches(
        matches=request.matches,
        user_message=request.user_message,
        top_k=request.top_k_chunks,
    )

    prompt = build_generate_prompt(
        user_profile=request.user_profile,
        matches=request.matches,
        chunks=chunks,
    )

    answer = await generate_llm_answer(prompt)

    recommendations: list[Recommendation] = []

    for match in request.matches:
        related_sources = [
            chunk for chunk in chunks if chunk.program_id == match.program_id
        ]

        recommendations.append(
            Recommendation(
                program_id=match.program_id,
                program_name=match.program_name,
                institution=match.institution,
                score=match.score,
                summary=f"{match.program_name} için belgeye dayalı açıklama oluşturuldu.",
                why_matched=match.match_reasons,
                eligibility_notes=match.missing_criteria,
                application_steps=[],
                required_documents=[],
                application_url=match.application_url,
                sources=related_sources,
            )
        )

    return RAGResponse(
        success=True,
        message="RAG önerileri üretildi.",
        error=None,
        answer=answer,
        recommendations=recommendations,
        sources=chunks,
    )


async def answer_question(request: RAGAnswerRequest) -> RAGResponse:
    program_ids = [match.program_id for match in request.current_matches]

    chunks = await retrieve_chunks(
        query=request.user_message,
        top_k=request.top_k_chunks,
        program_ids=program_ids or None,
    )

    prompt = build_answer_prompt(
        user_message=request.user_message,
        user_profile=request.user_profile,
        chunks=chunks,
    )

    answer = await generate_llm_answer(prompt)

    return RAGResponse(
        success=True,
        message="RAG cevabı üretildi.",
        error=None,
        answer=answer,
        recommendations=[],
        sources=chunks,
    )