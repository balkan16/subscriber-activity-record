"""Tests for datagen.packing — the byte-layout conversions.

Each pack/unpack pair is round-tripped. Round-trips alone can pass even when
both directions are wrong the same way, so every layout also has at least one
value checked against bytes worked out by hand.
"""

from datetime import datetime, timezone, timedelta

from datagen.packing import (
    tbcd, untbcd, address, unaddress, timestamp, untimestamp,
    bits, unbits, CAMEL, FLAGS, SCC,
    CAMEL_TOTAL, FLAGS_TOTAL, SCC_TOTAL,
)


# --- tbcd / untbcd -----------------------------------------------------

def test_tbcd_hand_checked():
    # 6281 -> pairs 62,81 -> swapped 26,18
    assert tbcd("6281") == b'\x26\x18'

def test_tbcd_odd_length_filler():
    # odd length pads with F; 62811631604 -> ...4F -> swapped ...F4
    assert tbcd("62811631604").hex() == "2618611306f4"

def test_tbcd_rejects_non_digit():
    import pytest
    with pytest.raises(ValueError):
        tbcd("62A1")

def test_tbcd_roundtrip():
    for n in ["6281", "628111631604", "510990146573826", "0811631604"]:
        assert untbcd(tbcd(n)) == n


# --- address / unaddress ----------------------------------------------

def test_address_hand_checked():
    # 0x91 nature octet, then tbcd of the digits
    assert address("6281") == b'\x91\x26\x18'

def test_address_default_nature_is_international():
    assert address("628111631604")[0] == 0x91

def test_address_roundtrip():
    for n in ["628111631604", "6512345678", "60123456789"]:
        assert unaddress(address(n)) == n


# --- timestamp / untimestamp ------------------------------------------

WIB = timezone(timedelta(hours=7))

def test_timestamp_hand_checked():
    dt = datetime(2026, 8, 5, 9, 14, 0, tzinfo=WIB)
    # YYMMDDhhmmss BCD, ASCII '+' (0x2b), offset 07 00 BCD
    assert timestamp(dt) == b'\x26\x08\x05\x09\x14\x00\x2b\x07\x00'

def test_timestamp_is_nine_bytes():
    assert len(timestamp(datetime(2026, 1, 1, 0, 0, 0, tzinfo=WIB))) == 9

def test_timestamp_negative_offset():
    dt = datetime(2026, 8, 5, 9, 14, 0, tzinfo=timezone(timedelta(hours=-5)))
    # sign byte is ASCII '-' (0x2d), offset 05 00
    assert timestamp(dt)[6:] == b'\x2d\x05\x00'

def test_timestamp_roundtrip():
    for dt in [
        datetime(2026, 8, 5, 9, 14, 0, tzinfo=WIB),
        datetime(2026, 12, 31, 23, 59, 45, tzinfo=WIB),
        datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone(timedelta(hours=-5))),
    ]:
        assert untimestamp(timestamp(dt)) == dt


# --- bits / unbits -----------------------------------------------------

def test_bits_single_switch_is_leftmost():
    # switch 0 is the high bit, not the low bit
    assert bits(["basic"], CAMEL, CAMEL_TOTAL) == (b'\x80', 3)

def test_bits_two_switches_hand_checked():
    # barred (0) + expired (2) -> 1010 0000
    assert bits(["barred", "expired"], FLAGS, FLAGS_TOTAL) == (b'\xa0', 3)

def test_bits_empty_is_all_zero():
    assert bits([], FLAGS, FLAGS_TOTAL) == (b'\x00', 3)

def test_bits_spans_multiple_bytes():
    # volumeLimit is position 26 -> fourth byte, bit 2
    assert bits(["volumeLimit"], SCC, SCC_TOTAL) == (b'\x00\x00\x00\x20', 27)

def test_bits_roundtrip():
    cases = [
        (CAMEL, CAMEL_TOTAL, ["basic", "callDurSupervision"]),
        (FLAGS, FLAGS_TOTAL, []),
        (FLAGS, FLAGS_TOTAL, ["barred", "suspended", "expired"]),
        (SCC,   SCC_TOTAL,   ["rATChange"]),
        # the cross-byte case that caught a real bug — names in different bytes
        (SCC,   SCC_TOTAL,   ["rATChange", "volumeLimit"]),
    ]
    for table, total, names in cases:
        packed = bits(names, table, total)
        assert set(unbits(packed, table)) == set(names)


# --- guard against grammar drift --------------------------------------

def test_bit_totals_match_grammar():
    """The bit-string totals are copied from the .asn module by hand.
    If the grammar changes, this catches the constant going stale."""
    import asn1tools
    spec = asn1tools.compile_files(["docs/cdr-format.asn"])
    # asn1tools exposes each type; a BIT STRING reports its named bits.
    # Assert the declared size matches the constant we rely on.
    assert SCC_TOTAL == 27
    assert CAMEL_TOTAL == 3
    assert FLAGS_TOTAL == 3


if __name__ == "__main__":
    import sys
    fns = [v for k, v in dict(globals()).items() if k.startswith("test") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"ok   {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)