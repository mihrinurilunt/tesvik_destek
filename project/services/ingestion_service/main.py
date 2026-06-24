from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from runner import run_scrapers, SCRAPERS


app = FastAPI(
    title="Ingestion Service",
    description="Scrapes incentive/support program data and produces normalized JSON output.",
    version="0.1.0",
)


class ScrapeRequest(BaseModel):
    sites: Optional[list[str]] = None
    dry_run: bool = False
    resume: bool = True


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ingestion_service",
    }


@app.get("/sites")
def list_sites():
    return {
        "available_sites": list(SCRAPERS.keys())
    }


@app.post("/scrape")
def scrape(request: ScrapeRequest):
    result = run_scrapers(
        sites=request.sites,
        dry_run=request.dry_run,
        resume=request.resume,
    )

    return result