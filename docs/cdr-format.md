# Input CDR format specification

Defines the input record formats consumed by this platform. Every type traces
to a freely available public specification (3GPP, IETF, ITU-T); anything
original is marked as such.

All input data is synthetic, generated against these grammars. There is no real
subscriber data, no real reference data, and no sample files from any
operational system.

---

## 0. Design principles

1. **Public lineage for every element.** The answer to "where did this schema
   come from?" is a document anyone can download.
2. **Industry patterns, not any particular implementation.** The general
   shapes are publicly specified; implementation-specific field inventories and
   tag layouts are not reproduced.
3. **One coherent format family.** All three sources share the same envelope,
   so the decoder, quality checks, and tooling are uniform.

### Shared framing

| Aspect | Choice | Public basis |
| --- | --- | --- |
| Abstract syntax | ASN.1 | ITU-T X.680 |
| Encoding | BER (Tag–Length–Value) | ITU-T X.690 |
| File container | header record + record stream | 3GPP TS 32.297 |
| Record framing | `CHOICE` of variants, tagged by `RecordType` | 3GPP TS 32.298 |
| Common types | `RecordType`, `IMSI` (TBCD-STRING), `MSISDN` (ISDN-AddressString), `TimeStamp`, `CallDuration`, `RecordExtensions` | 3GPP TS 32.298, `GenericChargingDataTypes` |
| Money | `MoneyAmount ::= SEQUENCE { valueDigits, exponent }` — exact decimal `valueDigits × 10^exponent` | IETF RFC 4006 unit-value shape |

**Time.** `TimeStamp` carries local time with a signed offset, not UTC.
Processing preserves local time end to end.

**Currency.** IDR throughout, declared here rather than carried per record.

### File container

```asn1
FileHeaderRecord ::= SEQUENCE {
  fileLength           [1] INTEGER,
  fileSequenceNumber   [2] INTEGER,          -- gaps reveal a missing file
  senderNodeId         [3] NodeID,
  fileOpenTimeStamp    [4] TimeStamp,
  lastAppendTimeStamp  [5] TimeStamp,
  recordCount          [6] INTEGER,          -- disagreement with contents is a defect
  fileClosureReason    [7] FileClosureReason,
  lostRecordIndicator  [8] BOOLEAN           -- upstream signalled loss
}
```

**File closure.** A file closes on whichever comes first: a size ceiling
(assumed 10 MB) or a maximum open interval. Arrival is therefore irregular —
frequent under load, timer-driven when traffic is low. The reason is recorded
in the header.

Three header fields carry the file-level quality anchors: the record count, the
file sequence number, and the lost-record indicator.

---

## 1. Usage records

**What they represent.** Network usage — voice calls, data sessions, short
messages — recorded as the subscriber consumes the network. Highest-volume
source.

**Public basis.** 3GPP TS 32.298 record types, taken from the published ASN.1
modules: `GenericChargingDataTypes` for common types, `CSChargingDataTypes` for
voice and short messages, `GPRSChargingDataTypes` for data sessions.

Records are declared `SET`, as in the specification: fields may appear in any
order and are identified by tag, not position.

### Subset and deviations

The specification's records are large — a mobile-originated call record carries
roughly fifty fields. This platform implements a subset. Every field the
specification marks mandatory is retained; the omitted fields are all OPTIONAL.

Deviations, stated explicitly:

- Parameterized types are not used. Bounded string types are replaced with
  plain equivalents. Encoded bytes are unaffected; only a length constraint is
  lost.
- Types imported from non-charging specifications are replaced with minimal
  local equivalents, each commented with its origin module.
- `listOfTrafficVolumes` is not populated. Records carry `listOfServiceData`
  only.
- Fields the specification marks OPTIONAL that this platform always emits —
  `servedMSISDN`, `nodeID`, `localSequenceNumber` — are declared mandatory. A
  tightening, not a relaxation.

### Data sessions

Modelled on `PGWRecord`, record type 85.

Mandatory in the specification and therefore retained: `recordType`,
`p-GWAddress`, `chargingID`, `servingNodeAddress`, `recordOpeningTime`,
`duration`, `causeForRecClosing`, `chargingCharacteristics`, `servingNodeType`.

Retained from the optional fields: `servedIMSI`, `servedMSISDN`,
`accessPointNameNI`, `recordSequenceNumber`, `nodeID`, `localSequenceNumber`,
`servingNodePLMNIdentifier`, `rATType`, `listOfServiceData`.

