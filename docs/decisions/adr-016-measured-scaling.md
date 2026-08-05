# ADR-016: Scaling is demonstrated by measurement

Date: 2026-08-05 · Status: accepted

## Context

A data platform should show that its design holds under load. Matching an
operator's absolute volumes is not possible on free-tier or local
infrastructure, and attempting it produces a system that cannot be demonstrated.

## Decision

Run a base configuration, then repeat at multiples of it. At each level record
throughput, decoder peak memory, batch duration, event-to-queryable latency, and
query latency.

The evidence is the shape of those curves: memory flat, time linear, and the
point where batch duration exceeds the poll cadence.

## Alternatives

**Report a single large volume figure.** Rejected — one number says nothing
about behaviour, and cannot be reproduced by a reader.

**Match operator-scale volumes.** Rejected — not runnable on the target
infrastructure, and absolute figures matching a particular operator would be
inappropriate for synthetic data in any case.

## Consequences

- The generator takes a scale multiplier as a first-class parameter, and nothing
  in it may accumulate in memory proportional to scale.
- The decoder's memory ceiling is asserted by test, not observed once.
- Finding the point where the design degrades is a result, not a failure. A
  system with no known limit has not been measured.
