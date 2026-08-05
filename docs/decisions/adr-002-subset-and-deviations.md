# ADR-002: Subset and deviations

Date: 2026-08-05 · Status: accepted

## Context

Specification records are large — a mobile-originated call record carries around
fifty fields, a packet gateway record around seventy. Most are optional and
describe network detail this platform never reads.

## Decision

Implement a subset. Every field the specification marks mandatory is retained;
everything omitted is optional.

Deviations, all documented in the format specification:

- Parameterized types are not used. Bounded string types are replaced with
  plain equivalents; encoded bytes are unaffected.
- Types imported from non-charging specifications are replaced with minimal
  local equivalents, each commented with its origin.
- Composite types outside the platform's scope are simplified to their
  underlying carriers.
- Three fields the specification marks optional are declared mandatory, because
  ingestion depends on them.

## Alternatives

**Implement the full records.** Rejected — a naive copy pulls in roughly 174
type definitions covering trunk groups, radio channel parameters, and
jurisdiction information, none of which the platform reads.

**Omit mandatory fields too.** Rejected — the resulting records could not be
described as conformant, which is the property the format specification exists
to provide.

## Consequences

- Every deviation is stated, so the claim is checkable rather than asserted.
- Tightening optional fields to mandatory is safe in one direction only: the
  platform emits its own data, so it can guarantee presence.
- A record from a real network would still decode, since unknown fields are
  simply absent from the grammar.
