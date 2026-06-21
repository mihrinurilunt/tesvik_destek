"""
TÜBİTAK scraper
Index : https://tubitak.gov.tr/tr/destekler   (tüm program linkleri tek sayfada)
Detail: https://tubitak.gov.tr/tr/destekler/{kategori}/{alt}/{program-slug}

Page structure (Drupal 10):
  - Main content: div.paragraph--type--duz-metin .field--name-field-icerik
    - Sections separated by <strong> tags inside <p> elements
  - File sections: div.paragraph--type--dosya-listesi-media
    - Section name: .field--name-field-baslik
    - Files: a[href]
"""

from bs4 import BeautifulSoup
from utils.http import get
from utils.models import make_record, make_section

BASE = "https://tubitak.gov.tr"
INDEX = f"{BASE}/tr/destekler"

# URL segments that indicate a program detail page (not a category listing)
_PROGRAM_PREFIXES = [
    "/tr/destekler/",
    "/tr/burslar/",
]


def get_program_urls(session) -> list[str]:
    r = get(session, INDEX)
    soup = BeautifulSoup(r.text, "html.parser")

    urls = set()
    for a in soup.select("a[href]"):
        href = a["href"].strip()

        # Normalise relative → absolute
        if href.startswith("/"):
            href = BASE + href

        if not href.startswith(BASE):
            continue

        path = href.replace(BASE, "")

        # Must be under /tr/destekler/ or /tr/burslar/
        if not any(path.startswith(p) for p in _PROGRAM_PREFIXES):
            continue

        # Must have at least 4 path segments:
        # /tr / destekler / kategori / program-slug
        segments = [s for s in path.split("/") if s]
        if len(segments) < 4:
            continue

        urls.add(href)

    return sorted(urls)


def _parse_text_sections(soup) -> list[dict]:
    """
    Parse the main duz-metin block.
    TÜBİTAK puts all content in one block, using <strong> tags as headers:
      <p><strong>Amaç</strong></p>
      <p>Bu programın amacı...</p>
    """
    sections = []
    block = soup.select_one(
        "div.paragraph--type--duz-metin .field--name-field-icerik"
    )
    if not block:
        return sections

    current_title = "Genel"
    current_lines = []

    for p in block.find_all("p"):
        strong = p.find("strong")
        if strong and strong.get_text(strip=True):
            # Save previous section
            if current_lines:
                sections.append(
                    make_section(current_title, " ".join(current_lines).strip())
                )
            current_title = strong.get_text(strip=True).rstrip(":")
            # Text on the same line after the <strong>
            rest = p.get_text(" ", strip=True)
            # Remove the header text itself
            rest = rest.replace(strong.get_text(strip=True), "").strip().lstrip(":")
            current_lines = [rest] if rest else []
        else:
            text = p.get_text(" ", strip=True)
            if text:
                current_lines.append(text)

    # Last section
    if current_lines:
        sections.append(
            make_section(current_title, " ".join(current_lines).strip())
        )

    return sections


def _parse_file_sections(soup) -> list[dict]:
    """
    Parse dosya-listesi blocks (Esaslar, Kılavuzlar, Formlar, etc.)
    Each block becomes its own section with links.
    """
    sections = []
    for block in soup.select("div.paragraph--type--dosya-listesi-media"):
        baslik_el = block.select_one(".field--name-field-baslik")
        title = baslik_el.get_text(strip=True) if baslik_el else "Dosyalar"

        links = []
        for a in block.select("a[href]"):
            href = a["href"].strip()
            if href.startswith("/"):
                href = BASE + href
            text = a.get_text(" ", strip=True)
            if text and href:
                links.append({"text": text, "href": href})

        if links:
            sections.append(make_section(title, "", links))

    return sections


def parse_program(session, url: str) -> dict:
    r = get(session, url)
    soup = BeautifulSoup(r.text, "html.parser")

    # Program name
    h1 = soup.select_one("h1 span")
    program_name = h1.get_text(strip=True) if h1 else ""

    sections = _parse_text_sections(soup) + _parse_file_sections(soup)

    return make_record(url, "tubitak", program_name, sections)