The service data list holds `ChangeOfServiceCondition` entries — one per rating
group per set of charging conditions. Within it, mandatory: `ratingGroup`,
`serviceConditionChange`, `timeOfReport`. Retained from the optional fields:
`timeOfFirstUsage`, `timeOfLastUsage`, `timeUsage`, `serviceIdentifier`,
`datavolumeFBCUplink`, `datavolumeFBCDownlink`.

Volumes are of type `DataVolumeGPRS`, in octets.

**Access technology.** `rATType` is a record-level field; the service data
entries do not carry it. The simulated node is configured to close the record
when the access technology changes — `causeForRecClosing` then carries
`rATChange` — so a record never spans two technologies and the record-level
value applies to every entry it contains. This is a configuration assumption,
permitted by the specification, not a deviation from it.

**Serving network.** `servingNodePLMNIdentifier` is likewise record level,
supplying the roaming dimension per record.

### Voice calls and short messages

Modelled on `MOCallRecord` and `MTCallRecord` (record types 0 and 1), and
`MOSMSRecord` and `MTSMSRecord` (types 6 and 7).

Mandatory for calls: `recordType`, `recordingEntity`, `callDuration`,
`causeForTerm`, `callReference`; `servedIMSI` additionally for the terminating
case.

Mandatory for short messages: `recordType`, `servedIMSI`, `msClassmark`,
`serviceCentre`, `recordingEntity`, `messageReference`, and the originating or
delivery timestamp.

Note that circuit-switched records carry `causeForTerm`, not
`causeForRecClosing`. The specification states there is no direct correlation
between the two types, so they are handled separately.

Short messages are atomic — a single record, no correlation or sequence fields.

### Interim records

A long data session is emitted as several records. An **interim** record is
closed by a limit or a condition change while the session runs; a **final**
record is closed by a normal or terminal release. A short session yields a
single complete record.

**Volumes are deltas.** Each record carries the volume accrued during its own
interval, not a running total. A session total is the sum of its records; a gap
in `recordSequenceNumber` means that sum is known to be incomplete.

**Time.** `duration` at record level is the wall-clock span the record covers.
`timeUsage` in a service data entry is the seconds that rating group was
actually active within that span. Rating groups run concurrently, so entry
times overlap and do not sum to the record duration.

Two signals indicate position in a sequence, neither an explicit flag:

- `recordSequenceNumber` is present only in a partial sequence. Its absence
  means the record covers the session by itself.
- `causeForRecClosing` distinguishes a record closed while the session
  continues from one closed because the session ended.

| Class | `causeForRecClosing` | Meaning |
| --- | --- | --- |
| Ended | `normalRelease (0)`, `abnormalRelease (4)`, `cAMELInitCallRelease (5)` | terminal record |
| Continues | `partialRecord (1)`, `volumeLimit (16)`, `timeLimit (17)`, `servingNodeChange (18)`, `maxChangeCond (19)`, `intraSGSNIntersystemChange (21)`, `rATChange (22)`, `mSTimeZoneChange (23)`, `sGSNPLMNIDChange (24)`, `sGWChange (25)`, `aPNAMBRChange (26)` | further records follow |
| Classify explicitly | `managementIntervention (20)` | operator action; session survival depends on the deployment |

Classification cannot be derived from the numeric range. The specification notes
that codes 0 to 15 correspond to the termination-cause type but that there is no
direct correlation between the two, and `partialRecord (1)` sits inside that
range while meaning the opposite. The mapping is therefore reference data,
maintained with the other tables. The enumeration also grows between releases,
so an unrecognized value is counted and surfaced rather than assumed into a
class.

No terminal flag is carried; one would only duplicate the cause. Enrichment
derives an `is_final` flag from the classification so that downstream consumers
do not carry the mapping.

Completeness remains uncertain regardless. If a session ends abnormally the
terminal record may never be produced. An ended-class cause is conclusive; its
absence is ambiguous, so no consumer may block waiting for one.

### Service condition changes

`serviceConditionChange` is a `BIT STRING`, not an enumeration — several
reasons may be set at once. A service data entry closes on any of them,
including quota management reasons that have no record-level equivalent:
thresholds reached, quota exhausted, reauthorization, validity timeout.

