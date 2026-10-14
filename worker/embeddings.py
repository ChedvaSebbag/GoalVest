"""הטמעה עם Ollama bge-m3, ב-batches של 32. ראו docs/10 §10.2."""

import requests

_BATCH = 32


def embed_texts(texts: list[str], *, base_url: str, model: str, post=None) -> list[list[float]]:
    send = post or requests.post
    vectors: list[list[float]] = []
    for offset in range(0, len(texts), _BATCH):
        batch = texts[offset : offset + _BATCH]
        response = send(
            f"{base_url.rstrip('/')}/api/embed",
            json={"model": model, "input": batch},
            timeout=120,
        )
        response.raise_for_status()
        body = response.json()
        embeddings = body.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(batch):
            raise ValueError("תשובת ההטמעה אינה תקינה")
        vectors.extend(embeddings)
    return vectors
