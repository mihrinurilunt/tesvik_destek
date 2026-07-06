"""
TKDK Deep Scraper
"""

from bs4 import BeautifulSoup
from utils.http import get
from utils.models import make_record, make_section

BASE = "https://www.tkdk.gov.tr"

# Derin tarama için ana başlangıç sayfaları
SEED_PAGES = [
    f"{BASE}/ipard/ipardprogrami",
    f"{BASE}/ipard/ipard3-destekleme-tedbirleri",
    f"{BASE}/Hibe/Takvim",
    f"{BASE}/ipard/tedbirler"
]


def get_program_urls(session) -> list[str]:
    urls = set()

    for seed in SEED_PAGES:
        try:
            r = get(session, seed)
        except Exception as e:
            print(f"  [TKDK] Seed sayfa atlandı: {seed} — {e}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href]"):
            href = a["href"].strip()
            if href.startswith("/"):
                href = BASE + href
            if not href.startswith("http"):
                continue
                
            # Teşvik ve mevzuatla ilgili olabilecek tüm alt bağlantıları toplayalım
            if any(k in href.lower() for k in ["tesvik", "destek", "tedbir", "program", "m1", "m2", "m3", "m101", "m103", "m302"]):
                urls.add(href)
                
    return list(urls)


def _parse_table(table_el) -> str:
    """TKDK tablolarındaki tüm hibe yüzdelerini ve bütçe sınırlarını kazır."""
    rows_text = []
    for row in table_el.find_all("tr"):
        cols = [col.get_text(" ", strip=True) for col in row.find_all(["td", "th"])]
        if any(cols):
            rows_text.append(" | ".join(cols))
    return "\n".join(rows_text)


def _heading_sections(soup) -> list[dict]:
    sections = []
    content_area = (
        soup.select_one("div.content-area")
        or soup.select_one("div#icerik")
        or soup.select_one("main")
        or soup.select_one("article")
        or soup.select_one(".page-content")
    )
    if not content_area:
        content_area = soup.find("body")

    current_title = "Genel Bilgiler"
    current_lines = []
    current_links = []

    def flush():
        if current_lines or current_links:
            sections.append(
                make_section(
                    current_title,
                    "\n".join(current_lines).strip(),
                    current_links or None,
                )
            )

    # h1'den h5'e, tabloları ve listeleri de içine katarak derin tarama yapıyoruz
    for el in content_area.find_all(["h1", "h2", "h3", "h4", "h5", "p", "li", "table", "a"]):
        tag = el.name
        if tag in ("h1", "h2", "h3", "h4", "h5"):
            flush()
            current_title = el.get_text(strip=True)
            current_lines = []
            current_links = []
        elif tag == "table":
            table_data = _parse_table(el)
            if table_data:
                current_lines.append("\n[Tablo Verisi]\n" + table_data + "\n")
        elif tag == "p":
            text = el.get_text(" ", strip=True)
            if text:
                current_lines.append(text)
            for a in el.find_all("a", href=True):
                href = a["href"].strip()
                if href.startswith("/"):
                    href = BASE + href
                link_text = a.get_text(" ", strip=True)
                if link_text and href:
                    current_links.append({"text": link_text, "href": href})
        elif tag == "li":
            text = el.get_text(" ", strip=True)
            if text:
                current_lines.append(f"- {text}")

    flush()
    return sections


def parse_program(session, url: str) -> dict:
    r = get(session, url)
    soup = BeautifulSoup(r.text, "html.parser")

    title_el = (
        soup.select_one("h1.page-title")
        or soup.select_one("div.page-header h1")
        or soup.select_one("h1")
    )
    program_name = title_el.get_text(strip=True) if title_el else url.split("/")[-1].replace("-", " ").title()

    sections = _heading_sections(soup)

    return make_record(url, "tkdk", program_name, sections)