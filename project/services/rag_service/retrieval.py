from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny

from shared.models import MatchResult, SourceChunk
from services.rag_service.llm_client import create_embedding

QDRANT_URL = "http://qdrant:6333"
COLLECTION_NAME = "tesvikler_v2"

client = QdrantClient(url=QDRANT_URL)


def build_program_filter(program_ids: Optional[list[str]] = None) -> Optional[Filter]:
    if not program_ids:
        return None

    return Filter(
        must=[
            FieldCondition(
                key="program_id",
                match=MatchAny(any=program_ids),
            )
        ]
    )


async def retrieve_chunks(
    query: str,
    top_k: int = 5,
    program_ids: Optional[list[str]] = None,
) -> list[SourceChunk]:
    query_vector = await create_embedding(query)

    query_result = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
        query_filter=build_program_filter(program_ids),
        with_payload=True,
    )

    results = query_result.points

    chunks: list[SourceChunk] = []

    for item in results:
        payload = item.payload or {}

        text = (
            payload.get("text")
            or payload.get("content")
            or payload.get("chunk_text")
            or payload.get("page_content")
            or ""
        )

        if not text:
            continue

        chunks.append(
            SourceChunk(
                chunk_id=str(payload.get("chunk_id", item.id)),
                program_id=payload.get("program_id"),
                program_name=payload.get("program_name"),
                text=text,
                score=item.score,
                source_file=payload.get("source_file"),
                source_url=payload.get("source_url"),
                metadata=payload.get("metadata", {}),
            )
        )

    return chunks


async def retrieve_chunks_for_matches(
    matches: list[MatchResult],
    user_message: str | None,
    top_k: int,
) -> list[SourceChunk]:
    program_ids = [match.program_id for match in matches]

    query_parts: list[str] = []

    if user_message:
        query_parts.append(user_message)

    for match in matches:
        query_parts.append(match.program_name)
        query_parts.extend(match.match_reasons)

    query = " ".join(query_parts)

    return await retrieve_chunks(
        query=query,
        top_k=top_k,
        program_ids=program_ids,
    )