Bit positions of interest here: `qoSChange (0)`, `sGSNChange (1)`,
`sGSNPLMNIDChange (2)`, `tariffTimeSwitch (3)`, `pDPContextRelease (4)`,
`rATChange (5)`, `serviceIdledOut (6)`, `configurationChange (8)`,
`serviceStop (9)`, `dCCATimeThresholdReached (10)`,
`dCCAVolumeThresholdReached (11)`, `dCCATimeExhausted (13)`,
`dCCAVolumeExhausted (14)`, `recordClosure (24)`, `timeLimit (25)`,
`volumeLimit (26)`.

### Extensions

`ManagementExtensions` carries fields added after the base grammar. Extensions
the platform consumes are resolved into typed columns; the remainder is
retained, so fields introduced later can be recovered from history.

## 2. Account transaction records

**What they represent.** Value entering or being corrected on a prepaid
account: top-ups and adjustments.

**Public basis.** No public CDR standard covers these — they are outputs of
prepaid charging platforms rather than network elements — so the record is an
original account-ledger design. It adopts public vocabulary: Diameter
Credit-Control `Requested-Action` values from RFC 4006 and RFC 8506, and the
3GPP online-charging account model of TS 32.296.

```asn1
AccountTxnCdrFile ::= SEQUENCE OF AccountTxnRecord

AccountTxnRecord ::= CHOICE {
  fileHeader   [0] FileHeaderRecord,
  transaction  [1] AccountTransactionRecord
}

AccountTransactionRecord ::= SEQUENCE {
  recordType           [0] RecordType,          -- refill | adjustment
  recordNumber         [1] INTEGER,             -- position within the file
  originNode           [2] NodeID,
  originHost           [3] NodeAddress,
  transactionId        [4] TransactionID,       -- with originNode, the duplicate key
  eventTimeStamp       [5] TimeStamp,
  requestedAction      [6] RequestedAction,     -- RFC 4006
  transactionAmount    [7] MoneyAmount,
  accountId            [8] AccountID,
  servedMSISDN         [9] MSISDN,
  serviceClass        [10] ServiceClass,
  balanceBefore       [11] MoneyAmount,
  balanceAfter        [12] MoneyAmount,
  refillChannel       [13] RefillChannel OPTIONAL,
  voucherReference    [14] IA5String OPTIONAL,
  activationDate      [15] TimeStamp OPTIONAL,
  recordExtensions    [16] RecordExtensions OPTIONAL
}

-- Original: no public standard covers prepaid top-up channels.
RefillChannel ::= ENUMERATED {
  retailerPOS      (0),   -- pulsa counter, physical outlet
  modernRetail     (1),   -- convenience-store chain
  selfcareApp      (2),   -- operator application
  mobileBanking    (3),
  smsBanking       (4),
  internetBanking  (5),
  atm              (6),
  eWallet          (7),
  eCommerce        (8),
  physicalVoucher  (9),   -- pairs with voucherReference
  ussd            (10)
}
```

The before-and-after pair yields a chaining invariant: for one account ordered
by transaction time, `balanceAfter` of one movement equals `balanceBefore` of
the next. Breaks are surfaced.

---

## 3. Account lifecycle records

**What they represent.** State changes on the account itself — activation,
service-class change, expiry, barring. The account's own event log, written as
state transitions.

**Public basis.** Also an original design, framed with the account-state
concepts of TS 32.296.

```asn1
AccountLifecycleCdrFile ::= SEQUENCE OF AccountLifecycleEntry

AccountLifecycleEntry ::= CHOICE {
  fileHeader   [0] FileHeaderRecord,
  lifecycle    [1] AccountLifecycleRecord
}

AccountLifecycleRecord ::= SEQUENCE {
  recordType           [0] RecordType,
  recordNumber         [1] INTEGER,
  accountId            [2] AccountID,
  servedMSISDN         [3] MSISDN,
  serviceClass         [4] ServiceClass,
  eventTimeStamp       [5] TimeStamp,
  lifecycleEvent       [6] LifecycleEvent,      -- ACTIVATION | EXPIRY | BARRING | SERVICE_CLASS_CHANGE
  balanceBefore        [7] MoneyAmount,
  balanceAfter         [8] MoneyAmount,
  accountFlagsBefore   [9] AccountFlags,
  accountFlagsAfter   [10] AccountFlags,
  serviceClassBefore  [11] ServiceClass OPTIONAL,
  serviceClassAfter   [12] ServiceClass OPTIONAL,
  activationDate      [13] TimeStamp OPTIONAL,
  expiryDate          [14] TimeStamp OPTIONAL,
  recordExtensions    [15] RecordExtensions OPTIONAL
}
```

