"""
UTILS - HTTP.PY
"""
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def make_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9",
    })
    return session


def get(session, url, delay=1.5):
    """Rate-limited GET. Returns response with UTF-8 encoding forced."""
    time.sleep(delay)
    r = session.get(url, timeout=20)
    r.encoding = "utf-8"
    r.raise_for_status()
    return r
