"""סינתזה מול Ollama אמיתי. לא רץ בברירת המחדל."""

import os
from datetime import date
from uuid import uuid4

import pytest

from agent.llm import ollama_text
from agent.pipeline import Services, run_assessment
from agent.schema import DISCLAIMER
from agent.suitability import load_rules
from mcp_tools.tax import load_tax_rules

TODAY = date(2026, 10, 14)


@pytest.mark.slow
def test_chain_synthesis_with_real_ollama():
    rules = load_rules()
    product = str(uuid4())
    services = Services(
        mode="chain",
        model_name=os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:7b-instruct"),
        load_products=lambda _snapshot: [{
            "product_id": product,
            "name": "גמל כללי",
            "type": "GEMEL_INVESTMENT",
            "channel": "gemel_policy",
            "institution_name": "גוף לדוגמה",
            "track": "כללי",
            "symbol": None,
            "risk_level": 4,
            "liquidity": "HIGH",
            "fee_assets": "0.60",
            "fee_deposit": "0",
        }],
        search_knowledge=lambda _query, _collection: [{
            "title": "כללי מס",
            "document_id": str(uuid4()),
            "excerpt": "תקופת הנעילה של קרן השתלמות.",
        }],
        search_web=lambda _query: [{
            "title": "ריבית בנק ישראל",
            "url": "https://example.com/rate",
            "excerpt": "הריבית הנוכחית.",
        }],
        run_tools=lambda _snapshot, _products: {"tax": [], "volatility": [], "fees": [], "growth": []},
        synthesize=lambda prompt: ollama_text(
            prompt,
            model=os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:7b-instruct"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ),
        rules=rules,
        tax_rules=load_tax_rules(),
        bonus=int(rules["retirement_bonus"]),
    )
    snapshot = {
        "goal": {
            "type": "APARTMENT",
            "title": "דירה",
            "target_date": "2030-10-14",
            "liquidity_need": "NONE",
            "excluded_channels": [],
            "initial_amount": "150000.00",
            "monthly_deposit": "3000.00",
            "target_amount": "400000.00",
        },
        "risk": {
            "score": 3,
            "label": "מאוזן",
            "answers": {"birth_year": 1990, "emergency_fund": "YES", "existing_products": ["NONE"]},
        },
    }
    outcome = run_assessment(snapshot, services, today=TODAY)
    assert outcome.ok
    assert outcome.payload["disclaimer"] == DISCLAIMER
    assert outcome.payload["channel_scores"]["hishtalmut"] <= 40
