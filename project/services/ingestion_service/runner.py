import json
from pathlib import Path
from typing import Optional

from utils.http import make_session
from scrapers import tubitak
from scrapers import kosgeb, tkdk


SCRAPERS = {
    "kosgeb": kosgeb,
    "tubitak": tubitak,
    "tkdk": tkdk,
}

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

OUTPUT_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = OUTPUT_DIR / "programs.json"

def load_existing() -> list[dict]:
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_records(records: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def already_scraped(records: list[dict]) -> set[str]:
    return {record["url"] for record in records if "url" in record}


def run_scrapers(
    sites: Optional[list[str]] = None,
    dry_run: bool = False,
    resume: bool = True,
) -> dict:
    if sites is None:
        sites = list(SCRAPERS.keys())

    unknown_sites = set(sites) - set(SCRAPERS.keys())

    if unknown_sites:
        return {
            "status": "error",
            "message": f"Unknown site(s): {list(unknown_sites)}",
            "records": [],
            "summary": {},
        }

    session = make_session()
    results = load_existing() if resume else []
    scraped_urls = already_scraped(results)

    summary = {}

    for name in sites:
        scraper = SCRAPERS[name]

        site_summary = {
            "found_urls": 0,
            "new_records": 0,
            "skipped": 0,
            "errors": 0,
        }

        try:
            urls = scraper.get_program_urls(session)
        except Exception as e:
            site_summary["errors"] += 1
            site_summary["error_message"] = str(e)
            summary[name] = site_summary
            continue

        site_summary["found_urls"] = len(urls)

        if dry_run:
            summary[name] = {
                **site_summary,
                "urls": urls,
            }
            continue

        for url in urls:
            if url in scraped_urls:
                site_summary["skipped"] += 1
                continue

            try:
                record = scraper.parse_program(session, url)
                results.append(record)
                scraped_urls.add(url)
                site_summary["new_records"] += 1

                if site_summary["new_records"] % 5 == 0:
                    save_records(results)

            except Exception as e:
                site_summary["errors"] += 1
                results.append(
                    {
                        "url": url,
                        "source": name,
                        "error": str(e),
                        "program_name": None,
                        "sections": [],
                    }
                )

        summary[name] = site_summary

    if not dry_run:
        save_records(results)

    return {
        "status": "success",
        "count": len(results),
        "records": results,
        "summary": summary,
        "output_file": str(OUTPUT_FILE),
    }
