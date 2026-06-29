import os
import json
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from openai import AsyncOpenAI
from pydantic import HttpUrl

from shared.config import settings
from shared.models import SourceChunk
from shared.logger import get_logger

logger = get_logger(__name__)

QDRANT_URL = getattr(settings, "QDRANT_URL", os.environ.get("QDRANT_URL", "http://qdrant:6333"))
OPENAI_API_KEY = getattr(settings, "OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))

qdrant_client = QdrantClient(url=QDRANT_URL)
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def get_embedding(text: str) -> List[float]:
    """
    Ingestion katmanı ile aynı embedding modelini ('text-embedding-3-small') kullanarak 
    sorgu metnini vektöre dönüştürür.
    """
    try:
        response = await openai_client.embeddings.create(
            input=[text],
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding üretimi başarısız oldu: {e}")
        raise e


async def retrieve_chunks(
    query_text: str,
    top_k: int = 5,
    program_id: Optional[str] = None
) -> List[SourceChunk]:
    """
    Qdrant veritabanında benzerlik araması gerçekleştirir. 
    Gerektiğinde program_id parametresi ile sadece ilgili teşvik dökümanı filtrelenebilir.
    """
    try:
        vector = await get_embedding(query_text)
        
        qdrant_filter = None
        if program_id:
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="program_id",
                        match=MatchValue(value=program_id)
                    )
                ]
            )
            
        search_results = qdrant_client.search(
            collection_name="tesvikler_v2",
            query_vector=vector,
            limit=top_k,
            query_filter=qdrant_filter
        )
        
        sources = []
        for hit in search_results:
            payload = hit.payload or {}
            
            # LlamaIndex'in döküman saklama biçimlerine (text veya _node_content) göre içerik ayıklanır
            raw_text = payload.get("text")
            if not raw_text and "_node_content" in payload:
                try:
                    node_data = json.loads(payload["_node_content"])
                    raw_text = node_data.get("text", "")
                except Exception:
                    raw_text = payload["_node_content"]
                    
            if not raw_text:
                raw_text = ""

            # URL verilerinin validasyonu
            validated_app_url = None
            app_url = payload.get("application_url")
            if app_url:
                try:
                    validated_app_url = HttpUrl(app_url)
                except Exception:
                    pass

            validated_source_url = None
            source_url = payload.get("source_url")
            if source_url:
                try:
                    validated_source_url = HttpUrl(source_url)
                except Exception:
                    pass
            
            sources.append(
                SourceChunk(
                    chunk_id=str(hit.id),
                    program_id=payload.get("program_id"),
                    program_name=payload.get("program_name"),
                    text=raw_text,
                    score=hit.score,
                    source_file=payload.get("source_file"),
                    source_url=validated_source_url,
                    metadata=payload
                )
            )
        return sources
    except Exception as e:
        logger.error(f"Qdrant arama operasyonu sırasında hata: {e}")
        return []