"""
KOSGEB Deep Scraper
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

    # Tüm olası detay bağlantılarını daha agresif tarıyoruz
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "destekdetay" in href or "destek-program" in href:
            if href.startswith("/"):
                href = BASE + href
            elif not href.startswith("http"):
                href = f"{BASE}/{href.lstrip('/')}"
            urls.add(href)

    return sorted(urls)


def _extract_links(element) -> list[dict]:
    links = []
    for a in element.select("a[href]"):
        href = a["href"].strip()
        text = a.get_text(" ", strip=True)
        if text and href:
            if href.startswith("/"):
                href = BASE + href
            links.append({"text": text, "href": href})
    return links


def _parse_table(table_el) -> str:
    """Tablolardaki satır ve sütun verilerini anlamlı bir metne dönüştürür."""
    rows_text = []
    for row in table_el.find_all("tr"):
        cols = [col.get_text(" ", strip=True) for col in row.find_all(["td", "th"])]
        if any(cols):
            rows_text.append(" | ".join(cols))
    return "\n".join(rows_text)


def parse_program(session, url: str) -> dict:
    r = get(session, url)
    soup = BeautifulSoup(r.text, "html.parser")

    # Program adını yakalamak için daha fazla yedekli seçici ekledik
    h1 = soup.select_one("h1")
    h3 = soup.select_one("div.heading h3") or soup.select_one("h3")
    program_name = ""
    if h3:
        program_name = h3.get_text(strip=True)
    elif h1:
        program_name = h1.get_text(strip=True)
    else:
        program_name = url.split("/")[-1].replace("-", " ").title()

    sections = []

    # 1. Aşama: Akordeon öğelerini tara (varsa)
    accordion_items = soup.select("div.accordion-item")
    if accordion_items:
        for item in accordion_items:
            title_el = item.select_one("h4.accordion-toggle") or item.select_one(".accordion-header")
            body_el = item.select_one("section.accordion-inner") or item.select_one(".accordion-body")

            if not title_el or not body_el:
                continue

            title = title_el.get_text(strip=True)
            
            # Akordeon içindeki tabloları da okuyoruz
            table_texts = []
            for tbl in body_el.find_all("table"):
                table_texts.append(_parse_table(tbl))
                tbl.decompose()  # Mükerrerliği önlemek için tabloyu ana metinden siliyoruz
                
            content = body_el.get_text(" ", strip=True)
            if table_texts:
                content += "\n\nTablo Verileri:\n" + "\n".join(table_texts)

            links = _extract_links(body_el)
            sections.append(make_section(title, content, links or None))

    # 2. Aşama: Akordeon yoksa veya ek içerik varsa, ana gövdeyi derinlemesine tara
    content_div = soup.select_one("div.content, div.page-content, article, div.entry-content")
    if content_div and len(sections) == 0:
        # Başlık ve paragrafları hiyerarşik olarak grupla
        current_title = "Genel Bilgiler"
        current_lines = []
        current_links = []

        for child in content_div.find_all(["h2", "h3", "h4", "p", "table", "ul"]):
            if child.name in ["h2", "h3", "h4"]:
                if current_lines:
                    sections.append(make_section(current_title, "\n".join(current_lines), current_links or None))
                current_title = child.get_text(strip=True)
                current_lines = []
                current_links = []
            elif child.name == "p":
                txt = child.get_text(" ", strip=True)
                if txt:
                    current_lines.append(txt)
                current_links.extend(_extract_links(child))
            elif child.name == "ul":
                for li in child.find_all("li"):
                    txt = li.get_text(" ", strip=True)
                    if txt:
                        current_lines.append(f"- {txt}")
                current_links.extend(_extract_links(child))
            elif child.name == "table":
                current_lines.append(_parse_table(child))

        if current_lines:
            sections.append(make_section(current_title, "\n".join(current_lines), current_links or None))

    return make_record(url, "kosgeb", program_name, sections)