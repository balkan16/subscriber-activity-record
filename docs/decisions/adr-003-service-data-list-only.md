# ADR-003: One service list, not two

Date: 2026-08-05 · Status: accepted

## Context

A packet gateway record can carry two parallel lists. One holds an entry per
rating group, describing what was consumed of each service. The other holds an
entry per bearer-level charging condition, carrying access technology and
location. Both are optional.

They describe the same traffic sliced two different ways, and they do not
cross-reference each other.

## Decision

Populate the service data list only. The traffic volume list is not emitted.

Because service data entries carry no access technology field, the simulated
node is configured to close the record when access technology changes. The
record-level value then applies unambiguously to every entry the record
contains.

## Alternatives

**Carry both lists.** Rejected on two grounds. Their volumes are two views of
the same traffic, so summing across both double-counts. And because they never
cross-reference, access technology and rating group can never appear on the same
row — "video traffic on 4G" would be unanswerable.

**Carry the traffic volume list only.** Rejected — it has no rating group
dimension at all, which is the breakdown the daily marts need.

## Consequences

- Every row carries both its service and its access technology.
- Access technology changes are visible across a session as separate records,
  not within a single record.
- Closing on access-technology change is a configuration assumption the
  specification permits. It is documented as an assumption, not presented as a
  requirement.
