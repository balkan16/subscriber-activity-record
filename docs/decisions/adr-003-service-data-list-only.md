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

A service data entry may carry its own access technology — the specification
defines `rATType` on the entry, as an optional field. It is not retained here.
Carrying it would put the same dimension in two places, and an entry-level
value that disagreed with the record-level one would have no defined
resolution.

Access technology is therefore taken from the record. For that to be
unambiguous a record must not span two technologies, so the simulated node is
configured to close the record when access technology changes.

## Alternatives

**Carry both lists.** Rejected on two grounds. Their volumes are two views of
the same traffic, so summing across both double-counts. And because they never
cross-reference, access technology and rating group can never appear on the same
row — "video traffic on 4G" would be unanswerable.

**Carry the traffic volume list only.** Rejected — it has no rating group
dimension at all, which is the breakdown the daily marts need.

**Retain `rATType` on the service data entry.** Rejected — it would allow a
record to span technologies, at the cost of two sources for one dimension and
no rule for reconciling them. Closing the record instead keeps one source.

## Consequences

- Every row carries both its service and its access technology.
- Access technology changes are visible across a session as separate records,
  not within a single record.
- Closing on access-technology change is a configuration assumption the
  specification permits. It is documented as an assumption, not presented as a
  requirement.
- The assumption is load-bearing. Because `rATType` is omitted from the entry,
  a record that did span technologies would attribute all of its entries to
  whichever value the record carried, with nothing in the data to reveal it.
