# ADR-007: Container grain in silver

Date: 2026-08-05 · Status: accepted

## Context

A data record carries one or more service data entries, one per quota bucket
under one set of charging conditions. Entries within a record can differ in
rating group, and a record can span more than one set of conditions.

## Decision

Silver explodes service data entries into one row each. A row is one charged
unit: a service data entry for data, a whole record for calls and messages.

Row identity is the node, its local sequence number, and the entry's position
within the record.

## Alternatives

**Aggregate entries to one row per record.** Rejected — it would require an
invented rule for which rating group represents the row, and would destroy the
service breakdown the daily marts are built on.

**Keep entries nested in a structured column.** Rejected — every query would
have to unpack the column, and the serving path returns rows at the grain they
are stored in.

## Consequences

- Additive measures are entry-level: volumes, time usage. Record-level fields
  repeat across the rows of one record and must never be summed.
- Three grains coexist and are named: entry, record, session.
- Calls and messages carry no entries and contribute one row each, so the fact
  grain is uniform across services.
