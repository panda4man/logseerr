from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from .loki import LokiStream

CHUNK_WINDOW_NS = 5 * 60 * 1_000_000_000  # 5 minutes in nanoseconds


@dataclass
class LogChunk:
    service: str
    start_time: datetime
    end_time: datetime
    log_text: str


def chunk_streams(streams: list[LokiStream]) -> list[LogChunk]:
    buckets: dict[tuple[str, int], list[str]] = defaultdict(list)

    for stream in streams:
        for ts_ns, line in stream.values:
            bucket_start_ns = (ts_ns // CHUNK_WINDOW_NS) * CHUNK_WINDOW_NS
            buckets[(stream.service, bucket_start_ns)].append(line)

    chunks = []
    for (service, bucket_start_ns), lines in sorted(buckets.items()):
        chunks.append(
            LogChunk(
                service=service,
                start_time=datetime.fromtimestamp(bucket_start_ns / 1e9, tz=timezone.utc),
                end_time=datetime.fromtimestamp(
                    (bucket_start_ns + CHUNK_WINDOW_NS) / 1e9, tz=timezone.utc
                ),
                log_text="\n".join(lines),
            )
        )
    return chunks
