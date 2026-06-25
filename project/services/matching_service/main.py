"""
Matching Service — FastAPI
  GET  /health        → servis sağlık kontrolü
  POST /find-matches  → profile en uygun programları bulur (top N, default 3)
"""
import json
import os
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from matcher import ProgramMatcher
from schemas import MatchRequest, MatchResult, UserProfile, ProgramData

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "output.json")
program_database: List[ProgramData] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global program_database
    print(f"Program veritabanı yükleniyor: {DB_PATH}")
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            raw_list = json.load(f)
        loaded = []
        for item in raw_list:
            try:
                loaded.append(ProgramData(**item))
            except Exception:
                pass
        program_database = [p for p in loaded if p.program_name]
        print(f"{len(program_database)} program başarıyla yüklendi.")
    except FileNotFoundError:
        print(f"UYARI: {DB_PATH} bulunamadı. Boş veritabanı ile başlatılıyor.")
        program_database = []
    yield
    program_database.clear()


app = FastAPI(
    title="Matching Service",
    description="Kullanıcı profili ile destek programlarını eşleştiren servis",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

matcher = ProgramMatcher()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "matching_service",
        "programs_loaded": len(program_database),
    }


@app.post("/find-matches", response_model=List[MatchResult], summary="En Uygun Programları Bul")
def find_best_matches(user_profile: UserProfile, limit: int = 3):
    """
    Kullanıcı profiline göre veritabanındaki TÜM programlar
    arasından en yüksek skorlu `limit` programı döndürür.
    """
    if not program_database:
        raise HTTPException(status_code=503, detail="Program veritabanı boş veya yüklenmedi.")
    try:
        results = []
        for program in program_database:
            results.append(matcher.match(MatchRequest(
                user_profile=user_profile,
                program_data=program,
            )))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=traceback.format_exc())