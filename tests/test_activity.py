import random
from datetime import datetime, timedelta, timezone

import pytest

from datagen.activity import usage
from datagen.ledger import Ledger
from datagen.session import SessionGenerator

WIB = timezone(timedelta(hours=7))
T0 = datetime(2026, 8, 5, 9, 0, 0, tzinfo=WIB)
MSISDN = '628111631604'
IMSI = '510990146573826'
KINDS = ['data', 'call', 'sms']


@pytest.fixture
def world():
    ledger = Ledger(['OCS-JKT-01'], rng=random.Random(1))
    sessions = SessionGenerator(['PGW-JKT-01'], ['MSC-JKT-01'], rng=random.Random(2))
    ledger.open_account(MSISDN, T0, opening_balance=50000)
    return ledger, sessions


@pytest.mark.parametrize('kind', KINDS)
def test_active_subscriber_gets_usage(world, kind):
    ledger, sessions = world
    assert usage(ledger, sessions, MSISDN, IMSI, T0, kind)


@pytest.mark.parametrize('kind', KINDS)
def test_barred_subscriber_gets_no_usage(world, kind):
    ledger, sessions = world
    ledger.bar(MSISDN, T0)
    assert usage(ledger, sessions, MSISDN, IMSI, T0, kind) == []


@pytest.mark.parametrize('kind', KINDS)
def test_unbarred_subscriber_gets_usage_again(world, kind):
    ledger, sessions = world
    ledger.bar(MSISDN, T0)
    ledger.unbar(MSISDN, T0 + timedelta(hours=1))
    assert usage(ledger, sessions, MSISDN, IMSI, T0 + timedelta(hours=2), kind)


@pytest.mark.parametrize('kind', KINDS)
def test_expired_subscriber_gets_no_usage(world, kind):
    ledger, sessions = world
    ledger.expire(MSISDN, T0)
    assert usage(ledger, sessions, MSISDN, IMSI, T0, kind) == []


def test_top_up_does_not_lift_barring(world):
    ledger, sessions = world
    ledger.bar(MSISDN, T0)
    ledger.top_up(MSISDN, T0, amount=100000)
    assert usage(ledger, sessions, MSISDN, IMSI, T0, 'data') == []


def test_usage_does_not_change_balance(world):
    ledger, sessions = world
    before = ledger.balance(MSISDN)
    for kind in KINDS * 20:
        usage(ledger, sessions, MSISDN, IMSI, T0, kind)
    assert ledger.balance(MSISDN) == before


def test_blocked_window_over_a_day(world):
    ledger, sessions = world
    produced = {}
    for hour in range(24):
        at = T0 + timedelta(hours=hour)
        if hour == 8:
            ledger.bar(MSISDN, at)
        if hour == 16:
            ledger.unbar(MSISDN, at)
        produced[hour] = bool(usage(ledger, sessions, MSISDN, IMSI, at, 'sms'))
    assert all(produced[h] for h in range(0, 8))
    assert not any(produced[h] for h in range(8, 16))
    assert all(produced[h] for h in range(16, 24))


def test_unknown_kind_rejected(world):
    ledger, sessions = world
    with pytest.raises(ValueError):
        usage(ledger, sessions, MSISDN, IMSI, T0, 'fax')
