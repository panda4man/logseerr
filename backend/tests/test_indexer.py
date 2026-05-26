import pytest
from datetime import datetime, timezone
from qdrant_client import AsyncQdrantClient
from app.ingestion.chunker import LogChunk
from app.ingestion.indexer import ensure_collection, upsert_chunks

COLLECTION = "test_logseerr"
VECTOR_SIZE = 4


@pytest.fixture
async def qdrant():
    client = AsyncQdrantClient(location=":memory:")
    yield client
    await client.close()


async def test_ensure_collection_creates_collection(qdrant):
    await ensure_collection(qdrant, COLLECTION, VECTOR_SIZE)
    collections = await qdrant.get_collections()
    names = [c.name for c in collections.collections]
    assert COLLECTION in names


async def test_ensure_collection_is_idempotent(qdrant):
    await ensure_collection(qdrant, COLLECTION, VECTOR_SIZE)
    await ensure_collection(qdrant, COLLECTION, VECTOR_SIZE)
    collections = await qdrant.get_collections()
    names = [c.name for c in collections.collections]
    assert names.count(COLLECTION) == 1


async def test_upsert_chunks_stores_payload(qdrant):
    await ensure_collection(qdrant, COLLECTION, VECTOR_SIZE)
    chunk = LogChunk(
        service="plex",
        start_time=datetime(2024, 5, 27, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2024, 5, 27, 0, 5, tzinfo=timezone.utc),
        log_text="stream started\nbuffering error",
    )
    await upsert_chunks(qdrant, COLLECTION, [chunk], [[0.1, 0.2, 0.3, 0.4]])
    results = await qdrant.scroll(COLLECTION, limit=10, with_payload=True)
    assert len(results[0]) == 1
    payload = results[0][0].payload
    assert payload["service"] == "plex"
    assert payload["log_text"] == "stream started\nbuffering error"


async def test_upsert_is_idempotent(qdrant):
    await ensure_collection(qdrant, COLLECTION, VECTOR_SIZE)
    chunk = LogChunk(
        service="plex",
        start_time=datetime(2024, 5, 27, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2024, 5, 27, 0, 5, tzinfo=timezone.utc),
        log_text="some log",
    )
    await upsert_chunks(qdrant, COLLECTION, [chunk], [[0.1, 0.2, 0.3, 0.4]])
    await upsert_chunks(qdrant, COLLECTION, [chunk], [[0.1, 0.2, 0.3, 0.4]])
    results = await qdrant.scroll(COLLECTION, limit=10)
    assert len(results[0]) == 1  # deterministic ID prevents duplicates
