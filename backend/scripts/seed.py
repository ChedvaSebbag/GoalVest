"""Seed אידמפוטנטי: 25 מוצרים, 3 משקיעים ו-3 סוכנים, רק דרך פקודות.

הרצה מתוך backend:
    python -m scripts.seed
"""

from decimal import Decimal
from uuid import UUID, uuid5

import sqlalchemy as sa
from app.commands.bus import CommandBus
from app.commands.products import CreateProduct
from app.commands.register_user import RegisterUser
from app.infrastructure.tables import rm_users
from app.reference.institutions import INSTITUTIONS
from goalvest_core import EmailAlreadyExists

PASSWORD = "Demo1234"
_NAMESPACE = UUID("a1000000-0000-4000-8000-000000000000")
_TERMS = {
    "HIGH": "אפשר למשוך את הכסף בלי תקופת נעילה מיוחדת, בכפוף לתנאי הגוף.",
    "PARTIAL": "הנזילות חלקית ותלויה בוותק או במועד, לפי תנאי המסלול.",
    "NONE": "הכסף נעול עד תום התקופה המוגדרת בתנאי המסלול.",
}
_TAX = {
    "HISHTALMUT": "כללי המס של קרן השתלמות, כולל ותק ופטור עד תקרה, נקבעים לפי הדין העדכני.",
    "GEMEL_INVESTMENT": "גמל להשקעה ממוסה לפי הדין העדכני, עם הבחנה בין משיכה שוטפת לבין גיל פרישה.",
    "SAVINGS_POLICY": "פוליסת חיסכון ממוסה לפי הדין העדכני ותנאי הפוליסה של הגוף.",
    "STOCK": "רווח ממנייה חייב במס רווחי הון לפי הדין העדכני.",
    "ETF": "רווח מתעודת סל חייב במס רווחי הון לפי הדין העדכני.",
}
_INVESTORS = (
    ("demo.investor1@goalvest.test", "נועה דמו", "0501000001"),
    ("demo.investor2@goalvest.test", "דניאל דמו", "0501000002"),
    ("demo.investor3@goalvest.test", "יעל דמו", "0501000003"),
)
_AGENTS = (
    ("demo.agent.migdal@goalvest.test", "רונית דמו", "0502000001", INSTITUTIONS[0].id, "DEMO-1001"),
    ("demo.agent.harel@goalvest.test", "יואב דמו", "0502000002", INSTITUTIONS[1].id, "DEMO-1002"),
    ("demo.agent.clal@goalvest.test", "מיכל דמו", "0502000003", INSTITUTIONS[2].id, "DEMO-1003"),
)
# kind, name, track, risk, liquidity, fee assets, fee deposit, r1, r3, r5, std, symbol, min deposit
_ROWS = (
    ("HISHTALMUT", "אופק השתלמות כללי", "מסלול כללי", 3, "PARTIAL", "0.80", "0.00", "7.20", "6.10", "5.40", "8.50", "", "0"),
    ("HISHTALMUT", "אופק השתלמות מניות", "מסלול מניות", 5, "PARTIAL", "0.90", "0.00", "11.40", "8.20", "7.10", "14.20", "", "0"),
    ("HISHTALMUT", "נתיב השתלמות אג\"ח", "מסלול אג\"ח", 2, "PARTIAL", "0.45", "0.00", "3.10", "2.80", "2.40", "3.20", "", "0"),
    ("HISHTALMUT", "נתיב השתלמות מחקה", "מחקה S&P 500", 5, "PARTIAL", "0.55", "0.00", "14.80", "11.20", "10.40", "15.10", "", "0"),
    ("HISHTALMUT", "שחר השתלמות שקלי", "מסלול שקלי", 2, "PARTIAL", "0.40", "0.00", "2.60", "2.20", "1.90", "2.40", "", "0"),
    ("HISHTALMUT", "שחר השתלמות חו\"ל", "מסלול מניות חו\"ל", 6, "PARTIAL", "0.95", "0.00", "9.70", "7.40", "6.80", "16.30", "", "0"),
    ("HISHTALMUT", "כרמל השתלמות הלכה", "מסלול הלכה", 4, "PARTIAL", "0.70", "0.00", "6.40", "5.50", "4.90", "9.10", "", "0"),
    ("HISHTALMUT", "כרמל השתלמות מדד", "מסלול S&P 500", 5, "PARTIAL", "0.50", "0.00", "13.90", "10.80", "9.70", "14.60", "", "0"),
    ("GEMEL_INVESTMENT", "גשר גמל להשקעה", "מסלול כללי", 4, "HIGH", "0.75", "0.00", "8.10", "6.70", "5.90", "9.80", "", "100"),
    ("GEMEL_INVESTMENT", "גשר גמל מניות", "מסלול מניות", 6, "HIGH", "0.85", "0.00", "12.20", "9.10", "8.00", "15.40", "", "100"),
    ("GEMEL_INVESTMENT", "ברק גמל להשקעה", "מחקה S&P 500", 5, "HIGH", "0.60", "0.00", "14.20", "11.00", "10.10", "14.90", "", "100"),
    ("GEMEL_INVESTMENT", "ברק גמל אג\"ח", "מסלול אג\"ח", 2, "HIGH", "0.40", "0.00", "2.90", "2.50", "2.10", "3.00", "", "100"),
    ("GEMEL_INVESTMENT", "דקל גמל להשקעה", "מסלול עד 50 אחוז מניות", 4, "HIGH", "0.65", "0.00", "7.80", "6.20", "5.50", "10.20", "", "100"),
    ("SAVINGS_POLICY", "פוליסת חיסכון אור", "מסלול כללי", 3, "PARTIAL", "1.10", "1.20", "6.50", "5.40", "4.80", "7.60", "", "250"),
    ("SAVINGS_POLICY", "פוליסת חיסכון אור מניות", "מסלול מניות", 6, "PARTIAL", "1.25", "1.50", "10.40", "8.10", "7.20", "13.80", "", "250"),
    ("SAVINGS_POLICY", "פוליסת חיסכון נוף", "מסלול S&P 500", 5, "PARTIAL", "0.90", "0.80", "13.60", "10.50", "9.40", "14.20", "", "250"),
    ("SAVINGS_POLICY", "פוליסת חיסכון נוף סולידי", "מסלול אג\"ח ממשלתי", 2, "NONE", "0.70", "0.60", "2.40", "2.10", "1.80", "2.20", "", "250"),
    ("ETF", "SPDR S&P 500", "S&P 500", 5, "HIGH", "0.09", "0.00", "16.20", "12.40", "11.10", "15.80", "SPY", "0"),
    ("ETF", "Invesco QQQ", "נאסד\"ק 100", 6, "HIGH", "0.20", "0.00", "18.40", "14.10", "13.20", "20.50", "QQQ", "0"),
    ("ETF", "iShares Core S&P 500", "S&P 500", 5, "HIGH", "0.03", "0.00", "16.00", "12.20", "11.00", "15.60", "IVV", "0"),
    ("ETF", "iShares MSCI Emerging", "שווקים מתעוררים", 6, "HIGH", "0.70", "0.00", "5.40", "3.20", "4.10", "18.40", "EEM", "0"),
    ("STOCK", "טבע", "תל אביב", 6, "HIGH", "0.00", "0.00", "-4.20", "1.80", "3.40", "28.00", "TEVA.TA", "0"),
    ("STOCK", "אפל", "נאסד\"ק", 5, "HIGH", "0.00", "0.00", "12.50", "15.20", "18.40", "24.10", "AAPL", "0"),
    ("STOCK", "מיקרוסופט", "נאסד\"ק", 5, "HIGH", "0.00", "0.00", "11.80", "14.60", "17.20", "22.40", "MSFT", "0"),
    ("STOCK", "נייס", "תל אביב", 6, "HIGH", "0.00", "0.00", "8.40", "9.10", "10.20", "26.50", "NICE.TA", "0"),
)


