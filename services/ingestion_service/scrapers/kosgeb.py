"""
KOSGEB scraper
Index : https://www.kosgeb.gov.tr/site/tr/genel/destekler/3/destekler
Detail: https://www.kosgeb.gov.tr/site/tr/genel/destekdetay/{id}/{slug}

Page structure:
  - Program sections are accordion items: div.accordion-item
  - Section title: h4.accordion-toggle
  - Section body: section.accordion-inner
  - File links: a[href] inside section body
"""

from bs4 import BeautifulSoup
from utils.http import get
from utils.models import make_record, make_section

BASE = "https://www.kosgeb.gov.tr"
INDEX = f"{BASE}/site/tr/genel/destekler/3/destekler"


def get_program_urls(session) -> list[str]:
    r = get(session, INDEX)
    soup = BeautifulSoup(r.text, "html.parser")

    urls = set()

    # Navbar links (ana programlar)
    for a in soup.select("a[href*='destekdetay']"):
        href = a["href"]
        if href.startswith("/"):
            href = BASE + href
        urls.add(href)

    # "Diğer Destekler" section in main content
    for a in soup.select("div.content a[href*='destekdetay']"):
        href = a["href"]
        if href.startswith("/"):
            href = BASE + href
        urls.add(href)

    return sorted(urls)


def _extract_links(element) -> list[dict]:
    links = []
    for a in element.select("a[href]"):
        href = a["href"].strip()
        text = a.get_text(" ", strip=True)
        if text and href:
            links.append({"text": text, "href": href})
    return links


def parse_program(session, url: str) -> dict:
    r = get(session, url)
    soup = BeautifulSoup(r.text, "html.parser")

    # Program name
    h3 = soup.select_one("div.heading h3")
    program_name = h3.get_text(strip=True) if h3 else ""

    sections = []
    for item in soup.select("div.accordion-item"):
        title_el = item.select_one("h4.accordion-toggle")
        body_el = item.select_one("section.accordion-inner")

        if not title_el or not body_el:
            continue

        title = title_el.get_text(strip=True)
        content = body_el.get_text(" ", strip=True)
        links = _extract_links(body_el)

        sections.append(make_section(title, content, links or None))

    return make_record(url, "kosgeb", program_name, sections)
