# ADR-015: Usage records carry no monetary value

Date: 2026-08-05 · Status: accepted

## Context

Customer support asks why a balance dropped. It would be convenient for a usage
record to state what a session cost.

The specification defines no charge, cost, or balance field on usage records.
Rating happens after a record is written.

## Decision

Usage records carry no monetary value. They state what was consumed. The account
feeds state what it cost and what the balance did.

## Alternatives

**Add a charge amount to usage records.** Rejected — no such field exists in the
specification, so it would be an invented addition, and unlike the account
records there is no gap forcing one.

**Add a remaining balance to usage records.** Rejected — the account records
already carry balance before and after each movement. Duplicating it creates two
sources of truth for one number.

## Consequences

- The usage daily mart carries volumes and time usage, not money. Charged
  amounts come from the account marts.
- Answering a balance question requires reading both feeds, which the two
  endpoints already support.
- What remains on usage records is the evidence that charging occurred: the
  charging profile, the quota reasons that closed each entry, and the
  service-logic markers on calls and messages.
