import httpx
from dataclasses import dataclass, field


@dataclass
class LokiStream:
    service: str
    values: list[tuple[int, str]]
    labels: dict[str, str] = field(default_factory=dict)


def _derive_service(labels: dict[str, str]) -> str:
    return (
        labels.get("job")
        or labels.get("compose_service")
        or labels.get("container")
        or labels.get("app", "unknown")
    )


async def fetch_streams(
    loki_url: str,
    start_ns: int,
    end_ns: int,
    *,
    page_limit: int = 5000,
    max_pages: int = 50,
) -> list[LokiStream]:
    accum: dict[frozenset, dict] = {}
    insertion_order: list[frozenset] = []
    current_start = start_ns

    async with httpx.AsyncClient() as client:
        for _ in range(max_pages):
            params = {
                "query": '{container!=""}',
                "start": str(current_start),
                "end": str(end_ns),
                "limit": str(page_limit),
                "direction": "forward",
            }
            resp = await client.get(
                f"{loki_url}/loki/api/v1/query_range",
                params=params,
                timeout=60,
            )
            resp.raise_for_status()

            page_results = resp.json()["data"]["result"]
            entry_count = 0
            max_ts_this_page = -1
            for result in page_results:
                labels = result["stream"]
                key = frozenset(labels.items())
                if key not in accum:
                    accum[key] = {"labels": labels, "values": []}
                    insertion_order.append(key)
                for ts_str, line in result["values"]:
                    ts = int(ts_str)
                    accum[key]["values"].append((ts, line))
                    entry_count += 1
                    if ts > max_ts_this_page:
                        max_ts_this_page = ts

            if entry_count == 0 or entry_count < page_limit:
                break

            new_start = max_ts_this_page + 1
            if new_start <= current_start:
                break
            current_start = new_start

    streams = []
    for key in insertion_order:
        data = accum[key]
        streams.append(
            LokiStream(
                service=_derive_service(data["labels"]),
                values=data["values"],
                labels=data["labels"],
            )
        )
    return streams
