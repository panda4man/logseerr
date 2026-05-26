from datetime import datetime, timezone
from app.ingestion.loki import LokiStream
from app.ingestion.chunker import chunk_streams, CHUNK_WINDOW_NS

# Base timestamp: 2024-05-27 00:00:00 UTC in nanoseconds
BASE_NS = 1716768000000000000


def test_lines_in_same_window_are_combined():
    stream = LokiStream(
        service="plex",
        values=[
            (BASE_NS, "line A"),
            (BASE_NS + 60_000_000_000, "line B"),   # +1 min — same 5-min window
            (BASE_NS + 119_000_000_000, "line C"),  # +1m59s — same window
        ],
    )
    chunks = chunk_streams([stream])
    assert len(chunks) == 1
    assert "line A" in chunks[0].log_text
    assert "line B" in chunks[0].log_text
    assert "line C" in chunks[0].log_text


def test_lines_in_different_windows_produce_separate_chunks():
    stream = LokiStream(
        service="plex",
        values=[
            (BASE_NS, "early"),
            (BASE_NS + CHUNK_WINDOW_NS, "later"),  # exactly one window later
        ],
    )
    chunks = chunk_streams([stream])
    assert len(chunks) == 2


def test_different_services_produce_separate_chunks():
    streams = [
        LokiStream(service="plex", values=[(BASE_NS, "plex log")]),
        LokiStream(service="sonarr", values=[(BASE_NS, "sonarr log")]),
    ]
    chunks = chunk_streams(streams)
    assert len(chunks) == 2
    assert {c.service for c in chunks} == {"plex", "sonarr"}


def test_chunk_has_correct_timestamps():
    stream = LokiStream(service="plex", values=[(BASE_NS, "line")])
    chunks = chunk_streams([stream])
    expected_start_ns = (BASE_NS // CHUNK_WINDOW_NS) * CHUNK_WINDOW_NS
    assert chunks[0].start_time == datetime.fromtimestamp(
        expected_start_ns / 1e9, tz=timezone.utc
    )
    assert chunks[0].end_time == datetime.fromtimestamp(
        (expected_start_ns + CHUNK_WINDOW_NS) / 1e9, tz=timezone.utc
    )


def test_empty_streams_returns_empty():
    assert chunk_streams([]) == []
