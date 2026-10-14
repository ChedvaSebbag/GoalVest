"""תשובות שגיאה אחידות. ראו docs/08 §8.1."""

from flask import jsonify
from pydantic import ValidationError


def error_response(status: int, code: str, message: str, fields: dict | None = None):
    return jsonify({
        "error": {"code": code, "message": message, "fields": fields or {}}
    }), status


def validation_response(exc: ValidationError):
    aliases = {
        "full_name": "fullName",
        "institution_id": "institutionId",
        "license_no": "licenseNo",
        "refresh_token": "refreshToken",
        "birth_year": "birthYear",
        "marital_status": "maritalStatus",
        "monthly_income_range": "monthlyIncomeRange",
        "has_emergency_fund": "hasEmergencyFund",
        "existing_products": "existingProducts",
        "drop_reaction": "dropReaction",
        "income_stability": "incomeStability",
        "emergency_fund": "emergencyFund",
        "initial_amount": "initialAmount",
        "monthly_deposit": "monthlyDeposit",
        "target_amount": "targetAmount",
        "target_date": "targetDate",
        "liquidity_need": "liquidityNeed",
        "excluded_channels": "excludedChannels",
        "preferred_channels": "preferredChannels",
        "preferred_institutions": "preferredInstitutions",
        "goal_id": "goalId",
        "consent_share_contact": "consentShareContact",
        "fee_deposit": "feeDeposit",
        "fee_assets": "feeAssets",
        "return_1y": "return1y",
        "return_3y": "return3y",
        "return_5y": "return5y",
        "std_dev": "stdDev",
        "risk_level": "riskLevel",
        "liquidity_terms": "liquidityTerms",
        "tax_notes": "taxNotes",
        "min_deposit": "minDeposit",
        "doc_type": "docType",
    }
    fields: dict[str, str] = {}
    for err in exc.errors():
        loc = err.get("loc") or ()
        key = aliases.get(str(loc[-1]), str(loc[-1])) if loc else "body"
        message = str(err.get("msg", "ערך לא תקין")).removeprefix("Value error, ")
        fields[key] = message
    return error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין", fields)


def rule_response(exc):
    if exc.code == "PROFILE_EXISTS":
        return error_response(409, exc.code, str(exc), exc.fields)
    if exc.code.startswith("INVALID_"):
        return error_response(400, "VALIDATION_ERROR", str(exc), exc.fields)
    return error_response(422, exc.code, str(exc), exc.fields)
