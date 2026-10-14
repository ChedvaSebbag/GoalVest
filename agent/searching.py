"""חיפוש במאגר. כשל של Ollama או Chroma הוא שגיאת תשתית."""

from agent.errors import InfrastructureError, as_infrastructure


def search_documents(query: str, collection: str) -> list[dict]:
    from worker.rag import search_knowledge_base

    try:
        return search_knowledge_base(query, collection, k=4)
    except ValueError:
        raise
    except Exception as exc:
        text = str(exc).lower()
        service = "Ollama" if "embed" in text or "11434" in text else "Chroma"
        infra = as_infrastructure(exc, service)
        raise infra or InfrastructureError(service, str(exc)) from exc
