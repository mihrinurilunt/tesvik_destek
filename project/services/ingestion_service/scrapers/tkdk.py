"""
TKDK scraper
Index : https://www.tkdk.gov.tr/ipard/ipardprogrami  (ve alt sayfalar)
Detail: program sayfaları

TKDK sitesi tek bir büyük IPARD programını çeşitli destekleme tedbirleri
(measure) üzerinden anlatır. Her tedbir ayrı bir sayfa.

Tedbir URL pattern:
  https://www.tkdk.gov.tr/ipard/{slug}
  https://www.tkdk.gov.tr/Icerik/{id}/{slug}

Page structure: genel HTML, <h2>/<h3> başlıkları + <p> paragrafları + tablolar
"""

from bs4 import BeautifulSoup
from utils.http import get
from utils.models import make_record, make_section

BASE = "https://www.tkdk.gov.tr"

# Ana giriş sayfaları — bunlardan iç linkler toplanır
SEED_PAGES = [
    f"{BASE}/ipard/ipardprogrami",
    f"{BASE}/ipard/ipard3-destekleme-tedbirleri",
    f"{BASE}/Hibe/Takvim",
]


def get_program_urls(session) -> list[str]:
    urls = set()

    for seed in SEED_PAGES:
        try:
            r = get(session, seed)
        except Exception as e:
            print(f"  [TKDK] seed atlandı: {seed} — {e}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a[href]"):
            href = a["href"].strip()
            if href.startswith("/"):
                href = BASE + href
            if not href.startswith(BASE):
                continue
            # Sadece içerik sayfaları — haber/duyuru değil
            path = href.replace(BASE, "").lower()
            skip_keywords = ["haber", "duyuru", "basin", "galeri", "dosya", "pdf", "#"]
            if any(k in path for k in skip_keywords):
                continue
            if len(path.split("/")) >= 2:
                urls.add(href)

    return sorted(urls)


def _heading_sections(soup) -> list[dict]:
    """
    TKDK sayfalarında içerik <h2>/<h3> başlıkları ve altlarındaki
    <p> etiketlerinden oluşur.
    """
    sections = []
    content_area = soup.select_one("div.content-area, div#icerik, main, article")
    if not content_area:
        content_area = soup.find("body")

    current_title = "Genel"
    current_lines = []
    current_links = []

    def flush():
        if current_lines or current_links:
            sections.append(
                make_section(
                    current_title,
                    " ".join(current_lines).strip(),
                    current_links or None,
                )
            )

    for el in content_area.find_all(["h1", "h2", "h3", "h4", "p", "li", "a"]):
        tag = el.name
        if tag in ("h1", "h2", "h3", "h4"):
            flush()
            current_title = el.get_text(strip=True)
            current_lines = []
            current_links = []
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

    # Başlık — çeşitli seçicileri dene
    title_el = (
        soup.select_one("h1.page-title")
        or soup.select_one("div.page-header h1")
        or soup.select_one("h1")
    )
    program_name = title_el.get_text(strip=True) if title_el else url.split("/")[-1]

    sections = _heading_sections(soup)

    return make_record(url, "tkdk", program_name, sections)
