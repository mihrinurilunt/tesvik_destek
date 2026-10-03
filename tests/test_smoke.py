"""Offline baseline: real API schemas and local Qdrant; no paid API calls."""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from qdrant_client import QdrantClient, AsyncQdrantClient, models

from shared.models import UserProfile
from services.orchestration_service.main import app as orchestration_app
from services.matching_service.main import app as matching_app
from services.rag_service.main import app as rag_app
from services.rag_service import retrieval, llm_client
from services.matching_service.matcher import Matcher
from shared.schemas import RAGGenerateRequest

PROFILE = dict(sector='Teknoloji', employee_count=5, annual_revenue=100000, needs=['Ar-Ge'])
PAYLOAD = dict(program_id='test_1', program_name='Test Destek', institution='KOSGEB',
               description='Teknoloji Ar-Ge destek programı.', sectors=['Teknoloji'], needs=['Ar-Ge'],
               application_url='https://example.org/program', text='Başvuru için resmi koşullar incelenmelidir.')

@pytest.mark.parametrize('app', [orchestration_app, matching_app, rag_app])
def test_health(app):
    assert TestClient(app).get('/health').status_code == 200

@pytest.mark.parametrize('changes', [dict(employee_count=-1), dict(annual_revenue=-1), dict(needs=[])])
def test_invalid_profile(changes):
    with pytest.raises(ValidationError):
        UserProfile(**(PROFILE | changes))

@pytest.mark.parametrize('message', ['merhaba', 'sen kimsin'])
def test_chat_without_external_services(message):
    response = TestClient(orchestration_app).post('/chat', json={'message': message})
    assert response.status_code == 200
    assert response.json()['success'] is True
    assert response.json()['answer']

def test_invalid_recommendation_request():
    assert TestClient(orchestration_app).post('/recommend', json={'user_profile': {}}).status_code == 422

def test_scraper_table_preserves_content():
    from bs4 import BeautifulSoup
    from scrapers.tkdk import _heading_sections
    sections = _heading_sections(BeautifulSoup('<main><h2>Destek</h2><table><tr><td>Oran</td><td>%50</td></tr></table></main>', 'html.parser'))
    assert '%50' in sections[0]['content']

def test_scraper_output_is_ingestion_input():
    import runner
    from services.ingestion_service import main
    assert runner.OUTPUT_FILE.resolve() == Path(main.JSON_PATH).resolve()

def test_named_vector_retrieval(monkeypatch):
    async def check():
        client = AsyncQdrantClient(':memory:')
        await client.create_collection('tesvikler_v2', vectors_config={'text-dense': models.VectorParams(size=3, distance=models.Distance.COSINE)})
        await client.upsert('tesvikler_v2', points=[models.PointStruct(id=1, vector={'text-dense': [1., 0., 0.]}, payload=PAYLOAD)])
        monkeypatch.setattr(retrieval, 'qdrant_client', client)
        monkeypatch.setattr(retrieval, 'get_embedding', AsyncMock(return_value=[1., 0., 0.]))
        try:
            result = await retrieval.retrieve_chunks('Test Destek', program_id='test_1')
            assert len(result) == 1
            assert str(result[0].source_url) == PAYLOAD['application_url']
        finally:
            await client.close()
    asyncio.run(check())


def test_matching_deduplicates_programs():
    async def check():
        client = AsyncQdrantClient(':memory:')
        await client.create_collection('tesvikler_v2', vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE))
        await client.upsert('tesvikler_v2', points=[models.PointStruct(id=i, vector=[1., 0., 0.], payload=PAYLOAD) for i in [1, 2]])
        matcher = Matcher()
        matcher._qdrant = client
        try:
            results = await matcher.find_matches(UserProfile(**PROFILE), top_k=5)
            assert len({r.program_id for r in results}) == len(results)
        finally:
            await client.close()
    asyncio.run(check())

def test_llm_failure_is_not_success(monkeypatch):
    monkeypatch.setattr(llm_client, 'retrieve_chunks', AsyncMock(return_value=[]))
    monkeypatch.setattr(llm_client.openai_client.chat.completions, 'create', AsyncMock(side_effect=RuntimeError('simulated outage')))
    request = RAGGenerateRequest(user_profile=PROFILE, matches=[dict(program_id='test_1', program_name='Test Destek', institution='KOSGEB', score=70)])
    from shared.exceptions import LLMException
    with pytest.raises(LLMException):
        asyncio.run(llm_client.call_llm_generate(request))


def test_matching_reads_all_pages():
    async def check():
        client = AsyncQdrantClient(':memory:')
        await client.create_collection('tesvikler_v2', vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE))
        await client.upsert('tesvikler_v2', points=[models.PointStruct(id=i, vector=[1., 0., 0.], payload=PAYLOAD | {'program_id': f'test_{i}'}) for i in range(3)])
        matcher = Matcher()
        matcher._qdrant = client
        try:
            assert len(await matcher._fetch_candidate_programs(limit=1)) == 3
        finally:
            await client.close()
    asyncio.run(check())


def test_retrieval_outage_is_error(monkeypatch):
    from shared.exceptions import RetrievalException
    monkeypatch.setattr(retrieval, 'get_embedding', AsyncMock(side_effect=RuntimeError('offline')))
    with pytest.raises(RetrievalException):
        asyncio.run(retrieval.retrieve_chunks('test'))


def test_llm_failure_returns_http_error(monkeypatch):
    monkeypatch.setattr(llm_client, 'retrieve_chunks', AsyncMock(return_value=[]))
    monkeypatch.setattr(llm_client.openai_client.chat.completions, 'create', AsyncMock(side_effect=RuntimeError('offline')))
    response = TestClient(rag_app).post('/rag/generate', json={'user_profile': PROFILE, 'matches': [dict(program_id='test_1', program_name='Test Destek', institution='KOSGEB', score=70)]})
    assert response.status_code == 500
    assert response.json()['success'] is False
