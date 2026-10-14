"""הרצת הערכה: איסוף ראיות, Deep Agent או שרשרת, ואז ולידציה. ראו docs/09 §9.4–9.6."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from agent.baseline import build_baseline
from agent.errors import FormatError, InfrastructureError
from agent.privacy import assert_public, market_queries, sensitive_terms
from agent.schema import parse_model_output
from agent.suitability import Suitability, evaluate, load_rules
from agent.validate import finalize, problems

_RAG = (
    ("תנאי נזילות ומיסוי לשוק ההון, קרן השתלמות וגמל להשקעה", "knowledge_base"),
    ("כללי מס על משיכה מקרן השתלמות ומגמל להשקעה", "knowledge_base"),
    ("תנאי פוליסה, נזילות ודמי ניהול", "policy_documents"),
)


@dataclass
class Services:
    mode: str
    model_name: str
    load_products: Callable[[dict], list[dict]]
    search_knowledge: Callable[[str, str], list[dict]]
    search_web: Callable[[str], list[dict]]
    run_tools: Callable[[dict, list[dict]], dict]
    synthesize: Callable[[str], str]
    rules: dict
    tax_rules: dict
    deep_run: Callable[[str], str] | None = None
    bonus: int = 15


@dataclass
class Trace:
    rules: list[dict] = field(default_factory=list)
    rag: list[dict] = field(default_factory=list)
    products: list[dict] = field(default_factory=list)
    tools: dict = field(default_factory=dict)
    web: list[dict] = field(default_factory=list)
    mode: str = ""
    notes: list[str] = field(default_factory=list)
    duration_ms: int = 0
    error: str = ""


@dataclass
class Outcome:
    ok: bool
    payload: dict | None = None
    error_code: str = ""
    message: str = ""
    trace: Trace | None = None


def run_assessment(
    snapshot: dict,
    services: Services,
    *,
    today: date,
    report: Callable[[str, object], None] | None = None,
) -> Outcome:
    started = time.perf_counter()
    trace = Trace(mode=services.mode)
    try:
        suitability = evaluate(snapshot, today=today, rules=services.rules, tax_rules=services.tax_rules)
    except (KeyError, TypeError, ValueError) as exc:
        return _failed(trace, started, "INVALID_SNAPSHOT", str(exc))
    trace.rules = list(suitability.flags)
    _emit(report, "rules", trace.rules)
    try:
        _collect(snapshot, services, trace, report)
        payload = _synthesize(snapshot, services, suitability, trace, started)
    except InfrastructureError:
        trace.duration_ms = _elapsed(started)
        raise
    except ValueError as exc:
        return _failed(trace, started, _code(exc), str(exc))
    trace.duration_ms = _elapsed(started)
    payload["duration_ms"] = trace.duration_ms
    _emit(report, "result", payload)
    return Outcome(True, payload=payload, trace=trace)


def _collect(snapshot: dict, services: Services, trace: Trace, report) -> None:
    banned = sensitive_terms(snapshot)
    trace.rag = _search_rag(services, banned)
    trace.products = services.load_products(snapshot)
    trace.tools = services.run_tools(snapshot, trace.products)
    trace.web = _search_web(services, trace.products, banned)
    _emit(report, "rag", trace.rag)
    _emit(report, "products", trace.products)
    _emit(report, "tools", trace.tools)
    _emit(report, "web", trace.web)
    if not trace.products:
        raise ValueError("אין מוצר מועמד")
    if not trace.rag or not trace.web:
        raise ValueError("חסר מקור מהמאגר או מהרשת")


def _synthesize(snapshot, services: Services, suitability: Suitability, trace: Trace, started: float) -> dict:
    prompt = _prompt(snapshot, suitability, trace)
    candidate_ids = {item["product_id"] for item in trace.products}
    if services.mode == "deep" and services.deep_run is not None:
        try:
            parsed = _attempts(services.deep_run, prompt, suitability, candidate_ids)
            trace.notes.append("deep")
            return finalize(parsed, suitability, model=services.model_name, duration_ms=_elapsed(started))
        except InfrastructureError:
            raise
        except FormatError as exc:
            trace.notes.append(f"fallback-chain:{exc}")
            trace.mode = "chain"
    try:
        parsed = _attempts(services.synthesize, prompt, suitability, candidate_ids)
        trace.notes.append("chain")
        return finalize(parsed, suitability, model=services.model_name, duration_ms=_elapsed(started))
    except InfrastructureError:
        raise
    except FormatError as exc:
        trace.notes.append(f"chain-format:{exc}")
    built = build_baseline(suitability, trace.products, trace.rag, trace.web, services.bonus)
    found = problems(built, suitability, candidate_ids)
    if found:
        raise ValueError("; ".join(found))
    trace.notes.append("baseline")
    return finalize(built, suitability, model=services.model_name, duration_ms=_elapsed(started))


def _attempts(call: Callable[[str], str], prompt: str, suitability: Suitability, candidate_ids: set[str]):
    error = ""
    last = "פורמט לא תקין"
    for _ in range(2):
        try:
            text = call(prompt if not error else prompt + "\nתקן לפי השגיאה: " + error)
            parsed = parse_model_output(text)
        except InfrastructureError:
            raise
        except Exception as exc:  # noqa: BLE001 – שגיאת מודל לא מוכרת נספרת ככשל פורמט
            infra = _infra(exc)
            if infra is not None:
                raise infra
            last = str(exc)
            error = last
            continue
        found = problems(parsed, suitability, candidate_ids)
        if not found:
            return parsed
        last = "; ".join(found)
        error = last
    raise FormatError(last)


def _infra(exc: Exception) -> InfrastructureError | None:
    from agent.errors import as_infrastructure

    if isinstance(exc, InfrastructureError):
        return exc
    return as_infrastructure(exc, "Ollama")


def _search_rag(services: Services, banned: list[str]) -> list[dict]:
    found: list[dict] = []
    for query, collection in _RAG:
        assert_public(query, banned)
        for hit in services.search_knowledge(query, collection):
            item = dict(hit)
            item["collection"] = collection
            found.append(item)
    return found


def _search_web(services: Services, products: list[dict], banned: list[str]) -> list[dict]:
    found: list[dict] = []
    for query in market_queries(products):
        assert_public(query, banned)
        found.extend(services.search_web(query))
    return found


def _prompt(snapshot: dict, suitability: Suitability, trace: Trace) -> str:
    goal = snapshot.get("goal") or {}
    risk = snapshot.get("risk") or {}
    return (
        "סנתז הערכת התאמה בעברית זהירה. אל תסתור את החוקים. החזר JSON בלבד, בלי overall_score.\n"
        f"סוג יעד: {goal.get('type')}. פרופיל: {risk.get('label')}.\n"
        f"חוקים: {list(suitability.flags)}\n"
        f"מוצרים מועמדים: {trace.products}\n"
        f"מקורות מאגר: {trace.rag[:4]}\n"
        f"כלים: {trace.tools}\n"
        f"מקורות רשת: {trace.web[:4]}\n"
        "המלץ רק על product_id מהרשימה. sources חייבים לכלול rag ו-web מהרשימות. "
        "rationale באורך 200 תווים לפחות. אסור: קנה, מומלץ בוודאות, תשואה מובטחת."
    )


def _failed(trace: Trace, started: float, code: str, message: str) -> Outcome:
    trace.error = message
    trace.duration_ms = _elapsed(started)
    return Outcome(False, error_code=code, message=message, trace=trace)


def _code(exc: ValueError) -> str:
    text = str(exc)
    if "מוצר" in text and "מקור" not in text:
        return "NO_CANDIDATES"
    return "MISSING_SOURCES"


def _emit(report, step: str, data: object) -> None:
    if report is not None:
        report(step, data)


def _elapsed(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def default_rules() -> tuple[dict, dict]:
    from mcp_tools.tax import load_tax_rules

    return load_rules(), load_tax_rules()
