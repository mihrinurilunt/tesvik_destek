"""
TÜBİTAK Deep Scraper
"""

from bs4 import BeautifulSoup
from utils.http import get
from utils.models import make_record, make_section

BASE = "https://tubitak.gov.tr"
INDEX = f"{BASE}/tr/destekler"

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

        if href.startswith("/"):
            href = BASE + href

        if not href.startswith(BASE):
            continue

        path = href.replace(BASE, "")

        if not any(path.startswith(p) for p in _PROGRAM_PREFIXES):
            continue

        segments = [s for s in path.split("/") if s]
        if len(segments) < 3:  # Daha derin olmayan kategorileri de yakalayabilmek için limiti 3'e çektik
            continue

        urls.add(href)

    return sorted(urls)


def _parse_table(table_el) -> str:
    rows_text = []
    for row in table_el.find_all("tr"):
        cols = [col.get_text(" ", strip=True) for col in row.find_all(["td", "th"])]
        if any(cols):
            rows_text.append(" | ".join(cols))
    return "\n".join(rows_text)


def _parse_text_sections(soup) -> list[dict]:
    sections = []
    
    # Sadece field--name-field-icerik değil, Drupal body alanlarını da kapsama alıyoruz
    block = (
        soup.select_one("div.paragraph--type--duz-metin .field--name-field-icerik")
        or soup.select_one(".field--name-body")
        or soup.select_one("div.node__content")
    )
    if not block:
        return sections

    current_title = "Genel Bilgiler"
    current_lines = []

    # p, table, ul, ol elemanlarını sırayla işliyoruz
    for el in block.find_all(["p", "table", "ul", "ol"]):
        if el.name == "p":
            strong = el.find("strong")
            # Eğer paragraf <strong> ile başlıyorsa yeni bir bölüme (section) geçiyoruz
            if strong and strong.get_text(strip=True) and len(strong.get_text(strip=True)) < 50:
                if current_lines:
                    sections.append(
                        make_section(current_title, "\n".join(current_lines).strip())
                    )
                current_title = strong.get_text(strip=True).rstrip(":")
                rest = el.get_text(" ", strip=True).replace(strong.get_text(strip=True), "").strip().lstrip(":")
                current_lines = [rest] if rest else []
            else:
                text = el.get_text(" ", strip=True)
                if text:
                    current_lines.append(text)
        elif el.name == "table":
            table_text = _parse_table(el)
            if table_text:
                current_lines.append("\n[Tablo Verisi]\n" + table_text + "\n")
        elif el.name in ["ul", "ol"]:
            for li in el.find_all("li"):
                li_text = li.get_text(" ", strip=True)
                if li_text:
                    current_lines.append(f"- {li_text}")

    if current_lines:
        sections.append(
            make_section(current_title, "\n".join(current_lines).strip())
        )

    return sections


def _parse_file_sections(soup) -> list[dict]:
    sections = []
    # Dosya indirme listeleri (Uygulama Esasları vb.)
    for block in soup.select("div.paragraph--type--dosya-listesi-media, .field--name-field-dosyalar"):
        baslik_el = block.select_one(".field--name-field-baslik") or block.select_one("h3")
        title = baslik_el.get_text(strip=True) if baslik_el else "İlgili Belgeler ve Başvuru Formları"

        links = []
        for a in block.select("a[href]"):
            href = a["href"].strip()
            if href.startswith("/"):
                href = BASE + href
            text = a.get_text(" ", strip=True)
            if text and href:
                links.append({"text": text, "href": href})

        if links:
            sections.append(make_section(title, "Bu bölümde programla ilgili resmi dökümanlar yer almaktadır.", links))

    return sections


def parse_program(session, url: str) -> dict:
    r = get(session, url)
    soup = BeautifulSoup(r.text, "html.parser")

    h1 = soup.select_one("h1 span") or soup.select_one("h1")
    program_name = h1.get_text(strip=True) if h1 else url.split("/")[-1].replace("-", " ").title()

    sections = _parse_text_sections(soup) + _parse_file_sections(soup)

    return make_record(url, "tubitak", program_name, sections)