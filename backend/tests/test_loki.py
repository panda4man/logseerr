import pytest
import respx
import httpx
from app.ingestion.loki import fetch_streams, LokiStream

LOKI_URL = "http://loki:3100"

SAMPLE_RESPONSE = {
    "status": "success",
    "data": {
        "resultType": "streams",
        "result": [
            {
                "stream": {"job": "plex"},
                "values": [
                    ["1716768000000000000", "stream started"],
                    ["1716768060000000000", "buffering error"],
                ],
            },
            {
                "stream": {"job": "sonarr"},
                "values": [["1716768120000000000", "episode downloaded"]],
            },
        ],
    },
}


@respx.mock
async def test_fetch_streams_returns_streams():
    respx.get(f"{LOKI_URL}/loki/api/v1/query_range").mock(
        return_value=httpx.Response(200, json=SAMPLE_RESPONSE)
    )
    streams = await fetch_streams(LOKI_URL, start_ns=0, end_ns=9999999999999999999)
    assert len(streams) == 2
    assert streams[0].service == "plex"
    assert len(streams[0].values) == 2
    assert streams[0].values[0] == (1716768000000000000, "stream started")
    assert streams[1].service == "sonarr"


@respx.mock
async def test_fetch_streams_uses_app_label_fallback():
    response = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {
                    "stream": {"app": "myapp"},
                    "values": [["1716768000000000000", "log line"]],
                }
            ],
        },
    }
    respx.get(f"{LOKI_URL}/loki/api/v1/query_range").mock(
        return_value=httpx.Response(200, json=response)
    )
    streams = await fetch_streams(LOKI_URL, start_ns=0, end_ns=9999)
    assert streams[0].service == "myapp"


@respx.mock
async def test_fetch_streams_raises_on_http_error():
    respx.get(f"{LOKI_URL}/loki/api/v1/query_range").mock(
        return_value=httpx.Response(500)
    )
    with pytest.raises(httpx.HTTPStatusError):
        await fetch_streams(LOKI_URL, start_ns=0, end_ns=9999)


@respx.mock
async def test_lokistream_carries_labels():
    response = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {
                    "stream": {"job": "plex", "level": "error", "container": "plex"},
                    "values": [["1000", "oops"]],
                }
            ],
        },
    }
    respx.get(f"{LOKI_URL}/loki/api/v1/query_range").mock(
        return_value=httpx.Response(200, json=response)
    )
    streams = await fetch_streams(LOKI_URL, start_ns=0, end_ns=9999)
    assert streams[0].labels == {"job": "plex", "level": "error", "container": "plex"}


@respx.mock
async def test_fetch_streams_paginates_until_short_page():
    page1 = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {"stream": {"job": "plex"}, "values": [["1000", "a"], ["2000", "b"]]}
            ],
        },
    }
    page2 = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {"stream": {"job": "plex"}, "values": [["3000", "c"]]}
            ],
        },
    }
    route = respx.get(f"{LOKI_URL}/loki/api/v1/query_range").mock(
        side_effect=[
            httpx.Response(200, json=page1),
            httpx.Response(200, json=page2),
        ]
    )
    streams = await fetch_streams(
        LOKI_URL, start_ns=0, end_ns=9999, page_limit=2
    )
    assert route.call_count == 2
    assert len(streams) == 1
    assert streams[0].service == "plex"
    assert [v[0] for v in streams[0].values] == [1000, 2000, 3000]


@respx.mock
async def test_fetch_streams_respects_max_pages():
    # Each call returns a full page with a fresh, advancing ts so the loop
    # would keep going indefinitely. max_pages must cap it.
    pages = [
        {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"job": "plex"},
                        "values": [
                            [str(base + 0), "a"],
                            [str(base + 100), "b"],
                        ],
                    }
                ],
            },
        }
        for base in (1000, 3000, 5000, 7000, 9000)
    ]
    route = respx.get(f"{LOKI_URL}/loki/api/v1/query_range").mock(
        side_effect=[httpx.Response(200, json=p) for p in pages]
    )
    await fetch_streams(
        LOKI_URL, start_ns=0, end_ns=99999, page_limit=2, max_pages=3
    )
    assert route.call_count == 3
