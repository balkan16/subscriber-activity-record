# ADR-004: Decode outside the distributed engine

Date: 2026-08-05 · Status: accepted

## Context

Source files are binary-encoded. Decoding a file wholesale expands it in memory
by roughly an order of magnitude, because each field becomes an object.

Distributed executors are the worst place to absorb an unpredictable memory
load: a single oversized file can fail a task, and retries repeat the failure.

## Decision

Decoding is a standalone component outside the processing engine. It parses
records sequentially, using each record's declared length, and emits bounded
batches of columnar output.

The lakehouse input contract is decoded columnar files.

## Alternatives

**Decode inside the engine, as a user-defined function.** Rejected — it places
peak memory in executors, where it is least controllable, and couples decoding
throughput to cluster scheduling.

**Decode the whole file, then write it.** Rejected — memory then scales with
file size rather than staying flat, which removes the property the design
depends on.

## Consequences

- Peak memory is bounded and independent of file size. This is asserted by test,
  not assumed.
- The decoder can be run, profiled, and scaled separately from the pipeline.
- It mirrors the mediation stage of operational telecom architectures, where
  decoding precedes the data platform.
- A decode failure isolates to one record, which is quarantined with a reason
  rather than failing the file.
