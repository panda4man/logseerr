from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .loki import LokiStream

CHUNK_WINDOW_NS = 5 * 60 * 1_000_000_000  # 5 minutes in nanoseconds

_LEVEL_LABEL_KEYS = ("level", "detected_level")


@dataclass
class LogChunk:
    service: str
    start_time: datetime
    end_time: datetime
    log_text: str
    levels: list[str] = field(default_factory=list)

    @property
    def time_range(self) -> str:
        return (
            f"{self.start_time.strftime('%Y-%m-%d %H:%M')}"
            f"–{self.end_time.strftime('%H:%M')} UTC"
        )

    @property
    def embedding_text(self) -> str:
        levels = ",".join(self.levels)
        return (
            f"service: {self.service}\n"
            f"levels: {levels}\n"
            f"time: {self.time_range}\n"
            f"{self.log_text}"
        )


def chunk_streams(streams: list[LokiStream]) -> list[LogChunk]:
    lines_by_bucket: dict[tuple[str, int], list[str]] = defaultdict(list)
    levels_by_bucket: dict[tuple[str, int], set[str]] = defaultdict(set)

    for stream in streams:
        stream_levels = {
            stream.labels[k]
            for k in _LEVEL_LABEL_KEYS
            if k in stream.labels and stream.labels[k]
        }
        for ts_ns, line in stream.values:
            bucket_start_ns = (ts_ns // CHUNK_WINDOW_NS) * CHUNK_WINDOW_NS
            key = (stream.service, bucket_start_ns)
            lines_by_bucket[key].append(line)
            levels_by_bucket[key].update(stream_levels)

    chunks = []
    for (service, bucket_start_ns), lines in sorted(lines_by_bucket.items()):
        levels = sorted(levels_by_bucket[(service, bucket_start_ns)])
        chunks.append(
            LogChunk(
                service=service,
                start_time=datetime.fromtimestamp(bucket_start_ns / 1e9, tz=timezone.utc),
                end_time=datetime.fromtimestamp(
                    (bucket_start_ns + CHUNK_WINDOW_NS) / 1e9, tz=timezone.utc
                ),
                log_text="\n".join(lines),
                levels=levels,
            )
        )
    return chunks