---

## 4. Provenance summary

| Element | Public origin |
| --- | --- |
| ASN.1 abstract syntax | ITU-T X.680 |
| BER encoding | ITU-T X.690 |
| File header and record stream | 3GPP TS 32.297 |
| `RecordType`, `IMSI`, `MSISDN`, `TimeStamp`, `CallDuration`, `RecordExtensions`, `CauseForRecClosing`, `LocationAreaAndCell` | 3GPP TS 32.298, `GenericChargingDataTypes` |
| Voice and short message records | 3GPP TS 32.298, `CSChargingDataTypes` (MOCallRecord, MTCallRecord, MOSMSRecord, MTSMSRecord) |
| Data session records and service data entries | 3GPP TS 32.298, `GPRSChargingDataTypes` (PGWRecord, ChangeOfServiceCondition) |
| `nodeID`, `localSequenceNumber`, `recordSequenceNumber`, `chargingID`, `callReference` | 3GPP TS 32.298 |
| `listOfServiceData`, `ratingGroup`, `serviceIdentifier`, `serviceConditionChange`, `DataVolumeGPRS` | 3GPP TS 32.298, `GPRSChargingDataTypes` |
| `MoneyAmount` unit-value shape | IETF RFC 4006 |
| `requestedAction` values | IETF RFC 4006 / RFC 8506 |
| Account balance and service-class concepts | 3GPP TS 32.296 |
| `AccountTransactionRecord`, `AccountLifecycleRecord` layouts | original |

---

## 5. Naming

Generic or public-specification names throughout: `recordType`, `servedIMSI`,
`servedMSISDN`, `callDuration`, `requestedAction`, `balanceBefore` /
`balanceAfter`, `serviceClass`, `recordExtensions`. Implementation-specific
field inventories and tag layouts are not reproduced.

---

## 6. How the data is produced

The generator emits BER files against these grammars with fixed seeds for
reproducibility, exercising every record variant and including deliberate
defects — a header record count that disagrees with the records present, gaps
in file sequence numbers, duplicate records, late files, unresolved codes.

Reference tables are synthetic or drawn from public sources such as published
MCC/MNC assignments and open geodata.

---

## 7. Open items

### Grain and coverage

- **Subscriber dimension source.** Enrichment uses two mechanisms. Code
  lookups resolve values carried in the record — rating group, serving PLMN,
  cell, RAT, closure cause, number prefix — and fail when a code has no entry.
  Dimension joins resolve attributes carried in no record at all, such as
  package and segment, and fail when the subscriber is unknown or the wrong
  version of an attribute is resolved. None of the three feeds is a subscriber
  master, so this requires a decision: add a subscriber dimension input, or
  derive what the account lifecycle feed supports — service class and its
  changes — and treat package and segment as unavailable.

### Decisions

- Whether usage records carry a remaining-balance figure alongside charge
  amount. Recommended not to: the account records already hold balance before
  and after, and duplicating it creates two sources of truth.
- Whether records carry a single fixed operator time zone or a per-record
  offset. Indonesia spans three zones; mixing conventions silently is a known
  source of error.

### Definitions to complete

- Assemble the trimmed ASN.1 module. Specification types are copied from the
  published modules; local equivalents are needed for the handful imported from
  non-charging specifications, principally `ISDN-AddressString` and
  `ManagementExtension`. Types with no specification source — `AccountID`,
  `TransactionID`, `ServiceClass`, `RequestedAction`, `LifecycleEvent`,
  `AccountFlags`, `RefillChannel`, `FileClosureReason`, `MoneyAmount` — are
  original and marked as such.
- The duplicate key for account lifecycle records. Transaction records use
  origin node with transaction identifier; lifecycle records carry neither.
- The cross-source join key. Usage records carry IMSI and MSISDN; account
  records carry MSISDN and account identifier but no IMSI, so MSISDN is the
  only identifier common to all three — and because numbers are reissued, the
  join is MSISDN together with service period.
- The cause-classification table, confirmed against the target release.

---

*Referenced specifications: 3GPP TS 32.296 / 32.297 / 32.298 (3gpp.org);
IETF RFC 4006 and RFC 8506; ITU-T X.680 and X.690.*
