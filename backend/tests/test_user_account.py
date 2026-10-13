"""UserAccount: נרמול אימייל, מדיניות סיסמה, ושדות חובה לסוכן."""

from uuid import uuid4

import pytest
from goalvest_core import BusinessRuleViolation
from goalvest_core.accounts import UserAccount


def _hash(password: str) -> str:
    return f"hashed:{password}"


def _register(account: UserAccount, **overrides) -> None:
    payload = {
        "email": "Noa@Mail.com",
        "full_name": "נועה לוי",
        "phone": "0501234567",
        "password": "Secret12",
        "role": "INVESTOR",
        "hash_password": _hash,
    }
    payload.update(overrides)
    account.register(**payload)


def test_register_normalizes_email_and_records_one_event():
    account = UserAccount()
    _register(account, email="  Noa@Mail.com  ")
    events = account.uncommitted_events
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "UserRegistered"
    assert event.version == 1
    assert event.payload["email"] == "noa@mail.com"
    assert event.payload["password_hash"] == "hashed:Secret12"
    assert account.email == "noa@mail.com"


def test_weak_password_records_nothing():
    account = UserAccount()
    with pytest.raises(BusinessRuleViolation) as caught:
        _register(account, password="short")
    assert caught.value.code == "WEAK_PASSWORD"
    assert account.uncommitted_events == ()


def test_agent_requires_institution_and_license():
    account = UserAccount()
    with pytest.raises(BusinessRuleViolation) as caught:
        _register(account, role="AGENT")
    assert caught.value.code == "AGENT_FIELDS_REQUIRED"
    assert account.version == 0


def test_agent_registration_keeps_license_on_the_event_only():
    account = UserAccount()
    institution_id = uuid4()
    _register(account, role="AGENT", institution_id=institution_id, license_no="  LIC-9  ")
    payload = account.uncommitted_events[0].payload
    assert payload["role"] == "AGENT"
    assert payload["institution_id"] == str(institution_id)
    assert payload["license_no"] == "LIC-9"
