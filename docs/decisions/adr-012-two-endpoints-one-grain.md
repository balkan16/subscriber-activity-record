# ADR-012: Two endpoints, one grain

Date: 2026-08-05 · Status: accepted

## Context

A support channel needs both a subscriber's recent usage and their recent
account activity. These come from separate feeds with separate lineages.

## Decision

Two endpoints — usage history and account history. Both return a flat list of
rows at the grain the rows are stored in, with response shapes typed per
service. No grouping, no totals.

The feeds are never joined in the pipeline. A consumer needing both reads both.

## Alternatives

**A single composed activity endpoint.** Rejected — it would join two
independent lineages inside the platform, and the composition a channel needs
depends on how it presents the data.

**Return session-level groupings and totals.** Rejected — the channel filters
and composes; returning rows keeps the platform's contract simple and the grain
explicit.

## Consequences

- Row counts can be large for an active subscriber. Filtering happens in the
  channel, so pagination is not required.
- Rows carry their correlation identifier, so a consumer can group by session
  without the platform assembling sessions.
- Response shapes differ by service rather than being one shape with unused
  fields.
