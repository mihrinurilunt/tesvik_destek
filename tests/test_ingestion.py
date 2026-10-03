"""Real local Qdrant + LlamaIndex, with deterministic free embeddings."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from llama_index.core import Document, Settings
from llama_index.core.embeddings import MockEmbedding
from qdrant_client import QdrantClient, models
from services.ingestion_service import main as ingestion
from services.rag_service import retrieval

@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(Settings, 'embed_model', MockEmbedding(embed_dim=3))
    client = QdrantClient(':memory:')
    yield client
    client.close()


def document(name='Eski program'):
    return Document(text=f'{name}: teknoloji yatırımı desteği. Başvuru şartları resmi sitededir.', metadata={
        'program_id': 'test_1', 'program_name': name, 'institution': 'KOSGEB',
        'source_url': 'https://example.org/program', 'sectors': ['Teknoloji'], 'needs': ['Yatırım'],
    })


def test_publish_retrieve_and_replace_without_deleting_old_data(db, monkeypatch):
    old = ingestion.publish_documents(db, [document()], 'tesvikler_v2')
    monkeypatch.setattr(retrieval, 'qdrant_client', SimpleNamespace(query_points=AsyncMock(side_effect=db.query_points)))
    monkeypatch.setattr(retrieval, 'get_embedding', AsyncMock(return_value=[0.5]*3))
    chunks = asyncio.run(retrieval.retrieve_chunks('yatırım', program_id='test_1'))
    assert len(chunks) == 1
    assert 'Eski program' in chunks[0].text
    new = ingestion.publish_documents(db, [document('Yeni program')], 'tesvikler_v2')
    chunks = asyncio.run(retrieval.retrieve_chunks('yatırım', program_id='test_1'))
    assert 'Yeni program' in chunks[0].text
    assert db.collection_exists(old) and db.collection_exists(new)
    assert db.count('tesvikler_v2').count == 1


def test_failed_build_keeps_published_data(db, monkeypatch):
    old = ingestion.publish_documents(db, [document()], 'tesvikler_v2')
    def fail(*args, **kwargs):
        raise RuntimeError('embedding outage')
    monkeypatch.setattr(ingestion, 'VectorStoreIndex', fail)
    with pytest.raises(RuntimeError):
        ingestion.publish_documents(db, [document('Yeni')], 'tesvikler_v2')
    assert db.get_aliases().aliases[0].collection_name == old
    assert db.count('tesvikler_v2').count == 1


def test_existing_physical_collection_is_preserved(db):
    db.create_collection('tesvikler_v2', vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE))
    with pytest.raises(ValueError, match='fiziksel'):
        ingestion.publish_documents(db, [document()], 'tesvikler_v2')
    assert db.collection_exists('tesvikler_v2')


def test_empty_build_cannot_replace_existing_data(db):
    old = ingestion.publish_documents(db, [document()], 'tesvikler_v2')
    with pytest.raises(ValueError, match='Boş'):
        ingestion.publish_documents(db, [], 'tesvikler_v2')
    assert db.get_aliases().aliases[0].collection_name == old


def test_recommendation_flow_through_service_http_contracts(db, monkeypatch):
    import httpx
    from fastapi.testclient import TestClient
    from services.matching_service import main as matching
    from services.rag_service import main as rag, llm_client
    from services.orchestration_service import main as orchestration, service_clients
    from shared.config import settings

    ingestion.publish_documents(db, [document()], 'tesvikler_v2')
    monkeypatch.setattr(matching.matcher, '_qdrant', SimpleNamespace(scroll=AsyncMock(side_effect=db.scroll)))
    monkeypatch.setattr(retrieval, 'qdrant_client', SimpleNamespace(query_points=AsyncMock(side_effect=db.query_points)))
    monkeypatch.setattr(retrieval, 'get_embedding', AsyncMock(return_value=[0.5]*3))
    def completion(content):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    monkeypatch.setattr(llm_client.openai_client.chat.completions, 'create', AsyncMock(side_effect=[
        completion('{"summary":"Kaynaklara dayalı test önerisi."}'),
        completion('Test şirketi için destek analizi tamamlandı.'),
    ]))
    real_client = httpx.AsyncClient
    def local_client(**kwargs):
        return real_client(**kwargs, mounts={
            settings.MATCHING_SERVICE_URL: httpx.ASGITransport(app=matching.app),
            settings.RAG_SERVICE_URL: httpx.ASGITransport(app=rag.app),
        })
    monkeypatch.setattr(service_clients.httpx, 'AsyncClient', local_client)
    response = TestClient(orchestration.app).post('/recommend', json={'user_profile': {
        'sector': 'Teknoloji', 'employee_count': 5, 'annual_revenue': 100000, 'needs': ['Yatırım'],
    }})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['success'] is True
    assert len(result['matches']) == len(result['recommendations']) == 1
    assert result['sources'][0]['source_url'] == 'https://example.org/program'
    assert result['recommendations'][0]['summary'] == 'Kaynaklara dayalı test önerisi.'


def test_long_scraped_metadata_does_not_exceed_chunk_budget(db, monkeypatch, tmp_path):
    import json
    record = {'program_id':'long_1','program_name':'Uzun Destek','institution':'KOSGEB',
              'url':'https://example.org/program','sections':[{'title':'Başvuru Şartları','content':'Resmi başvuru koşulu. '*1500}]}
    path=tmp_path/'input.json'; path.write_text(json.dumps([record]))
    monkeypatch.setattr(ingestion, 'JSON_PATH', str(path))
    monkeypatch.setattr(ingestion, 'OpenAIEmbedding', lambda **kwargs: MockEmbedding(embed_dim=3))
    monkeypatch.setattr(ingestion.qdrant_client, 'QdrantClient', lambda **kwargs: db)
    monkeypatch.setattr(db, 'close', lambda: None)
    ingestion.run_ingestion()
    points, _ = db.scroll('tesvikler_v2', limit=1)
    assert points[0].payload['conditions']
    assert db.count('tesvikler_v2').count > 1
