import random
from datetime import datetime, timedelta

from datagen.packing import address, timestamp, bits, FLAGS, FLAGS_TOTAL

REFILL_CHANNELS = [
    'retailerPOS', 'modernRetail', 'selfcareApp', 'mobileBanking', 'smsBanking',
    'internetBanking', 'atm', 'eWallet', 'eCommerce', 'physicalVoucher', 'ussd',
]

TOP_UP_AMOUNTS = [5000, 10000, 20000, 25000, 50000, 100000]

PACKAGES = {
    'data_daily_1gb': 5000,
    'data_weekly_3gb': 15000,
    'data_monthly_10gb': 50000,
    'voice_100min': 20000,
    'sms_500': 10000,
}

SERVICE_CLASSES = [100, 200, 300]


def money(amount):
    return {'valueDigits': amount, 'exponent': 0}


class Account:
    def __init__(self, msisdn, account_id, balance, service_class,
                 activated_at, expires_at, flags=None):
        self.msisdn = msisdn
        self.account_id = account_id
        self.balance = balance
        self.service_class = service_class
        self.activated_at = activated_at
        self.expires_at = expires_at
        self.flags = flags if flags is not None else set()


class Ledger:
    def __init__(self, nodes, rng=None, omit_rate=0.2, validity_days=30):
        self.nodes = nodes
        self.rng = rng or random.Random()
        self.omit_rate = omit_rate
        self.validity = timedelta(days=validity_days)
        self.accounts = {}
        self.txn_counter = {node: 0 for node in nodes}
        self.txn_record_number = 0
        self.life_record_number = 0

    def balance(self, msisdn):
        return self.accounts[msisdn].balance

    def _omit(self):
        return self.rng.random() < self.omit_rate

    def _node(self):
        node = self.rng.choice(self.nodes)
        return node, f'{node.lower()}.ocs.local'

    def open_account(self, msisdn, now, opening_balance=0, service_class=None):
        account = Account(
            msisdn=msisdn,
            account_id=f'ACC{msisdn[-10:]}',
            balance=opening_balance,
            service_class=service_class or self.rng.choice(SERVICE_CLASSES),
            activated_at=now,
            expires_at=now + self.validity,
        )
        self.accounts[msisdn] = account
        return self._lifecycle(account, 'activation', now, set(), set(), 0, opening_balance)

    def top_up(self, msisdn, now, amount=None):
        account = self.accounts[msisdn]
        amount = amount or self.rng.choice(TOP_UP_AMOUNTS)
        before = account.balance
        account.balance += amount
        account.expires_at = max(account.expires_at, now + self.validity)
        record = self._transaction(account, now, 'refund', 0, amount, before, account.balance)
        if not self._omit():
            channel = self.rng.choice(REFILL_CHANNELS)
            record['refillChannel'] = channel
            if channel == 'physicalVoucher':
                record['voucherReference'] = f'V{self.rng.randrange(10**11, 10**12)}'
        return ('transaction', record)

    def buy_package(self, msisdn, now, package=None):
        account = self.accounts[msisdn]
        package = package or self.rng.choice(list(PACKAGES))
        price = PACKAGES[package]
        if account.balance < price or account.flags:
            return None
        before = account.balance
        account.balance -= price
        record = self._transaction(account, now, 'directDebiting', 1, price, before, account.balance)
        return ('transaction', record)

    def expire(self, msisdn, now):
        account = self.accounts[msisdn]
        before_flags = set(account.flags)
        before = account.balance
        account.flags.add('expired')
        account.balance = 0
        return self._lifecycle(account, 'expiry', now, before_flags, set(account.flags), before, 0)

    def bar(self, msisdn, now):
        account = self.accounts[msisdn]
        before_flags = set(account.flags)
        account.flags.add('barred')
        return self._lifecycle(account, 'barring', now, before_flags, set(account.flags),
                               account.balance, account.balance)

    def unbar(self, msisdn, now):
        account = self.accounts[msisdn]
        before_flags = set(account.flags)
        account.flags.discard('barred')
        return self._lifecycle(account, 'unbarring', now, before_flags, set(account.flags),
                               account.balance, account.balance)

    def change_class(self, msisdn, now, new_class=None):
        account = self.accounts[msisdn]
        old_class = account.service_class
        choices = [c for c in SERVICE_CLASSES if c != old_class]
        account.service_class = new_class or self.rng.choice(choices)
        entry = self._lifecycle(account, 'classChange', now, set(account.flags), set(account.flags),
                                account.balance, account.balance)
        entry[1]['serviceClassBefore'] = old_class
        entry[1]['serviceClassAfter'] = account.service_class
        return entry

    def _transaction(self, account, now, action, record_type, amount, before, after):
        node, host = self._node()
        self.txn_counter[node] += 1
        self.txn_record_number += 1
        record = {
            'accountRecordType': record_type,
            'recordNumber': self.txn_record_number,
            'originNode': node,
            'originHost': host,
            'transactionId': f'{node}-{self.txn_counter[node]:010d}',
            'eventTimeStamp': timestamp(now),
            'requestedAction': action,
            'transactionAmount': money(amount),
            'accountId': account.account_id,
            'servedMSISDN': address(account.msisdn),
            'serviceClass': account.service_class,
            'balanceBefore': money(before),
            'balanceAfter': money(after),
        }
        if not self._omit():
            record['activationDate'] = timestamp(account.activated_at)
        return record

    def _lifecycle(self, account, event, now, flags_before, flags_after, before, after):
        node, host = self._node()
        self.life_record_number += 1
        record = {
            'recordNumber': self.life_record_number,
            'originNode': node,
            'originHost': host,
            'accountId': account.account_id,
            'servedMSISDN': address(account.msisdn),
            'serviceClass': account.service_class,
            'eventTimeStamp': timestamp(now),
            'lifecycleEvent': event,
            'balanceBefore': money(before),
            'balanceAfter': money(after),
            'accountFlagsBefore': bits(sorted(flags_before), FLAGS, FLAGS_TOTAL),
            'accountFlagsAfter': bits(sorted(flags_after), FLAGS, FLAGS_TOTAL),
        }
        if not self._omit():
            record['activationDate'] = timestamp(account.activated_at)
        if not self._omit():
            record['expiryDate'] = timestamp(account.expires_at)
        return ('lifecycle', record)
