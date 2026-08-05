# ADR-011: Serving reads the detail layer

Date: 2026-08-05 · Status: accepted

## Context

The history endpoints return rows at the grain they are stored in. That grain
exists in the enriched detail layer. The aggregate layer holds daily summaries
for analytical use.

## Decision

The endpoints read the detail layer directly. The aggregate layer is analytical
only and is never on the serving path.

The detail layer is partitioned by event date, so a rolling twenty-four hour
lookup touches one or two partitions.

## Alternatives

**Serve from the aggregate layer.** Rejected — it holds daily summaries, which
is the wrong grain, and building a serving view there would put two different
purposes in one layer.

**Copy the serving window into a separate indexed store.** Rejected — it was
proposed without a requirement behind it. It adds a second copy, a second thing
to keep fresh, and additional staleness, to solve a latency problem that has not
been measured.

## Consequences

- One fewer component, and no copy that can fall behind.
- Query latency depends on partitioning working as intended, which is measured
  across scale rather than assumed.
- If measurement shows the latency is unacceptable, a serving store is a small
  addition rather than a rewrite.
