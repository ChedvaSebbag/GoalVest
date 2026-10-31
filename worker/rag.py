"""חיפוש סמנטי ב-ChromaDB. הסוכן ישתמש בזה. ראו docs/10 §10.3–10.4."""

# Retrieval for RAG: the query is embedded with bge-m3 (Ollama) and the closest chunks are
# fetched from ChromaDB (cosine distance, k=6). Collections: policy_documents, knowledge_base,
# product_profiles. Results are passed to the LLM prompt as cited evidence.

from worker.embeddings import embed_texts

_COLLECTIONS = frozenset({"policy_documents", "knowledge_base", "product_profiles"})


def open_collection(name: str, *, host: str, port: int):
    import chromadb

    if name not in _COLLECTIONS:
        raise ValueError("אוסף לא מוכר")
    client = chromadb.HttpClient(host=host, port=int(port))
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def search_knowledge_base(
    query: str,
    collection: str,
    k: int = 6,
    product_ids: list[str] | None = None,
    *,
    topic: str | None = None,
    store=None,
    embedder=None,
) -> list[dict]:
    """חיפוש סמנטי. מחזיר קטעים עם title, document_id, excerpt ו-score."""
    text = query.strip()
    if not text:
        raise ValueError("חסרה שאילתה")
    if collection not in _COLLECTIONS:
        raise ValueError("אוסף לא מוכר")
    if k < 1:
        raise ValueError("k חייב להיות חיובי")
    embed = embedder or _default_embed
    chroma = store if store is not None else _default_store(collection)
    vector = embed([text])[0]
    found = chroma.query(**_query(vector, k, product_ids, topic))
    documents = _first(found.get("documents"))
    metadatas = _first(found.get("metadatas"))
    distances = _first(found.get("distances"))
    items: list[dict] = []
    for index, excerpt in enumerate(documents):
        meta = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
        distance = distances[index] if index < len(distances) else None
        items.append(
            {
                "title": meta.get("title") or meta.get("document_id") or "",
                "document_id": meta.get("document_id"),
                "excerpt": (excerpt or "")[:400],
                "score": None if distance is None else round(1 - float(distance), 4),
            }
        )
    return items


def _query(vector: list[float], k: int, product_ids: list[str] | None, topic: str | None) -> dict:
    payload = {
        "query_embeddings": [vector],
        "n_results": k,
        "include": ["documents", "metadatas", "distances"],
    }
    where = _where(product_ids, topic)
    if where is not None:
        payload["where"] = where
    return payload


def _where(product_ids: list[str] | None, topic: str | None) -> dict | None:
    filters: list[dict] = []
    if product_ids is not None:
        filters.append({"product_id": {"$in": [str(item) for item in product_ids]}})
    if topic:
        filters.append({"topic": topic})
    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}


def _first(value) -> list:
    if not value:
        return []
    head = value[0]
    return list(head or [])


def _default_embed(texts: list[str]) -> list[list[float]]:
    from app.config import Config

    return embed_texts(texts, base_url=Config.OLLAMA_BASE_URL, model=Config.OLLAMA_EMBED_MODEL)


def _default_store(name: str):
    from urllib.parse import urlparse

    from app.config import Config

    parsed = urlparse(Config.CHROMA_URL)
    return open_collection(name, host=parsed.hostname or "localhost", port=parsed.port or 8000)
