"""סכמת פלט ההערכה. הציון הכללי וההבהרה נקבעים בקוד. ראו docs/09 §9.8–9.9."""

import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

DISCLAIMER = "ההערכה נוצרה אוטומטית ואינה מהווה ייעוץ השקעות."
CHANNELS = ("capital_market", "hishtalmut", "gemel_policy")
BANNED_PHRASES = ("קנה", "מומלץ בוודאות", "תשואה מובטחת")


class ChannelScores(BaseModel):
    capital_market: int = Field(ge=0, le=100)
    hishtalmut: int = Field(ge=0, le=100)
    gemel_policy: int = Field(ge=0, le=100)


class Allocation(BaseModel):
    capital_market: int = Field(ge=0, le=100)
    hishtalmut: int = Field(ge=0, le=100)
    gemel_policy: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def totals_100(self) -> "Allocation":
        if self.capital_market + self.hishtalmut + self.gemel_policy != 100:
            raise ValueError("סכום התמהיל חייב להיות 100")
        return self


class RecommendedProduct(BaseModel):
    product_id: UUID
    fit_score: int = Field(ge=0, le=100)
    reason: str = Field(max_length=300)


class Source(BaseModel):
    type: Literal["rag", "web", "tool"]
    title: str
    document_id: UUID | None = None
    url: str | None = None
    excerpt: str | None = Field(default=None, max_length=400)

    @field_validator("url")
    @classmethod
    def http_url(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not value.startswith(("http://", "https://")):
            raise ValueError("כתובת המקור אינה תקינה")
        return value


class RiskFlag(BaseModel):
    code: str
    severity: Literal["high", "medium", "info"]
    text: str


class ModelAssessment(BaseModel):
    model_config = {"extra": "ignore"}

    channel_scores: ChannelScores
    allocation: Allocation
    recommended_products: list[RecommendedProduct] = Field(min_length=1, max_length=5)
    rationale: str = Field(min_length=200, max_length=3000)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    sources: list[Source] = Field(min_length=2)


def parse_model_output(text: str) -> ModelAssessment:
    raw = _json_object(text)
    return ModelAssessment.model_validate(raw)


def _json_object(text: str) -> dict:
    stripped = text.strip()
    if "```" in stripped:
        body = stripped.split("```", 2)[1]
        if body.lstrip().startswith("json"):
            body = body.lstrip()[4:]
        stripped = body
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("הפלט אינו JSON")
    loaded = json.loads(stripped[start : end + 1])
    if not isinstance(loaded, dict):
        raise ValueError("הפלט אינו אובייקט")  # noqa: TRY004 – כשל פענוח פלט, לא טיפוס פייתון
    return loaded
