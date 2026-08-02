# CLAUDE.md

Project rules for this repository, including AI-assisted work.

## Project

A data platform for a simulated prepaid mobile operator. Three synthetic feeds
— usage, account transactions, account lifecycle — are decoded from ASN.1 BER
files, processed through a medallion lakehouse, and served as two history APIs.
Design: `README.md`, `docs/cdr-format.md`, `docs/decisions/`.

## Code standards

Decode logic, silver transformations, grain handling, data-quality checks, and
API query logic are hand-authored. AI assistance is used for scaffolding,
tests, fixtures, CI, and documentation.

- Small commits, one concern each.
- Tests and linting pass before a commit is proposed.
- Design decisions live in `docs/decisions/` as ADRs. A change that contradicts
  an accepted ADR is raised, not implemented around.
- All data is synthetic. No real-looking credentials, hostnames, or references
  to any specific commercial system.
- Figures in documentation come from actual runs.

## Invariants

Rules that must hold regardless of whether tests pass. Each has a test.

- **Grain.** One row is one charged unit: a service-data container for data, a
  record for voice and short messages. Containers are never aggregated away.
- **Volumes are deltas.** Each record carries its own interval. Session totals
  are sums. Record-level fields are never summed across rows of one record.
- **Idempotent ingestion.** Reprocessing a file leaves table state unchanged.
  Identity is node with local sequence number, plus container ordinal where
  applicable.
- **Quarantine over loss.** Records failing validation are retained with a
  reason. Nothing is silently dropped.
- **Unknown codes stay unknown.** A code absent from reference data is flagged
  and counted, never inferred from a similar value.
- **No session assembly in the pipeline.** Fragments are stored as they arrive;
  correlation identifiers let consumers group them.
- **Serving reads silver.** Gold is analytical only.
- **Freshness.** Thirty minutes from event occurrence to queryable. Changes
  that add latency to the ingest path require justification.
- **Local time throughout.** No conversion to UTC.

## Layout

```
datagen/      synthetic events and reference data
mediation/    binary decode
pipelines/    bronze, silver, gold
serving/      history APIs
docs/         format specification, decision records
tests/        scenario and regression tests
```
