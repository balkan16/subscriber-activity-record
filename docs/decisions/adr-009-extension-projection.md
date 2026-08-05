# ADR-009: Extensions are projected, not discarded

Date: 2026-08-05 · Status: accepted

## Context

Records carry an extension list — a set of identifier and payload pairs — so
that fields can be added without changing the grammar. Extensions the platform
does not recognise will appear, because the mechanism exists precisely for
fields introduced later.

## Decision

Extensions the platform consumes are resolved into typed columns. The remainder
is retained in a single flexible column, keyed by identifier, and counted.

## Alternatives

**Drop unrecognized extensions.** Rejected — when a field later turns out to
matter, the history is unrecoverable. The records existed; the data was thrown
away at ingestion.

**Retain everything and project nothing.** Rejected — fields the platform reads
constantly would sit inside a map, which is slow to query and awkward to type.

## Consequences

- A new extension can be promoted to a typed column and backfilled from history.
- Unrecognized identifiers are visible as a metric, so their appearance is
  noticed rather than silently accumulating.
- An extension marked as significant that the platform does not recognise is a
  quarantine condition, since the record has declared that ignoring it would be
  wrong.
