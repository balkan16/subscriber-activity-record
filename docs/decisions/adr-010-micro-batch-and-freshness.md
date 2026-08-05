# ADR-010: Micro-batch processing against a freshness requirement

Date: 2026-08-05 · Status: accepted

## Context

Records must be queryable within thirty minutes of the event occurring. This is
a requirement, not a target, and it is measured from event occurrence — so it
includes time the record spends waiting for its file to close.

Files close on a size ceiling or a maximum open interval, whichever comes first.

## Decision

Processing is micro-batch. The landing area is polled every minute and whatever
has arrived is processed.

Worst case, with a file closing on the timer rather than on size:

    10   file fill (maximum)
     1   transfer
     2   decode
     1   pickup
     2   processing
    ──
    16   minutes

## Alternatives

**Continuous streaming.** Rejected — the file fill wait dominates the budget and
cannot be recovered downstream, so a continuous topology would buy little at
materially higher operational complexity.

**A fixed multi-minute batch interval.** Rejected — it adds up to its own length
in waiting for no benefit, since polling costs almost nothing when there is
nothing to process.

**Arrival-triggered processing.** Deferred — near-zero pickup delay, but an
event-driven component with its own failure modes, and the difference is a
rounding error against a thirty-minute budget.

## Consequences

- The binding case is low traffic, not high: files then close on the timer and
  spend the full interval filling.
- Processing must complete faster than the poll cadence, or lag compounds. This
  is monitored, not assumed.
- Under burst, newest files are processed first so that current activity stays
  within the requirement.
- The figure is measured and published. If the distribution approaches the
  requirement, arrival-triggered processing is the next step.
