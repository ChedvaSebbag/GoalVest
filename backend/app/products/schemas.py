"""סכמות קלט של מוצר. החוקים העסקיים נשארים ב-Aggregate."""

from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _decimal(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError("הערך אינו תקין")  # noqa: TRY004 — ולידציית קלט, לא TypeError של פייתון
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError("הערך אינו תקין") from exc


class ProductBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_type: str = Field(alias="type")
    name: str
    track: str
    symbol: str | None = None
    fee_deposit: Decimal = Field(alias="feeDeposit")
    fee_assets: Decimal = Field(alias="feeAssets")
    return_1y: Decimal = Field(alias="return1y")
    return_3y: Decimal = Field(alias="return3y")
    return_5y: Decimal = Field(alias="return5y")
    std_dev: Decimal = Field(alias="stdDev")
    risk_level: int = Field(alias="riskLevel")
    liquidity: str
    liquidity_terms: str = Field(alias="liquidityTerms")
    tax_notes: str = Field(alias="taxNotes")
    min_deposit: Decimal = Field(alias="minDeposit")
    description: str

    @field_validator(
        "fee_deposit", "fee_assets", "return_1y", "return_3y", "return_5y", "std_dev", "min_deposit", mode="before",
    )
    @classmethod
    def money(cls, value: object) -> Decimal:
        return _decimal(value)

    def as_kwargs(self) -> dict:
        return {
            "product_type": self.product_type,
            "name": self.name,
            "track": self.track,
            "symbol": self.symbol,
            "fee_deposit": self.fee_deposit,
            "fee_assets": self.fee_assets,
            "return_1y": self.return_1y,
            "return_3y": self.return_3y,
            "return_5y": self.return_5y,
            "std_dev": self.std_dev,
            "risk_level": self.risk_level,
            "liquidity": self.liquidity,
            "liquidity_terms": self.liquidity_terms,
            "tax_notes": self.tax_notes,
            "min_deposit": self.min_deposit,
            "description": self.description,
        }


class DeactivateBody(BaseModel):
    reason: str = ""
