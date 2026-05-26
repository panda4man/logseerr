import json
import pytest
import respx
import httpx
from app.ingestion.embedder import embed_text

EMBED_URL = "http://embed-server:8080"
MODEL = "nomic-embed-text"
SAMPLE_VECTOR = [0.1, 0.2, 0.3, 0.4]


@respx.mock
async def test_embed_text_returns_vector():
    respx.post(f"{EMBED_URL}/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [{"embedding": SAMPLE_VECTOR}]})
    )
    result = await embed_text(EMBED_URL, MODEL, "some log text")
    assert result == SAMPLE_VECTOR


@respx.mock
async def test_embed_text_sends_correct_payload():
    route = respx.post(f"{EMBED_URL}/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [{"embedding": SAMPLE_VECTOR}]})
    )
    await embed_text(EMBED_URL, MODEL, "hello")
    body = json.loads(route.calls[0].request.content)
    assert body["input"] == "hello"
    assert body["model"] == MODEL


@respx.mock
async def test_embed_text_raises_on_server_error():
    respx.post(f"{EMBED_URL}/v1/embeddings").mock(return_value=httpx.Response(503))
    with pytest.raises(httpx.HTTPStatusError):
        await embed_text(EMBED_URL, MODEL, "text")
