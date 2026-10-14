"""הטמעת מסמכי הידע מ-seed/knowledge אל collection knowledge_base."""

import argparse
import logging
from pathlib import Path

from app.config import Config

from worker.chunking import split_text
from worker.embeddings import embed_texts
from worker.rag import open_collection

logger = logging.getLogger(__name__)


def index_knowledge(directory: Path, collection, embedder) -> int:
    count = 0
    for path in sorted(directory.glob("*.md")):
        meta, body = _front_matter(path.read_text(encoding="utf-8"))
        chunks = split_text(body)
        if not chunks:
            continue
        document_id = path.stem
        title = meta.get("title") or document_id
        collection.upsert(
            ids=[f"{document_id}:{index}" for index in range(len(chunks))],
            embeddings=embedder(chunks),
            documents=chunks,
            metadatas=[
                {
                    "document_id": document_id,
                    "title": title,
                    "topic": meta.get("topic", ""),
                    "source_url": meta.get("source_url", ""),
                    "valid_from": meta.get("valid_from", ""),
                    "chunk_index": index,
                }
                for index in range(len(chunks))
            ],
        )
        count += 1
    return count


def _front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        key, separator, value = line.partition(":")
        if separator:
            meta[key.strip()] = value.strip()
    return meta, parts[2].strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="הטמעת מאגר הידע")
    parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from urllib.parse import urlparse

    parsed = urlparse(Config.CHROMA_URL)
    directory = Path(__file__).resolve().parents[1] / "seed" / "knowledge"
    collection = open_collection("knowledge_base", host=parsed.hostname or "localhost", port=parsed.port or 8000)

    def embed(texts: list[str]) -> list[list[float]]:
        return embed_texts(texts, base_url=Config.OLLAMA_BASE_URL, model=Config.OLLAMA_EMBED_MODEL)

    count = index_knowledge(directory, collection, embed)
    logger.info("הוטמעו %s מסמכי ידע", count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
