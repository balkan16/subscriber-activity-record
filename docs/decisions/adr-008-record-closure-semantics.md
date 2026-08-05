# ADR-008: Volumes are deltas; closure cause is reference data

Date: 2026-08-05 · Status: accepted

## Context

Interim records could plausibly carry either the volume accrued in their own
interval or a running total for the session. Downstream aggregation differs
entirely between the two.

Separately, whether a record is the last of a session must be determined. The
specification provides no explicit flag; it provides a closure cause with values
whose meanings do not follow from their numeric range.

## Decision

Each record carries the volume accrued during its own interval. A session total
is the sum of its records.

Closure cause values are classified as ending the session or continuing it. The
classification is reference data, maintained alongside the other mapping tables.
Enrichment derives a final-record flag from it.

## Alternatives

**Cumulative volumes.** Rejected — a partial read would look correct while being
incomplete, whereas summing deltas makes a missing record visible as an
undercount.

**An explicit terminal flag in the record.** Rejected — it is fully derivable
from the closure cause, so carrying it would be redundant data and the only
unnecessary original element in an otherwise traceable format.

**Deriving the classification from the numeric range.** Rejected — the
specification states the low range mirrors a different enumeration with no
direct correlation, and at least one value inside that range means the opposite
of its neighbours.

## Consequences

- A gap in the record sequence number marks a session total as known-incomplete.
- The enumeration grows between releases, so an unrecognized value is counted and
  surfaced rather than assumed into a class.
- Completeness remains uncertain regardless: if a session ends abnormally the
  terminal record may never be produced. An ending cause is conclusive; its
  absence is ambiguous, so no consumer may block waiting for one.
