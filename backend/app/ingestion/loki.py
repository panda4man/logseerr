import httpx
from dataclasses import dataclass


@dataclass
class LokiStream:
    service: str
    values: list[tuple[int, str]]


async def fetch_streams(loki_url: str, start_ns: int, end_ns: int) -> list[LokiStream]:
    params = {
        "query": '{container=~".+"}',
        "start": str(start_ns),
        "end": str(end_ns),
        "limit": "5000",
        "direction": "forward",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{loki_url}/loki/api/v1/query_range",
            params=params,
            timeout=30,
        )
        resp.raise_for_status()

    streams = []
    for result in resp.json()["data"]["result"]:
        labels = result["stream"]
        service = labels.get("job") or labels.get("compose_service") or labels.get("container") or labels.get("app", "unknown")
        values = [(int(ts), line) for ts, line in result["values"]]
        streams.append(LokiStream(service=service, values=values))
    return streams
