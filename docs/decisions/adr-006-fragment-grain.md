# ADR-006: Fragment-grain ingestion

Date: 2026-08-05 · Status: accepted

## Context

A long session is not emitted as one record. The charging system closes a record
whenever a limit is reached — volume, time, or a change in charging conditions —
and opens another. One session therefore arrives as several records over time.

Sessions may run for hours. The activity view has a thirty-minute freshness
requirement.

## Decision

Ingestion stores one row per record and does not reassemble sessions. Identity
and correlation fields are carried through, so a consumer can group records into
sessions if it wants to.

## Alternatives

**Reassemble sessions during ingestion.** Rejected — a session cannot be
assembled until it closes, which is unbounded. A session still running would be
invisible, which is the opposite of what customer support needs.

**Store fragments but expose only completed sessions.** Rejected — the same
latency problem moved one layer later.

## Consequences

- Nothing blocks on a record that may never arrive.
- Consumers must not read one row as one session. Row counts are not session
  counts.
- A missing fragment is detectable through a gap in the record sequence number,
  so an incomplete total can be flagged rather than being silently wrong.
- Fragmentation is intended behaviour of online charging, not a defect. Nothing
  in the pipeline tries to repair it.
