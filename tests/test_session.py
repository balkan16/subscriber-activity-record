import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asn1tools
import pytest

from datagen.packing import unbits, untimestamp, SCC
from datagen.session import SessionGenerator, CONTINUES, ENDS

WIB = timezone(timedelta(hours=7))
T0 = datetime(2026, 8, 5, 9, 0, 0, tzinfo=WIB)
MSISDN = '628111631604'
IMSI = '510990146573826'
SPEC = asn1tools.compile_files([str(Path(__file__).parent.parent / 'docs' / 'cdr-format.asn')])


@pytest.fixture
def gen():
    return SessionGenerator(['PGW-JKT-01', 'PGW-SBY-01'], ['MSC-JKT-01'], rng=random.Random(7))


def sessions(gen, n=300):
    out = []
    t = T0
    for _ in range(n):
        records = gen.data_session(MSISDN, IMSI, t)
        out.append(records)
        t += timedelta(hours=1)
    return out


def data_only(records):
    return [r[1] for r in records if r[0] == 'data']


def test_one_charging_id_per_session(gen):
    seen = set()
    for records in sessions(gen):
        ids = {r['chargingID'] for r in data_only(records)}
        assert len(ids) == 1
        assert not ids & seen
        seen |= ids


def test_sequence_numbers_contiguous(gen):
    for records in sessions(gen):
        data = data_only(records)
        if len(data) == 1:
            assert 'recordSequenceNumber' not in data[0]
        else:
            assert [r['recordSequenceNumber'] for r in data] == list(range(1, len(data) + 1))


def test_only_last_record_ends(gen):
    for records in sessions(gen):
        data = data_only(records)
        assert all(r['causeForRecClosing'] in CONTINUES for r in data[:-1])
        assert data[-1]['causeForRecClosing'] in ENDS


def test_session_sizes_mostly_single(gen):
    sizes = [len(data_only(r)) for r in sessions(gen, 1000)]
    assert max(sizes) <= 4
    assert sizes.count(1) > len(sizes) / 2
    assert any(s > 1 for s in sizes)


def test_call_interrupt_pattern(gen):
    found = False
    for records in sessions(gen, 500):
        for i, (alt, rec) in enumerate(records):
            if alt in ('moCall', 'mtCall'):
                found = True
                assert records[i - 1][0] == 'data'
                assert records[i - 1][1]['causeForRecClosing'] == 22
                assert records[i + 1][0] == 'data'
    assert found


def test_records_follow_in_time(gen):
    for records in sessions(gen):
        data = data_only(records)
        for prev, curr in zip(data, data[1:]):
            prev_end = untimestamp(prev['recordOpeningTime']) + timedelta(seconds=prev['duration'])
            assert untimestamp(curr['recordOpeningTime']) >= prev_end


def test_local_sequence_unique_per_node(gen):
    keys = [(r['nodeID'], r['localSequenceNumber'])
            for records in sessions(gen) for r in data_only(records)]
    assert len(keys) == len(set(keys))


def test_container_reason_matches_record(gen):
    expected = {22: 'rATChange', 16: 'volumeLimit', 17: 'timeLimit', 0: 'pDPContextRelease', 4: 'pDPContextRelease'}
    for records in sessions(gen):
        for r in data_only(records):
            for c in r['listOfServiceData']:
                assert expected[r['causeForRecClosing']] in unbits(c['serviceConditionChange'], SCC)
                assert c['timeUsage'] <= r['duration']


def test_optional_fields_sometimes_omitted(gen):
    data = [r for records in sessions(gen) for r in data_only(records)]
    with_imsi = sum('servedIMSI' in r for r in data)
    assert 0 < with_imsi < len(data)


def test_all_record_types_round_trip(gen):
    entries = [e for records in sessions(gen, 50) for e in records]
    entries += [gen.call(MSISDN, IMSI, T0, d) for d in ('mo', 'mt') for _ in range(20)]
    entries += [gen.sms(MSISDN, IMSI, T0, d) for d in ('mo', 'mt') for _ in range(20)]
    kinds = set()
    for entry in entries:
        decoded = SPEC.decode('UsageRecord', SPEC.encode('UsageRecord', entry))
        assert decoded[0] == entry[0]
        kinds.add(entry[0])
    assert kinds == {'data', 'moCall', 'mtCall', 'moSMS', 'mtSMS'}


@pytest.mark.parametrize('direction', ['mo', 'mt'])
def test_call_carries_answer_time(gen, direction):
    alt, record = gen.call(MSISDN, IMSI, T0, direction)
    assert untimestamp(record['answerTime']) == T0
    decoded = SPEC.decode('UsageRecord', SPEC.encode('UsageRecord', (alt, record)))
    assert decoded[1]['answerTime'] == record['answerTime']


def test_interrupting_call_starts_when_data_record_closes(gen):
    found = False
    for records in sessions(gen, 500):
        for i, (alt, rec) in enumerate(records):
            if alt in ('moCall', 'mtCall'):
                found = True
                prev = records[i - 1][1]
                prev_end = untimestamp(prev['recordOpeningTime']) + timedelta(seconds=prev['duration'])
                call_end = untimestamp(rec['answerTime']) + timedelta(seconds=rec['callDuration'])
                assert untimestamp(rec['answerTime']) == prev_end
                assert untimestamp(records[i + 1][1]['recordOpeningTime']) == call_end
    assert found
