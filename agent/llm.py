"""סינתזה מקומית ב-Ollama. כשל חיבור הוא שגיאת תשתית."""

from agent.errors import InfrastructureError, as_infrastructure


def ollama_text(prompt: str, *, model: str, base_url: str) -> str:
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:
        raise InfrastructureError("Ollama", "חבילת המודל לא מותקנת") from exc
    try:
        message = ChatOllama(model=model, temperature=0.1, base_url=base_url).invoke(prompt)
    except Exception as exc:
        infra = as_infrastructure(exc, "Ollama")
        if infra is not None:
            raise infra from exc
        raise
    content = getattr(message, "content", message)
    return content if isinstance(content, str) else str(content)
