import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asn1tools
import pytest

from datagen.ledger import Ledger, PACKAGES

WIB = timezone(timedelta(hours=7))
T0 = datetime(2026, 8, 5, 9, 0, 0, tzinfo=WIB)
MSISDN = '628111631604'
SPEC = asn1tools.compile_files([str(Path(__file__).parent.parent / 'docs' / 'cdr-format.asn')])


@pytest.fixture
def ledger():
    return Ledger(['OCS-JKT-01', 'OCS-SBY-01'], rng=random.Random(42))


def amount(record, field):
    return record[1][field]['valueDigits']


def test_top_up_raises_balance(ledger):
    ledger.open_account(MSISDN, T0)
    entry = ledger.top_up(MSISDN, T0, amount=25000)
    assert amount(entry, 'balanceAfter') - amount(entry, 'balanceBefore') == 25000
    assert ledger.balance(MSISDN) == 25000


def test_purchase_refused_without_funds(ledger):
    ledger.open_account(MSISDN, T0)
    assert ledger.buy_package(MSISDN, T0, 'data_monthly_10gb') is None
    assert ledger.balance(MSISDN) == 0


def test_purchase_debits_price(ledger):
    ledger.open_account(MSISDN, T0, opening_balance=60000)
    entry = ledger.buy_package(MSISDN, T0, 'data_monthly_10gb')
    assert ledger.balance(MSISDN) == 60000 - PACKAGES['data_monthly_10gb']
    assert entry[1]['requestedAction'] == 'directDebiting'


def test_barred_account_cannot_purchase(ledger):
    ledger.open_account(MSISDN, T0, opening_balance=60000)
    ledger.bar(MSISDN, T0)
    assert ledger.buy_package(MSISDN, T0) is None


def test_balance_chains_across_both_feeds(ledger):
    entries = [ledger.open_account(MSISDN, T0)]
    t = T0
    for _ in range(50):
        t += timedelta(minutes=17)
        step = ledger.rng.choice(['top_up', 'buy', 'bar', 'unbar', 'class'])
        if step == 'top_up':
            entries.append(ledger.top_up(MSISDN, t))
        elif step == 'buy':
            entry = ledger.buy_package(MSISDN, t)
            if entry:
                entries.append(entry)
        elif step == 'bar':
            entries.append(ledger.bar(MSISDN, t))
        elif step == 'unbar':
            entries.append(ledger.unbar(MSISDN, t))
        else:
            entries.append(ledger.change_class(MSISDN, t))
    entries.append(ledger.expire(MSISDN, t + timedelta(days=1)))
    for prev, curr in zip(entries, entries[1:]):
        assert amount(prev, 'balanceAfter') == amount(curr, 'balanceBefore')
    assert ledger.balance(MSISDN) == 0


def test_transaction_ids_unique_per_node(ledger):
    ledger.open_account(MSISDN, T0, opening_balance=10**7)
    keys = set()
    for _ in range(200):
        record = ledger.top_up(MSISDN, T0)[1]
        keys.add((record['originNode'], record['transactionId']))
    assert len(keys) == 200


def test_optional_fields_sometimes_omitted(ledger):
    ledger.open_account(MSISDN, T0)
    records = [ledger.top_up(MSISDN, T0)[1] for _ in range(200)]
    with_channel = sum('refillChannel' in r for r in records)
    assert 0 < with_channel < 200


def test_records_encode_and_round_trip(ledger):
    lifecycle = [ledger.open_account(MSISDN, T0, opening_balance=60000)]
    txn = [ledger.top_up(MSISDN, T0), ledger.buy_package(MSISDN, T0)]
    lifecycle += [ledger.bar(MSISDN, T0), ledger.change_class(MSISDN, T0), ledger.expire(MSISDN, T0)]
    for entry in txn:
        assert SPEC.decode('AccountTxnRecord', SPEC.encode('AccountTxnRecord', entry))[0] == 'transaction'
    for entry in lifecycle:
        assert SPEC.decode('AccountLifecycleEntry', SPEC.encode('AccountLifecycleEntry', entry))[0] == 'lifecycle'
