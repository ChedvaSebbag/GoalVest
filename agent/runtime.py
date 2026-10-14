"""חיבור השירותים לבקשה אחת: שאילתות, כלים, Tavily ו-LLM."""

import os
from datetime import date

from app.config import Config
from app.queries.candidates import find_candidate_products
from sqlalchemy.orm import Session

from agent.llm import ollama_text
from agent.pipeline import Services, default_rules
from agent.privacy import sensitive_terms
from agent.searching import search_documents
from agent.tools_local import run_market_tools
from agent.web import tavily_search


def build_services(session: Session, snapshot: dict, mode: str, *, today: date | None = None) -> Services:
    rules, tax_rules = default_rules()
    model = Config.OLLAMA_CHAT_MODEL
    base_url = Config.OLLAMA_BASE_URL
    api_key = os.getenv("TAVILY_API_KEY", "")

    def load_products(_snapshot: dict) -> list[dict]:
        goal = _snapshot.get("goal") or {}
        risk = _snapshot.get("risk") or {}
        return find_candidate_products(
            session,
            risk_score=int(risk.get("score") or 3),
            excluded_channels=list(goal.get("excluded_channels") or []),
            liquidity_need=str(goal.get("liquidity_need") or "NONE"),
            minimum=int(rules["candidate_min"]),
            limit=int(rules["candidate_max"]),
        )

    def deep_run(prompt: str) -> str:
        from agent.deep_runner import invoke_deep

        return invoke_deep(
            prompt,
            search=search_documents,
            products=lambda: load_products(snapshot),
            web=lambda query: tavily_search(query, api_key=api_key),
            model_name=model,
            base_url=base_url,
            api_key=api_key,
            banned=sensitive_terms(snapshot),
        )

    return Services(
        mode=mode,
        model_name=model,
        load_products=load_products,
        search_knowledge=search_documents,
        search_web=lambda query: tavily_search(query, api_key=api_key),
        run_tools=lambda current, products: run_market_tools(current, products, today=today),
        synthesize=lambda prompt: ollama_text(prompt, model=model, base_url=base_url),
        rules=rules,
        tax_rules=tax_rules,
        deep_run=deep_run if mode == "deep" else None,
        bonus=int(rules["retirement_bonus"]),
    )
