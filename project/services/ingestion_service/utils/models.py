"""
UTILS - MODELS.PY
"""

from datetime import datetime, timezone

import hashlib


def make_program_id(source: str, url: str) -> str:
    raw = f"{source}:{url}"
    hash_part = hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]
    return f"{source}_{hash_part}"

def make_record(url: str, source: str, program_name: str, sections: list) -> dict:
    return {
        "program_id": make_program_id(source, url),
        "url": url,
        "source": source,
        "institution": source.upper(),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "program_name": program_name,
        "sections": sections,
    }


def make_section(title: str, content: str, links: list = None) -> dict:
    section = {"title": title, "content": content}
    if links:
        section["links"] = links
    return section
