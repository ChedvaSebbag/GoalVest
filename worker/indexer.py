"""Indexer: קורא ProductDocumentUploaded, מטמיע ב-Chroma, ורושם אירוע עם ה-checkpoint באותה טרנזקציה."""

import argparse
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from app.bootstrap import build_dispatcher
from app.config import Config
from app.infrastructure.db import get_engine
from app.infrastructure.event_store import EventStoreRepository, _to_event
from app.infrastructure.tables import consumer_checkpoints, event_store, rm_products
from app.products.storage import resolve_stored
from goalvest_core import BusinessRuleViolation
from goalvest_core.products import Product
from sqlalchemy.orm import Session

from worker.chunking import split_text
from worker.embeddings import embed_texts
from worker.extract import extract_text
from worker.rag import open_collection

CONSUMER = "document-indexer"
_INTERVAL_SECONDS = 15
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Outcome:
    ok: bool
    chunks: int = 0
    error: str = ""


def run_once(
    session: Session,
    *,
    storage_dir: Path,
    embedder: Callable[[list[str]], list[list[float]]],
    collection,
    model: str,
    commit: Callable[[Session], None] | None = None,
) -> int:
    """מעבד העלאות חדשות. כל מסמך: upsert ל-Chroma, ואז אירוע ו-checkpoint בטרנזקציה אחת."""
    position = _checkpoint(session)
    rows = _pending_uploads(session, position)
    done = 0
    for row in rows:
        upload = _to_event(row)
        outcome = _prepare(session, upload, storage_dir, embedder, collection)
        _record(session, upload, outcome, int(row["global_position"]), model)
        _finish(session, commit)
        done += 1
    return done


def _prepare(session: Session, upload, storage_dir: Path, embedder, collection) -> _Outcome:
    payload = upload.payload
    try:
        path = resolve_stored(storage_dir, payload["storage_path"])
    except BusinessRuleViolation:
        return _Outcome(False, error="הקובץ לא נמצא")
    if not path.is_file():
        return _Outcome(False, error="הקובץ לא נמצא")
    try:
        text = extract_text(path)
    except (OSError, ValueError) as exc:
        return _Outcome(False, error=str(exc) or "חילוץ הטקסט נכשל")
    chunks = split_text(text)
    if not chunks:
        return _Outcome(False, error="נדרש מסמך עם טקסט")
    institution_id = _institution_id(session, upload.aggregate_id)
    if institution_id is None:
        return _Outcome(False, error="המוצר לא נמצא")
    vectors = embedder(chunks)
    document_id = str(payload["document_id"])
    collection.upsert(
        ids=[f"{document_id}:{index}" for index in range(len(chunks))],
        embeddings=vectors,
        documents=chunks,
        metadatas=[
            {
                "product_id": str(upload.aggregate_id),
                "institution_id": str(institution_id),
                "document_id": document_id,
                "chunk_index": index,
                "title": payload["file_name"],
            }
            for index in range(len(chunks))
        ],
    )
    return _Outcome(True, chunks=len(chunks))


def _record(session: Session, upload, outcome: _Outcome, position: int, model: str) -> None:
    repository = EventStoreRepository(session, build_dispatcher())
    product = Product.from_events(repository.load(upload.aggregate_id, Product.aggregate_type))
    previous = product.version
    metadata = {"role": "WORKER", "consumer": CONSUMER}
    document_id = str(upload.payload["document_id"])
    if outcome.ok:
        product.mark_document_indexed(
            document_id=document_id,
            chunks_count=outcome.chunks,
            embedding_model=model,
            metadata=metadata,
        )
    else:
        product.mark_document_index_failed(document_id=document_id, error=outcome.error, metadata=metadata)
    repository.append(product.aggregate_id, previous, product.uncommitted_events)
    _save_checkpoint(session, position)


def _pending_uploads(session: Session, position: int) -> list:
    return (
        session.execute(
            sa.select(event_store)
            .where(event_store.c.event_type == "ProductDocumentUploaded", event_store.c.global_position > position)
            .order_by(event_store.c.global_position.asc())
        )
        .mappings()
        .all()
    )


def _checkpoint(session: Session) -> int:
    row = session.execute(
        sa.select(consumer_checkpoints.c.last_position).where(consumer_checkpoints.c.consumer_name == CONSUMER)
    ).scalar_one_or_none()
    return 0 if row is None else int(row)


def _save_checkpoint(session: Session, position: int) -> None:
    exists = session.execute(
        sa.select(consumer_checkpoints.c.consumer_name).where(consumer_checkpoints.c.consumer_name == CONSUMER)
    ).first()
    if exists is None:
        session.execute(sa.insert(consumer_checkpoints).values(consumer_name=CONSUMER, last_position=position))
        return
    session.execute(
        sa.update(consumer_checkpoints)
        .where(consumer_checkpoints.c.consumer_name == CONSUMER)
        .values(last_position=position)
    )


def _institution_id(session: Session, product_id: UUID) -> UUID | None:
    row = session.execute(
        sa.select(rm_products.c.institution_id).where(rm_products.c.product_id == product_id)
    ).first()
    return None if row is None else row[0]


def _finish(session: Session, commit: Callable[[Session], None] | None) -> None:
    if commit is None:
        session.commit()
        return
    commit(session)


def _collection():
    from urllib.parse import urlparse

    parsed = urlparse(Config.CHROMA_URL)
    return open_collection("policy_documents", host=parsed.hostname or "localhost", port=parsed.port or 8000)


def _embed(texts: list[str]) -> list[list[float]]:
    return embed_texts(texts, base_url=Config.OLLAMA_BASE_URL, model=Config.OLLAMA_EMBED_MODEL)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="הטמעת מסמכי מוצר ב-ChromaDB")
    parser.add_argument("--once", action="store_true", help="הרצה אחת בלי לולאה")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    storage = Path(Config.DOCUMENT_STORAGE_DIR)
    while True:
        try:
            session = Session(get_engine(Config.DB_CONNECTION_STRING))
            try:
                count = run_once(
                    session,
                    storage_dir=storage,
                    embedder=_embed,
                    collection=_collection(),
                    model=Config.OLLAMA_EMBED_MODEL,
                )
            finally:
                session.close()
            logger.info("עובדו %s מסמכים", count)
        except KeyboardInterrupt:
            return 0
        except Exception:
            logger.exception("ההטמעה נכשלה")
            if args.once:
                return 1
        if args.once:
            return 0
        time.sleep(_INTERVAL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
