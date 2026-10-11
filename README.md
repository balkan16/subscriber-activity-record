# Subscriber Activity Record

A data platform for a simulated prepaid mobile operator. It answers the question
customer care hears most often: *"What happened on this number?"* Which calls,
messages and data sessions used the line, and how the balance moved, available
within 30 minutes of the event.

All data is synthetic. A generator produces the same kind of binary files a real
network produces, including their delivery patterns and their defects.

## In one picture

```
generator ──▶ binary CDR files ──▶ decoder ──▶ bronze ──▶ silver ──┬──▶ history APIs   (customer care)
                                                                    └──▶ gold marts     (analytics)
```

1. **Generator** writes three kinds of binary file, the way network and charging
   systems do.
2. **Decoder** reads each file one record at a time, using a fixed amount of
   memory however large the file, and writes plain columnar files.
3. **Bronze** stores what arrived, unchanged.
4. **Silver** cleans it: removes duplicates, handles late arrivals, looks up
   codes, and runs quality checks.
5. **History APIs** read silver and return a subscriber's recent activity.
6. **Gold** holds daily summaries for analysis.

## Terms used here

| Term | Meaning |
|---|---|
| CDR | Call Detail Record: one record of network activity (a call, a message, part of a data session) |
| ASN.1 / BER | The schema language and binary encoding telecom systems use for CDRs |
| MSISDN | The subscriber's phone number |
| Feed | One stream of files from one kind of source |
| Bronze / silver / gold | Raw, cleaned, and summarised layers of the lakehouse |

## The three feeds

| Feed | One record is | Example |
|---|---|---|
| Usage | one call, one message, or one part of a data session | a 3-minute call; 40 minutes of mobile data |
| Account transaction | one money movement | a top-up of 25,000; a 10 GB package purchase |
| Account lifecycle | one change of account state | activation, barring, unbarring, class change, expiry |

Each feed has its own file type and its own directory. Usage records follow a
trimmed subset of the 3GPP standard (TS 32.298); each file starts with a header
record modelled on TS 32.297, followed by the records back to back. The account
feeds have no public standard, so their schemas are original.

Full format: [`docs/cdr-format.md`](docs/cdr-format.md) · grammar:
[`docs/cdr-format.asn`](docs/cdr-format.asn)

## The generator

The generator does not try to simulate a whole network. It produces random
activity, held to a few rules so the pipeline's checks have something real to
test:

- **One balance per subscriber.** Every top-up, purchase and lifecycle event
  records the balance before and after, and each record's "before" equals the
  previous record's "after", across both account feeds.
- **Sessions hang together.** The records of one data session share one
  correlation identifier and are numbered 1, 2, 3 with no gaps. Only the last
  one carries an "ended" reason.
- **Calls interrupt data.** Voice runs on 2G here, so a call closes the current
  data record with a technology-change reason, and the session resumes after the
  call ends.
- **Blocked accounts are silent.** A barred or expired subscriber produces no
  usage until the account is active again.
- **Optional fields are sometimes missing**, as in real files, so the pipeline
  has to cope with absent values.

| Module | Role |
|---|---|
| `datagen/packing.py` | Converts phone numbers, times and flag sets into the byte layouts the records require |
| `datagen/writer.py` | Writes records to a binary file and reads them back |
| `datagen/ledger.py` | Holds account state; produces transaction and lifecycle records |
| `datagen/session.py` | Produces usage records: data sessions, calls, messages |
| `datagen/activity.py` | Asks the ledger whether a subscriber may use the network before producing usage |

## Key design decisions

Each decision has a record in [`docs/decisions/`](docs/decisions).

- **Decode outside Spark.** Binary CDR files grow roughly tenfold in memory when
  decoded all at once. A separate decoder reads one record at a time and hands
  Spark plain columnar files. (ADR-004)
- **Keep session parts as they arrive.** Long data sessions arrive as several
  records. Each is stored as its own row; nothing waits for a session to end.
  Session totals are calculated afterwards. (ADR-006)
- **One row per charged unit.** A data record holds one container per charging
  bucket; each container becomes a row. Calls and messages are one row each.
  (ADR-007)
- **Usage carries no money.** The standard has no cost field on usage records;
  charges appear only in the account feeds. (ADR-015)
- **Different duplicate keys per feed.** Each feed identifies a record by
  different fields, so each has its own rule for spotting duplicates. (ADR-014)
- **Micro-batch, not streaming.** Files close every ten minutes at most, which
  already uses up a third of the 30-minute budget. Checking for new files every
  minute is enough; continuous streaming would add complexity without
  recovering that time. (ADR-010)
- **APIs read silver.** The APIs return detail rows, so they read the cleaned
  detail layer directly. Gold is for analysis only. (ADR-011)
- **Scale is measured, not claimed.** The same pipeline runs at 1x, 2x, 5x and
  10x volume; memory, time and freshness are recorded at each. (ADR-016)

## Correctness rules

- Reprocessing a file leaves every table unchanged.
- Records that fail checks are kept aside with a reason, never silently dropped.
- A code missing from the reference tables is flagged and counted, never guessed.
- Consecutive balance records must chain; breaks are reported.
- Unknown record types are kept and counted, not skipped.
- Times stay in local time throughout.

## Status

| Part | State |
|---|---|
| Record grammar (`docs/cdr-format.asn`) | done |
| Generator: packing, file writer, ledger, usage sessions, status gate | done, tested |
| Generator: subscriber population, event loop, defect injection | next |
| Decoder | planned |
| Bronze, silver, gold | planned |
| History APIs | planned |

Performance figures are published once measured; none are claimed in advance.

## Running the tests

```bash
python3 -m pip install asn1tools pytest
python3 -m pytest tests/ -v
```

Run from the repository root.

## Layout

```
datagen/      synthetic data generator
mediation/    binary decoder
pipelines/    bronze, silver, gold
serving/      history APIs
docs/         format specification, grammar, decision records
tests/        tests
```

## Stack

Python · asn1tools · Spark · Delta Lake · FastAPI. Runs locally on open-source
components, and on Databricks Free Edition.

## Development notes

AI-assisted for scaffolding, tests, documentation and parts of the generator.
Architecture, record design and correctness rules are hand-authored. Significant
choices are recorded as decision records.