def run_seed(session, bus: CommandBus) -> dict:
    investors = [_investor(session, bus, email, name, phone) for email, name, phone in _INVESTORS]
    agents = [_agent(session, bus, *item) for item in _AGENTS]
    for index, row in enumerate(_ROWS, start=1):
        _product(bus, index, row, agents[(index - 1) % len(agents)])
    return {"investors": len(investors), "agents": len(agents), "products": len(_ROWS)}


def main() -> None:
    from app import create_app
    from app.bootstrap import build_command_bus
    from app.infrastructure.db import get_db
    from flask import current_app

    app = create_app()
    with app.app_context():
        session = get_db()
        summary = run_seed(session, build_command_bus(session, current_app.extensions["projections"]))
    print(
        f"משקיעים: {summary['investors']}, סוכנים: {summary['agents']}, "
        f"מוצרים: {summary['products']}. סיסמת הדמו: {PASSWORD}"
    )


def _investor(session, bus: CommandBus, email: str, full_name: str, phone: str) -> UUID:
    return _register(session, bus, RegisterUser(
        command_id=_cid(f"user:{email}"),
        email=email,
        full_name=full_name,
        phone=phone,
        password=PASSWORD,
        role="INVESTOR",
    ))


def _agent(session, bus: CommandBus, email: str, full_name: str, phone: str, institution_id: UUID, license_no: str) -> UUID:
    return _register(session, bus, RegisterUser(
        command_id=_cid(f"user:{email}"),
        email=email,
        full_name=full_name,
        phone=phone,
        password=PASSWORD,
        role="AGENT",
        institution_id=institution_id,
        license_no=license_no,
    ))


def _register(session, bus: CommandBus, command: RegisterUser) -> UUID:
    try:
        return bus.dispatch(command).id
    except EmailAlreadyExists:
        return session.execute(sa.select(rm_users.c.user_id).where(rm_users.c.email == command.email)).scalar_one()


def _product(bus: CommandBus, index: int, row: tuple, actor_id: UUID) -> None:
    kind, name, track, risk, liquidity, fee_assets, fee_deposit, r1, r3, r5, std, symbol, minimum = row
    bus.dispatch(CreateProduct(
        command_id=_cid(f"product:{index}"),
        actor_id=actor_id,
        product_id=_pid(index),
        data={
            "product_type": kind,
            "name": name,
            "track": track,
            "symbol": symbol or None,
            "fee_deposit": Decimal(fee_deposit),
            "fee_assets": Decimal(fee_assets),
            "return_1y": Decimal(r1),
            "return_3y": Decimal(r3),
            "return_5y": Decimal(r5),
            "std_dev": Decimal(std),
            "risk_level": risk,
            "liquidity": liquidity,
            "liquidity_terms": _TERMS[liquidity],
            "tax_notes": _TAX[kind],
            "min_deposit": Decimal(minimum),
            "description": f"{name}. מסלול {track}. הנתונים להמחשה ואינם תחזית.",
        },
    ))


def _cid(key: str) -> UUID:
    return uuid5(_NAMESPACE, key)


def _pid(index: int) -> UUID:
    return UUID(f"b2000000-0000-4000-8000-{index:012d}")


if __name__ == "__main__":
    main()
