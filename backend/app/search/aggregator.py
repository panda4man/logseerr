"""Deterministic aggregation over indexed log chunks.

Powers meta-questions ("which container has the most errors", "how many
containers have errors") that single-shot semantic RAG cannot answer. Counting
is exact Python over the whole (optionally time-filtered) corpus; the LLM only
phrases the precomputed stats.

Granularity note: a "chunk" is one 5-minute window for one service (see
``chunker.py``). ``levels`` is the set of distinct level labels seen in that
window, derived from Loki stream labels — not a per-line error count. So error
figures here count error-active windows, not individual error lines.
"""
from collections import defaultdict
from datetime import datetime

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, Range

ERROR_LEVELS = {"error", "err", "critical", "crit", "fatal", "emergency", "alert"}

_SCROLL_PAGE = 256


async def scroll_all_chunks(
    client: AsyncQdrantClient,
    collection_name: str,
    since: datetime | None = None,
    max_chunks: int = 10000,
) -> tuple[list[dict], bool]:
    """Pull every chunk payload (no vectors), optionally filtered by start_time.

    Returns ``(chunks, truncated)`` where ``truncated`` is True if the
    ``max_chunks`` cap was reached before the corpus was exhausted.
    """
    scroll_filter = None
    if since is not None:
        scroll_filter = Filter(
            must=[
                FieldCondition(
                    key="start_time",
                    range=Range(gte=since.timestamp()),
                )
            ]
        )

    chunks: list[dict] = []
    offset = None
    truncated = False
    while True:
        points, offset = await client.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=_SCROLL_PAGE,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in points:
            payload = point.payload or {}
            chunks.append(
                {
                    "service": payload.get("service", "unknown"),
                    "time_range": payload.get("time_range", ""),
                    "start_time": payload.get("start_time"),
                    "levels": payload.get("levels", []),
                }
            )
            if len(chunks) >= max_chunks:
                truncated = True
                break
        if truncated or offset is None:
            break
    return chunks, truncated


def aggregate_by_service(chunks: list[dict]) -> list[dict]:
    """Group chunks by service, counting error-active windows and levels.

    Sorted by ``error_chunk_count`` descending, then ``chunk_count`` descending.
    """
    chunk_count: dict[str, int] = defaultdict(int)
    error_chunk_count: dict[str, int] = defaultdict(int)
    level_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for chunk in chunks:
        service = chunk.get("service", "unknown")
        chunk_count[service] += 1
        levels = [str(lvl).lower() for lvl in chunk.get("levels", [])]
        for lvl in levels:
            level_counts[service][lvl] += 1
        if any(lvl in ERROR_LEVELS for lvl in levels):
            error_chunk_count[service] += 1

    per_service = [
        {
            "service": service,
            "chunk_count": chunk_count[service],
            "error_chunk_count": error_chunk_count[service],
            "distinct_levels": sorted(level_counts[service]),
            "level_counts": dict(level_counts[service]),
        }
        for service in chunk_count
    ]
    per_service.sort(key=lambda s: (-s["error_chunk_count"], -s["chunk_count"], s["service"]))
    return per_service


def build_stats_summary(
    per_service: list[dict], since: datetime | None, truncated: bool
) -> str:
    """Render a compact, deterministic stats block for the LLM prompt."""
    total_chunks = sum(s["chunk_count"] for s in per_service)
    containers_with_errors = [s for s in per_service if s["error_chunk_count"] > 0]

    window = (
        f"since {since.strftime('%Y-%m-%d %H:%M')} UTC" if since is not None else "all time"
    )

    lines = [
        f"Time window: {window}",
        f"Total log windows (5-min each): {total_chunks}",
        f"Distinct containers: {len(per_service)}",
        f"Distinct containers with errors: {len(containers_with_errors)}",
        "",
        "Per-container (error_windows / total_windows | levels):",
    ]
    for s in per_service:
        levels = ", ".join(f"{lvl}={n}" for lvl, n in sorted(s["level_counts"].items()))
        lines.append(
            f"- {s['service']}: {s['error_chunk_count']} / {s['chunk_count']}"
            f"{f' | {levels}' if levels else ''}"
        )
    if truncated:
        lines.append("")
        lines.append(
            "NOTE: results truncated at the scan cap; counts are a lower bound, not complete."
        )
    return "\n".join(lines)
