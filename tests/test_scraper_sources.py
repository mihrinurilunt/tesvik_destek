from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from scrapers import tkdk, tubitak
from utils import http


def test_tubitak_excludes_category_pages(monkeypatch):
    monkeypatch.setattr(tubitak, 'get', lambda *args: SimpleNamespace(text='''
    <a href="/tr/destekler/sanayi">Kategori</a>
    <a href="/tr/destekler/sanayi/ulusal-destek-programlari">Kategori</a>
    <a href="/tr/destekler/sanayi/ulusal-destek-programlari/1501-program">Program</a>'''))
    assert tubitak.get_program_urls(None) == ['https://tubitak.gov.tr/tr/destekler/sanayi/ulusal-destek-programlari/1501-program']


def test_tkdk_excludes_error_language_and_external_links(monkeypatch):
    monkeypatch.setattr(tkdk, 'get', lambda *args: SimpleNamespace(text='''
    <a href="/Home/Dil?ReturnUrl=/ipard/program">Dil</a>
    <a href="https://elsewhere.example/Tedbir/program">Harici</a>
    <a href="/Tedbir/destek-1">Program</a>'''))
    assert tkdk.get_program_urls(None) == ['https://www.tkdk.gov.tr/Tedbir/destek-1']


@pytest.mark.parametrize('url,html', [
    ('https://www.tkdk.gov.tr/Home/Http404', '<p>Error</p>'),
    ('https://www.tkdk.gov.tr/old', '<h1>Page Not Found</h1>'),
])
def test_http_rejects_soft_404(monkeypatch,url,html):
    monkeypatch.setattr(http.time, 'sleep', lambda _: None)
    response=Mock(url=url,text=html)
    session=Mock(); session.get.return_value=response
    with pytest.raises(ValueError):
        http.get(session,url)


def test_tubitak_rejects_empty_program(monkeypatch):
    monkeypatch.setattr(tubitak, 'get', lambda *args: SimpleNamespace(text='<h1>Category</h1>'))
    with pytest.raises(ValueError):
        tubitak.parse_program(None,'https://tubitak.gov.tr/tr/destekler/sanayi')


def test_tkdk_generic_heading_uses_program_label(monkeypatch):
    url='https://www.tkdk.gov.tr/Tedbir/ciftlik-faaliyetleri-4'
    monkeypatch.setattr(tkdk, 'get', lambda *args: SimpleNamespace(text='<main><h1>Sektörler</h1><a href="/Tedbir/ciftlik-faaliyetleri-4">Çiftlik Faaliyetleri</a><p>Destek koşulları.</p></main>'))
    assert tkdk.parse_program(None,url)['program_name'] == 'Çiftlik Faaliyetleri'
