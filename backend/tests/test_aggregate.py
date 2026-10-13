"""Given events → When → Then על Aggregate, בלי מסד נתונים."""

from datetime import UTC
from decimal import Decimal
from uuid import uuid4

import pytest
from goalvest_core import AggregateRoot, BusinessRuleViolation, Event


class Wallet(AggregateRoot):
    aggregate_type = "Wallet"

    def __init__(self, aggregate_id=None) -> None:
        super().__init__(aggregate_id)
        self.balance = Decimal(0)
        self.is_open = False

    def open_account(self) -> None:
        if self.is_open:
            raise BusinessRuleViolation("החשבון כבר פתוח")
        self._record("AccountOpened", {})

    def deposit(self, amount: Decimal) -> None:
        if not self.is_open:
            raise BusinessRuleViolation("אי אפשר להפקיד לחשבון סגור")
        if amount <= 0:
            raise BusinessRuleViolation("סכום ההפקדה חייב להיות חיובי")
        self._record("MoneyDeposited", {"amount": amount})

    def _when(self, event: Event) -> None:
        if event.event_type == "AccountOpened":
            self.is_open = True
        elif event.event_type == "MoneyDeposited":
            self.balance += event.payload["amount"]
        else:
            raise NotImplementedError(event.event_type)


def _opened(aggregate_id) -> Event:
    return Event(
        event_id=uuid4(),
        aggregate_id=aggregate_id,
        version=1,
        event_type="AccountOpened",
        aggregate_type="Wallet",
        payload={},
    )


def test_given_opened_account_when_deposit_then_balance_and_new_event():
    aggregate_id = uuid4()
    wallet = Wallet.from_events([_opened(aggregate_id)])

    assert wallet.version == 1
    assert wallet.uncommitted_events == ()

    wallet.deposit(Decimal("10.50"))

    assert wallet.balance == Decimal("10.50")
    assert wallet.version == 2
    recorded = wallet.uncommitted_events
    assert len(recorded) == 1
    assert recorded[0].event_type == "MoneyDeposited"
    assert recorded[0].version == 2
    assert recorded[0].aggregate_id == aggregate_id
    assert recorded[0].payload["amount"] == Decimal("10.50")
    assert recorded[0].occurred_at.tzinfo is UTC


def test_given_opened_account_when_deposit_is_not_positive_then_no_event():
    wallet = Wallet.from_events([_opened(uuid4())])

    with pytest.raises(BusinessRuleViolation):
        wallet.deposit(Decimal(0))

    assert wallet.balance == Decimal(0)
    assert wallet.version == 1
    assert wallet.uncommitted_events == ()
