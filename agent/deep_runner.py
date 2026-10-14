"""Deep Agent עם שני תת-סוכנים. כשל פורמט חוזר לשרשרת. ראו docs/09 §9.6."""

import asyncio
import os
import sys
from collections.abc import Callable

from agent.errors import as_infrastructure
from agent.privacy import assert_public

_SYSTEM = """אתה אנליסט התאמת השקעות במערכת GoalVest. תפקידך להעריך עד כמה כל אפיק
(שוק ההון, קרן השתלמות, קופת גמל להשקעה/פוליסת חיסכון) מתאים ליעד ולפרופיל של המשקיע.
- הסתמך רק על: נתוני הבקשה, תוצאות חוקי ההתאמה, מסמכים מהמאגר, תוצאות כלים ותוצאות חיפוש.
- כל טענה עובדתית על מס, נזילות או דמי ניהול חייבת מקור (rag או web).
- אל תסתור את חוקי ההתאמה שקיבלת.
- המלץ רק על מוצרים מתוך רשימת המועמדים.
- כתוב בעברית פשוטה. אל תשתמש בלשון ציווי ("קנה"), אלא "מתאים יותר", "כדאי לשקול".
- אסור לשלוח לשירות חיפוש שם, אימייל, טלפון או סכום אישי.
- החזר JSON בלבד לפי הסכמה, בלי שדה overall_score."""


def invoke_deep(
    prompt: str,
    *,
    search: Callable[[str, str], list[dict]],
    products: Callable[[], list[dict]],
    web: Callable[[str], list[dict]],
    model_name: str,
    base_url: str,
    api_key: str,
    banned: list[str],
) -> str:
    try:
        from deepagents import create_deep_agent
        from langchain_core.tools import tool
        from langchain_ollama import ChatOllama
    except ImportError as exc:
        raise RuntimeError("חבילת Deep Agent לא מותקנת") from exc
    tools = _local_tools(search, products, web, banned, tool)
    tools.extend(_mcp_tools(api_key, banned))
    model = ChatOllama(model=model_name, temperature=0.1, base_url=base_url)
    agent = create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=_SYSTEM,
        subagents=[
            {
                "name": "market-researcher",
                "description": "חוקר תנאי שוק וחדשות על גופים ומסלולים באינטרנט",
                "system_prompt": "חפש רק מונחים ציבוריים: שם מסלול, שם גוף, ריבית בנק ישראל. בלי סכום או פרט אישי.",
                "tools": _matching(tools, "tavily", "volatility"),
            },
            {
                "name": "policy-analyst",
                "description": "מנתח תנאי פוליסות ומיסוי מתוך מאגר המסמכים",
                "system_prompt": "הסתמך על המאגר ועל מחשבון המס. אל תמציא שיעור מס.",
                "tools": _matching(tools, "search_knowledge", "tax"),
            },
        ],
    )
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            {"recursion_limit": 25},
        )
    except Exception as exc:
        infra = as_infrastructure(exc, "Ollama")
        if infra is not None:
            raise infra from exc
        raise RuntimeError(str(exc)) from exc
    return _text(result)


def _local_tools(search, products, web, banned: list[str], tool):
    @tool
    def search_knowledge_base(query: str, collection: str) -> str:
        """חיפוש במאגר. collection הוא knowledge_base או policy_documents."""
        if collection not in {"knowledge_base", "policy_documents"}:
            return "אוסף לא מותר"
        assert_public(query, banned)
        return _dump(search(query, collection))

    @tool
    def find_candidate_products() -> str:
        """רשימת המוצרים המועמדים להערכה. מותר להמליץ רק מתוכה."""
        return _dump(products())

    @tool
    def tavily_search(query: str) -> str:
        """חיפוש ציבורי ברשת: ריבית, מדדים, שם גוף או שם מסלול. בלי פרטים אישיים."""
        assert_public(query, banned)
        return _dump(web(query))

    return [search_knowledge_base, find_candidate_products, tavily_search]


def _mcp_tools(api_key: str, banned: list[str]) -> list:
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        return []
    servers = {
        "goalvest-tools": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "mcp_tools.server"],
        }
    }
    if api_key:
        servers["tavily"] = {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "tavily-mcp"],
            "env": {**os.environ, "TAVILY_API_KEY": api_key},
        }
    try:
        tools = asyncio.run(MultiServerMCPClient(servers).get_tools())
    except Exception:  # noqa: BLE001 – כשל MCP נופל לשרשרת, לא מפיל את התהליך
        return []
    guarded = []
    for item in tools:
        name = getattr(item, "name", "")
        if "tavily" in name.lower():
            _guard(item, banned)
        guarded.append(item)
    return guarded


def _guard(tool, banned: list[str]) -> None:
    original = tool.invoke

    def invoke(input, config=None, **kwargs):
        assert_public(str(input), banned)
        return original(input, config, **kwargs)

    tool.invoke = invoke


def _matching(tools: list, *parts: str) -> list:
    chosen = [tool for tool in tools if any(part in getattr(tool, "name", "") for part in parts)]
    return chosen or tools[:1]


def _dump(value) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, default=str)


def _text(result) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        structured = result.get("structured_response")
        if structured is not None:
            return _dump(structured if not hasattr(structured, "model_dump") else structured.model_dump(mode="json"))
        messages = result.get("messages") or []
        if messages:
            last = messages[-1]
            content = getattr(last, "content", None)
            if content is None and isinstance(last, dict):
                content = last.get("content")
            if isinstance(content, list):
                return "".join(str(part.get("text", part)) if isinstance(part, dict) else str(part) for part in content)
            return str(content or "")
    return str(result)
