# ADR-013: Three feeds, three file types

Date: 2026-08-05 · Status: accepted

## Context

The platform consumes three feeds: network usage, account transactions, and
account lifecycle events. Each is produced by a different source on its own
schedule.

## Decision

Each feed has its own file type, declared as a sequence of a choice whose first
alternative is the file header.

The file types describe file structure. Decoding is per record.

## Alternatives

**Merge the two account feeds into one file type.** Rejected — they are produced
independently, and merging would couple their delivery and their sequence
numbering.

**Decode a file as a single object using the file type.** Rejected — it would
hold every record in memory at once, defeating the bounded-memory design. The
file types exist for documentation; the streaming reader is what actually reads
files.

## Consequences

- Each feed has independent file sequence numbering, so a gap in one says
  nothing about the others.
- Three landing paths and three file writers.
- The choice construct is what allows a header and data records to share one
  stream, since every element of a sequence must be the same type.
