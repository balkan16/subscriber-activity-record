# ADR-001: Standards basis

Date: 2026-07-30 · Status: accepted

## Context

The platform reads CDR files. Two things need defining: what a record
contains, and how records are packaged into a file.

Both need public lineage — a reviewer should be able to trace any field to a
downloadable specification.

## Decision

- **Record content** — 3GPP TS 32.298, a trimmed subset. ASN.1, BER encoded.
- **File packaging** — 3GPP TS 32.297. File header, per-record header, closure
  metadata, naming.

Separate layers: a change to record content does not affect file framing, or
the reverse.

## Alternatives

**TS 32.299 (Diameter).** Rejected — it defines a protocol, not a file format.
The envelope would still have to be invented, including the metadata used to
detect loss.

**An original schema.** Rejected — simpler to build, but nothing traceable to
an external source.

## Consequences

- The grammar covers three record types: data session, voice call, short
  message.
- The file header carries record count, file sequence number, and closure
  reason. These are the data-quality anchors: a count that disagrees with the
  records present, or a gap in sequence numbers, is detectable without reading
  record content.
- The account feeds have no public standard. Their schemas are original and
  marked as such.
- TS 32.298 defines no monetary type; charge amounts use the RFC 4006
  unit-value shape.
- Enumerations differ between releases. A target release is pinned, and
  unrecognized values are surfaced rather than assumed.
- BER decoding of deeply optional structures is the cost of traceability.
