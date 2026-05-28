import uuid
from datetime import datetime

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from .chunker import LogChunk


async def ensure_collection(
    client: AsyncQdrantClient, collection_name: str, vector_size: int
) -> None:
    existing = await client.get_collections()
    names = [c.name for c in existing.collections]
    if collection_name not in names:
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def _chunk_id(service: str, start_time: datetime) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{service}:{start_time.isoformat()}"))


async def upsert_chunks(
    client: AsyncQdrantClient,
    collection_name: str,
    chunks: list[LogChunk],
    vectors: list[list[float]],
) -> None:
    if not chunks:
        return
    points = [
        PointStruct(
            id=_chunk_id(chunk.service, chunk.start_time),
            vector=vector,
            payload={
                "service": chunk.service,
                "start_time": chunk.start_time.timestamp(),
                "end_time": chunk.end_time.timestamp(),
                "time_range": chunk.time_range,
                "log_text": chunk.log_text,
                "levels": chunk.levels,
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]
    await client.upsert(collection_name=collection_name, points=points)
