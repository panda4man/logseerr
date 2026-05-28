import pytest
from datetime import datetime, timezone
from qdrant_client import AsyncQdrantClient
from app.ingestion.chunker import LogChunk
from app.ingestion.indexer import ensure_collection, upsert_chunks
from app.search.aggregator import (
    aggregate_by_service,
    build_stats_summary,
    scroll_all_chunks,
)

COLLECTION = "test_agg"
VECTOR_SIZE = 4


def _chunk(service, hour, levels):
    return LogChunk(
        service=service,
        start_time=datetime(2024, 5, 27, hour, 0, tzinfo=timezone.utc),
        end_time=datetime(2024, 5, 27, hour, 5, tzinfo=timezone.utc),
        log_text=f"{service} line",
        levels=levels,
    )


@pytest.fixture
async def populated_qdrant():
    client = AsyncQdrantClient(location=":memory:")
    await ensure_collection(client, COLLECTION, VECTOR_SIZE)
    # plex: 2 error windows; sonarr: 1 error window; radarr: 0 error windows
    chunks = [
        _chunk("plex", 20, ["error"]),
        _chunk("plex", 21, ["warn", "error"]),
        _chunk("sonarr", 21, ["error"]),
        _chunk("radarr", 21, ["info"]),
    ]
    vectors = [[1.0, 0.0, 0.0, 0.0]] * len(chunks)
    await upsert_chunks(client, COLLECTION, chunks, vectors)
    yield client
    await client.close()


async def test_scroll_returns_all_chunks(populated_qdrant):
    chunks, truncated = await scroll_all_chunks(populated_qdrant, COLLECTION)
    assert len(chunks) == 4
    assert truncated is False
    assert {c["service"] for c in chunks} == {"plex", "sonarr", "radarr"}


async def test_scroll_respects_time_filter(populated_qdrant):
    since = datetime(2024, 5, 27, 21, 0, tzinfo=timezone.utc)
    chunks, _ = await scroll_all_chunks(populated_qdrant, COLLECTION, since=since)
    # plex@20:00 excluded; plex@21, sonarr@21, radarr@21 remain
    assert len(chunks) == 3
    assert all(c["service"] != "plex" or c["time_range"].startswith("2024-05-27 21") for c in chunks)


async def test_scroll_truncates_at_cap(populated_qdrant):
    chunks, truncated = await scroll_all_chunks(populated_qdrant, COLLECTION, max_chunks=2)
    assert len(chunks) == 2
    assert truncated is True


def test_aggregate_counts_error_windows_and_orders():
    chunks = [
        {"service": "plex", "levels": ["error"]},
        {"service": "plex", "levels": ["warn", "error"]},
        {"service": "sonarr", "levels": ["error"]},
        {"service": "radarr", "levels": ["info"]},
    ]
    result = aggregate_by_service(chunks)
    by_service = {s["service"]: s for s in result}

    assert by_service["plex"]["error_chunk_count"] == 2
    assert by_service["plex"]["chunk_count"] == 2
    assert by_service["sonarr"]["error_chunk_count"] == 1
    assert by_service["radarr"]["error_chunk_count"] == 0
    # sorted by error_chunk_count desc → plex first
    assert result[0]["service"] == "plex"
    assert by_service["plex"]["level_counts"]["error"] == 2
    assert by_service["plex"]["level_counts"]["warn"] == 1


def test_aggregate_error_level_matching_is_case_insensitive():
    chunks = [{"service": "x", "levels": ["ERROR"]}, {"service": "y", "levels": ["Critical"]}]
    result = {s["service"]: s for s in aggregate_by_service(chunks)}
    assert result["x"]["error_chunk_count"] == 1
    assert result["y"]["error_chunk_count"] == 1


def test_build_stats_summary_includes_totals_and_truncation():
    per_service = aggregate_by_service(
        [
            {"service": "plex", "levels": ["error"]},
            {"service": "radarr", "levels": ["info"]},
        ]
    )
    summary = build_stats_summary(per_service, since=None, truncated=True)
    assert "Distinct containers: 2" in summary
    assert "Distinct containers with errors: 1" in summary
    assert "all time" in summary
    assert "truncated" in summary
    assert "plex" in summary and "radarr" in summary
