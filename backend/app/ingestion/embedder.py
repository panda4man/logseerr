import httpx


async def embed_text(embed_url: str, model: str, text: str) -> list[float]:
    """
    Calls an OpenAI-compatible /v1/embeddings endpoint.
    If your embed server uses a different format, update this file only.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{embed_url}/v1/embeddings",
            json={"input": text, "model": model},
            timeout=30,
        )
        resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]
