# ADR-005: Encoding built first, using a compiled module

Date: 2026-08-05 · Status: accepted

## Context

The generator writes binary files and the decoder reads them. Both need an
implementation of the encoding rules. The alternative was to defer binary
encoding and start with a simpler format so the rest of the pipeline could run
sooner.

## Decision

Build the binary encoding first. Per-record encoding and decoding use a library
compiled from an ASN.1 module held in this repository. File framing and the
streaming reader are hand-written.

The module is the same artifact the code runs against, so the specification and
the implementation cannot drift.

## Alternatives

**Start with a simple encoding and swap binary in later.** Rejected — the whole
pipeline would run within days, but the hardest and most distinctive part of the
project would sit unwritten, and probably stay that way.

**Hand-roll the encoder.** Rejected — it would re-implement a published standard
for no gain, and subtle errors in nested lengths or packed digit encodings are
easy to introduce and hard to detect.

## Consequences

- The grammar must actually compile, which converts unresolved type definitions
  from a documentation task into build errors.
- The memory bound comes from the per-record length in the record header, not
  from the encoding internals, so using a library does not weaken it.
- Nothing downstream can be built until records encode and decode, which is a
  deliberate ordering.
