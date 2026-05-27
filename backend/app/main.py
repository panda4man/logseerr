import logging
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import httpx

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient

from .config import settings
from .ingestion.chunker import chunk_streams
from .ingestion.embedder import embed_text
from .ingestion.indexer import ensure_collection, upsert_chunks
from .ingestion.loki import fetch_streams
from .search.llm import generate_answer
from .search.retriever import search_chunks

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

qdrant = AsyncQdrantClient(url=settings.qdrant_url)
scheduler = AsyncIOScheduler()

_TIME_PATTERNS: list[tuple[re.Pattern, callable]] = [
    (re.compile(r"last\s+(\d+)\s+hours?", re.I), lambda m: timedelta(hours=int(m.group(1)))),
    (re.compile(r"last\s+(\d+)\s+days?", re.I), lambda m: timedelta(days=int(m.group(1)))),
    (re.compile(r"last\s+(\d+)\s+weeks?", re.I), lambda m: timedelta(weeks=int(m.group(1)))),
    (re.compile(r"last\s+24\s+hours?", re.I), lambda _: timedelta(hours=24)),
    (re.compile(r"last\s+hour", re.I), lambda _: timedelta(hours=1)),
    (re.compile(r"last\s+week", re.I), lambda _: timedelta(weeks=1)),
    (re.compile(r"\btoday\b", re.I), lambda _: timedelta(hours=24)),
    (re.compile(r"\byesterday\b", re.I), lambda _: timedelta(hours=48)),
]


def _parse_time_filter(query: str) -> datetime | None:
    for pattern, delta_fn in _TIME_PATTERNS:
        m = pattern.search(query)
        if m:
            return datetime.now(tz=timezone.utc) - delta_fn(m)
    return None


async def run_ingestion() -> None:
    logger.info("Ingestion run starting")
    now_ns = time.time_ns()
    lookback_ns = settings.ingest_interval_minutes * 60 * 1_000_000_000 * 2

    try:
        streams = await fetch_streams(
            loki_url=settings.loki_url,
            start_ns=now_ns - lookback_ns,
            end_ns=now_ns,
        )
    except Exception:
        logger.exception("Failed to fetch from Loki — skipping run")
        return

    chunks = chunk_streams(streams)
    if not chunks:
        logger.info("No log chunks to index")
        return

    vectors, valid_chunks = [], []
    for chunk in chunks:
        try:
            vector = await embed_text(settings.embed_url, settings.embed_model, chunk.log_text)
            vectors.append(vector)
            valid_chunks.append(chunk)
        except Exception:
            logger.exception("Embed failed for %s/%s — skipping", chunk.service, chunk.start_time)

    if not valid_chunks:
        return

    await ensure_collection(qdrant, settings.collection_name, len(vectors[0]))
    await upsert_chunks(qdrant, settings.collection_name, valid_chunks, vectors)
    logger.info("Ingestion complete: %d chunks indexed", len(valid_chunks))


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        run_ingestion, "interval", minutes=settings.ingest_interval_minutes, id="ingestion"
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="logseerr", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str


class SearchResponse(BaseModel):
    answer: str | None
    sources: list[dict]


@app.get("/health")
async def health():
    checks: dict[str, str] = {}

    # Qdrant
    try:
        await qdrant.get_collections()
        checks["qdrant"] = "ok"
    except Exception:
        checks["qdrant"] = "unavailable"

    # Embed server (Ollama embeddings instance)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.embed_url}/api/tags", timeout=5)
            resp.raise_for_status()
        checks["embed"] = "ok"
    except Exception:
        checks["embed"] = "unavailable"

    # LLM server (Ollama)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.ollama_url}/api/tags", timeout=5)
            resp.raise_for_status()
        checks["llm"] = "ok"
    except Exception:
        checks["llm"] = "unavailable"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503
    return JSONResponse(content={"status": "ok" if all_ok else "degraded", **checks}, status_code=status_code)


@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    try:
        query_vector = await embed_text(settings.embed_url, settings.embed_model, req.query)
    except Exception:
        raise HTTPException(status_code=503, detail="Embedding service unavailable")

    since = _parse_time_filter(req.query)

    try:
        sources = await search_chunks(qdrant, settings.collection_name, query_vector, since=since)
    except Exception:
        raise HTTPException(status_code=503, detail="Vector search unavailable")

    answer = await generate_answer(settings.ollama_url, settings.ollama_model, req.query, sources)
    return SearchResponse(answer=answer, sources=sources)
