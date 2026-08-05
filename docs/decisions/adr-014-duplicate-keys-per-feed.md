# ADR-014: Duplicate keys differ per feed

Date: 2026-08-05 · Status: accepted

## Context

Ingestion must be idempotent: reprocessing a file leaves table state unchanged.
That requires a key that identifies a record uniquely.

The three feeds carry different identity fields, because they come from
different kinds of source.

## Decision

- Usage records: the node with its local sequence number, plus the entry's
  position within the record.
- Account transactions: the origin node with the transaction identifier.
- Account lifecycle records: the origin node, the account, the event, and the
  event timestamp.

## Alternatives

**One uniform key shape across all feeds.** Rejected — the lifecycle record
carries no transaction identifier and no counter, so a uniform shape would mean
adding fields to a record that has no natural source for them.

**A per-node counter on lifecycle records.** Rejected — it would guarantee
uniqueness and detect gaps, but requires the producing system to maintain a
counter, which the composite avoids.

**Omitting the timestamp from the lifecycle key.** Rejected — accounts are
barred and unbarred repeatedly, so the same account, event, and node recur.
Without the timestamp a genuine event would be discarded as a duplicate.

## Consequences

- Deduplication logic has three shapes rather than one.
- The lifecycle key assumes one account cannot undergo the same event at the
  same node in the same instant. The generator asserts this rather than
  assuming it.
- A node counter is monotonic, so a gap reveals a missing record. That property
  is available for usage records and not for lifecycle records.
