# Subscriber Activity Record — Customer Support

Data platform for a simulated prepaid mobile operator. Network usage and
account events feed two consumption paths: a low-latency subscriber activity
view for customer care, and daily marts for analytics.

All data is synthetic. The generator reproduces the delivery patterns,
encoding, and defects of operational telecom sources.

## Goals

- Ingest binary-encoded CDRs with bounded memory
- Resolve coded network attributes against externally maintained reference data
- Serve subscriber activity lookups with observable freshness
- Produce complete daily marts with a defined late-data policy
- Idempotent ingestion and quarantine over silent loss
- Reproducible on local or free-tier infrastructure

## Non-goals

- **Billing, rating, and charging.** CDRs are consumed for operational
  visibility, not revenue computation
- **Real-time processing.** The design is micro-batch; freshness is measured,
  not instantaneous
- **Production hardening.** Authentication, multi-tenancy, and user interfaces
  are outside this scope

## Sources

Three synthetic feeds, each with a distinct structural archetype:

| Source | Grain | Structure |
|---|---|---|
| Usage | One call or data session, or one interval of a longer one | Tagged union of record types, deep optionality, a nested list of per-quota-bucket containers, and an extension list for later additions |
| Account transaction | One financial movement — top-up or adjustment | Flat and positional; carries account state before and after the movement |
| Account lifecycle | One state change — activation, class change, expiry, barring | Flat and positional; a tagged union of many event variants |

Usage records are the largest and most complex of the three. Their record
syntax follows a trimmed subset of 3GPP TS 32.298 and file framing follows
TS 32.297; the account feeds use original schemas, as no public standard covers
them. Full specification: [`docs/cdr-format.md`](docs/cdr-format.md).

## Architecture

```
generator ──▶ landing (encoded) ──▶ mediation decoder ──▶ landing (decoded)
                                                                  │
                                                                  ▼
                                                       bronze   raw, as delivered
                                                                  │
                                                                  ▼
                                                       silver   normalize · dedupe
                                                                late data · enrich
                                                                quality expectations
                                                                  │
                                                  ┌───────────────┴───────────────┐
                                                  ▼                               ▼
                                        gold  activity view              gold  daily marts
                                                  │                               │
                                                  ▼                               ▼
                                            activity API                  analytical SQL
```

| Component | Responsibility | Runtime |
|---|---|---|
| Generator | Synthetic subscribers, stateful events, reference tables, injected defects | Python |
| Mediation decoder | Binary CDR files to columnar records under a fixed memory ceiling | Python |
| Bronze | Append-only landing with source lineage | Spark |
| Silver | Normalization, dedupe, late data, enrichment, quality gates | Spark |
| Gold | Activity view for lookup, scoped to the current service period; daily marts for analysis | Spark |
| Activity API | Point lookup of recent activity, with freshness metadata | Python |
| Observability | Freshness, quarantine, and processing metrics | Python / SQL |

## Design decisions

**Decode outside the distributed engine.** ASN.1 BER files expand roughly an
order of magnitude in memory when decoded wholesale, and executors are the
worst place to absorb that. A standalone decoder parses sequentially and emits
bounded batches — the mediation stage of operational telecom architectures.
Lakehouse input contract: decoded columnar files.

**Session fragments are preserved, not stitched.** A long session is emitted as
several interim records, closed on volume or time limits. Ingestion keeps one
row per record and carries identity and correlation fields through, so loads
stay idempotent and nothing waits on a session that has not ended. Session
totals are a derived aggregate, recomputed for the sessions a batch touches and
marked open until a terminal record arrives.

**Extensions are projected, not discarded.** Usage records carry an extension
list for fields added after the base grammar. Extensions the platform consumes
are resolved into typed columns and the remainder is retained, so fields
introduced later can still be recovered from history.

**Micro-batch, not streaming.** Files arrive at short intervals against a
sub-hour freshness objective. Scheduled batches meet it at lower operational
complexity. Revisited if the objective tightens.

**Transactional table format.** Concurrent read and write, late-data
restatement, and reference-data rewrites require atomic commits, snapshot
isolation, and merge semantics — Delta Lake.

**Serving separated from storage.** Point lookups run against a materialized
store refreshed by the gold stage; lakehouse tables are optimized for scans.

**Versioned reference data.** Enrichment preserves the mapping in effect at
event time, keeping historical outputs reproducible.

## Correctness

- **Idempotent ingestion** — reprocessing a file leaves table state unchanged
- **Quarantine over loss** — failed records retained with a reason
- **Unknown codes stay visible** — a code with no entry in the reference tables
  is marked unresolved and counted, never guessed from a similar value or
  dropped
- **Grain is explicit** — a usage record measures its own interval, not a whole
  session; aggregates sum correlated fragments rather than counting rows, and
  flag sequences known to be incomplete
- **Balance continuity** — account transactions carry state before and after
  the movement; consecutive movements on an account are checked to chain, and
  breaks are surfaced
- **Unrecognized record variants** are retained and counted rather than skipped
- **Late data** — rolling window on the interactive path; defined close and
  restatement rule on the daily path

## Testing

Seeded scenarios assert exact output for scripted subscriber histories,
including unresolved-code and late-arrival cases. Decoder memory ceiling
asserted. Idempotency asserted by replay. Quality expectations run inside the
pipeline.

## Stack

Python · Spark · Delta Lake · DuckDB · FastAPI. Runs locally through Docker on
open-source components, and on Databricks Free Edition unmodified.

## Layout

```
datagen/      synthetic events and reference data
mediation/    binary decode
pipelines/    bronze, silver, gold
serving/      activity API and materialization
docs/         format specification, design notes, decision records
tests/        scenario and regression tests
```

## Status

Design phase. Figures are published once measured; none are claimed in advance.
Decisions: [`docs/decisions/`](docs/decisions)

## Development notes

AI-assisted for scaffolding, tests, and documentation. Architecture,
transformation logic, and correctness properties are hand-authored. Significant
choices are recorded as architecture decision records.
