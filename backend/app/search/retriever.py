from datetime import datetime

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, Range


async def search_chunks(
    client: AsyncQdrantClient,
    collection_name: str,
    query_vector: list[float],
    since: datetime | None = None,
    top_k: int = 10,
    min_score: float | None = None,
) -> list[dict]:
    query_filter = None
    if since is not None:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="start_time",
                    range=Range(gte=since.timestamp()),
                )
            ]
        )

    results = await client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
    )

    hits = []
    for hit in results.points:
        if min_score is not None and hit.score < min_score:
            continue
        payload = hit.payload or {}
        hits.append(
            {
                "service": payload.get("service", "unknown"),
                "time_range": payload.get("time_range", ""),
                "log_text": payload.get("log_text", ""),
                "levels": payload.get("levels", []),
                "score": hit.score,
            }
        )
    return hits
