import pytest
from datetime import datetime, timezone
from qdrant_client import AsyncQdrantClient
from app.ingestion.chunker import LogChunk
from app.ingestion.indexer import ensure_collection, upsert_chunks
from app.search.retriever import search_chunks

COLLECTION = "test_logseerr"
VECTOR_SIZE = 4


@pytest.fixture
async def populated_qdrant():
    client = AsyncQdrantClient(location=":memory:")
    await ensure_collection(client, COLLECTION, VECTOR_SIZE)
    chunks = [
        LogChunk(
            service="plex",
            start_time=datetime(2024, 5, 27, 21, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 5, 27, 21, 5, tzinfo=timezone.utc),
            log_text="buffering error: stream stalled",
        ),
        LogChunk(
            service="sonarr",
            start_time=datetime(2024, 5, 27, 21, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 5, 27, 21, 5, tzinfo=timezone.utc),
            log_text="episode downloaded successfully",
        ),
    ]
    vectors = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]]
    await upsert_chunks(client, COLLECTION, chunks, vectors)
    yield client
    await client.close()


async def test_search_returns_results(populated_qdrant):
    results = await search_chunks(
        populated_qdrant, COLLECTION, [1.0, 0.0, 0.0, 0.0], top_k=10
    )
    assert len(results) > 0
    assert all("service" in r for r in results)
    assert all("log_text" in r for r in results)
    assert all("time_range" in r for r in results)


async def test_search_respects_top_k(populated_qdrant):
    results = await search_chunks(
        populated_qdrant, COLLECTION, [1.0, 0.0, 0.0, 0.0], top_k=1
    )
    assert len(results) == 1


async def test_search_with_time_filter_excludes_old_chunks(populated_qdrant):
    # Both chunks are on 2024-05-27; filter to after 2024-05-28 → 0 results
    since = datetime(2024, 5, 28, 0, 0, tzinfo=timezone.utc)
    results = await search_chunks(
        populated_qdrant, COLLECTION, [1.0, 0.0, 0.0, 0.0], since=since, top_k=10
    )
    assert len(results) == 0


async def test_search_without_time_filter_returns_all(populated_qdrant):
    results = await search_chunks(
        populated_qdrant, COLLECTION, [1.0, 0.0, 0.0, 0.0], since=None, top_k=10
    )
    assert len(results) == 2
