# S1.P09.S03 — Portable supplied-review documents

## Accepted scope and provenance

ACTIVATION-01 accepts design A and the immediate library-bytes delivery choice.
The original draft is 31504 bytes, SHA-256
`12c9c719fb024c2c1f24fecbfbaec6c597e06ad3e075cc53f177cb30003b638d`.
Its primary planning ledger is `P09-POST-S02-REMAINING-01`, 50207 bytes,
SHA-256 `4795bbd7a3c593a8e30f4d7fb338eff595725ac4bfe38e256b7bb7c1a8eb7d01`.
The received activation is 46452 bytes, SHA-256
`8d23b8a19ff36b34a12874e1289a68abd1dd8b925b83719016987099a4287ae4`.
Its embedded draft has table-padding/final-LF differences; the available original
matching the bound digest controls. Both received and original bytes are preserved
in external execution evidence. Historical unactivated labels do not cancel the
user's explicit dispatch. These external files are not runtime dependencies.

The producer already holds one whole S01 supplied review and 0–8 whole S02
attribution assertions. This increment returns a stable document that another
library caller can decode, inspect and re-encode. Caller-owned transport is the
delivery boundary. No selected-file API, P08-file conversion, CLI, storage backend,
source retrieval or effective-review policy is added. The narrow P09 format
precedes general P10 persistence without implementing or activating P10.

## Public interface and dependencies

`faultatlas.assessment_review_document.__all__` contains exactly, in this order:

```python
def encode_assessment_review_document(
    review: SuppliedAssessmentReview,
    attributions: tuple[SuppliedAssessmentReviewAttribution, ...],
) -> bytes: ...

def decode_assessment_review_document(
    data: bytes,
) -> tuple[SuppliedAssessmentReview, tuple[SuppliedAssessmentReviewAttribution, ...]]: ...

def inspect_assessment_review_document(data: bytes) -> str: ...
```

These pure synchronous functions consume the public S01/S02 model owners and
`inspect_assessment_review_attributions`. Stdlib `json` and `typing` are their
only other direct imports. No private validator/codec, new domain model,
package-root export, equality override, dependency or persistent cache is added.
Every operation makes one public S02 inspection invocation after the preceding
admission steps succeed. It returns no partial value, bytes or view on failure.

The byte operations perform no file/network access, subprocess execution,
clock/UUID allocation, environment/configuration read, printing or callback.
Imports do not probe a filesystem backend. Document text, locators, instructions
and attribution remain data. The caller's initial byte acquisition and subsequent
transport are outside these guarantees.

## Exact v1 format and meaning

Exactly one JSON object has these four required keys and no others:

| Key | Meaning |
| --- | --- |
| `format` | Exact string `faultatlas-supplied-review` |
| `version` | Exact integer 1; bool is not an integer version |
| `review` | One complete native-JSON `SuppliedAssessmentReview` |
| `attributions` | Array of 0–8 complete native-JSON `SuppliedAssessmentReviewAttribution` values |

Every assertion includes its whole target review. The format has no target
inheritance, compact pointer, positional identity, timestamp, status or envelope
default. All S01/S02 child-required fields, nullable fields, defaults, scalar
bounds and ordered-array semantics remain owner-defined.

The requested review and each assertion are independently validated. The whole
assertion target must equal the requested review: its scope, judgment, original
attribution and complete assessment, including opinions, nested attribution,
revision and ordered members. Equal reconstruction matches. A narrow scope,
unchanged basis, matching label, UUID or hash cannot excuse a valid difference.
Repeated full targets remain separate occurrences of the same value, without
assigning a persistent occurrence identity.

Order, duplicate records, competing reviewer labels and source references survive.
An empty assertion array means none supplied. A required null reviewer means
explicitly unknown; `"unknown"` is a supplied label. A required null source means
no association supplied, not an availability observation. Each present source
retains all six fields of its `DurableEvidenceRecordReference`; it is not opened,
verified as supporting evidence or required to belong to assessment materials.
Original review supplier, assertion supplier and attributed reviewer stay separate.

No authentication, authorship, independence, examination, applicability, freshness,
support, confidence, conflict adjudication, withdrawal or supersession is inferred.
An external provider review is not automatically a review of newly authored
FaultAtlas content. Missing original rationale must not be invented.

## Raw intake and failure order

Decode and inspect accept only `type(data) is bytes`. No string, bytearray,
memoryview, bytes subclass or iterable conversion occurs. The raw cap is checked
before decoding. UTF-8 is strict; BOM and invalid encoding fail without guessing,
replacement decoding or normalization.

A string/escape-aware scan refuses container nesting beyond 36 before recursive
JSON parsing. It supplies a bound, not a substitute JSON parser. The stdlib
decoder rejects malformed, empty or multiple documents and trailing non-whitespace.
Hooks reject duplicate decoded keys at any object, float/exponent tokens,
nonfinite constants, integer lexemes longer than 20 characters and integers outside
signed 64-bit range. Decoded keys and strings must be UTF-8 encodable; escaped lone
surrogates fail. Null and bool remain JSON primitives subject to owning field rules.

Global byte, encoding, lexical, JSON and raw-tree admission precede semantic
construction. Then require exact root shape, format, integer version, object
review and array assertions. Check assertion capacity before constructing the
requested review or any assertion. Validate the requested review first, then each
assertion and its complete target match in order. The first owner-invalid member
or valid mismatch wins. An early semantic mismatch outranks a later owner-invalid
parsed member, but never a global syntax, duplicate-key, number, encoding or
resource failure in that same document.

After successful reconstruction/binding, invoke the unchanged public S02 inspector
once. Independently check the complete normalized document and canonical encoding
before returning even a decoded pair or view. This establishes representability
and decode/encode closure; admission cannot return a value that this format cannot
encode. Inspect returns that one complete S02 view unchanged, including its LF.

Encode first invokes public S02 to preserve exact typed-argument, tuple/capacity,
child-validation and binding behavior. Revalidate the declared model owners before
projecting their values; do not serialize an unchecked original or subclass extra
field. Count and encode the complete normalized envelope. Revalidation may repeat
bounded traversals; it is not bypassed using object identity or a cache.

## Canonical bytes and separate display

The normalized projection includes all defaults, unset values and nulls.
Canonical bytes use stdlib `json.dumps` with `sort_keys=True`, compact separators
`(',', ':')`, `ensure_ascii=False`, `allow_nan=False`, strict UTF-8 and exactly one
final LF. Only object keys sort; arrays retain order. No Unicode normalization.
Canonical document bytes can contain literal Unicode and are not terminal-safe
display text. The inherited complete S02 view retains its recoverable escaping.

Accepted whitespace, key-order, escape and default-omission differences normalize.
The complete decoded values survive, and re-encoding canonical input produces
identical bytes. Original input bytes are not modified or archived by this API.
This is the project's v1 representation, not an external canonical-JSON standard,
signature, authentication mechanism or record-registration service. Future owner
changes must preserve this v1 contract or receive separate format authority.

The [README example](../../README.md#portable-review-document-bytes) provides a
complete supplied input and decode/inspect/encode/reopen calls. The test owner
contains frozen complete parallel, sparse/default and Unicode input/value/byte/view
oracles copied from the verified pre-implementation companion. The small canonical
example is 982 bytes, SHA-256
`ddd10452c3f5f45220087e31069addbb8fe493e897d6bae02df4a1501013972f`;
its complete view is 2627 bytes, SHA-256
`8297c6942ffd6e23f243fd3d2c8346e1df9dcf6062a2c43f2c1d8baedff18990`.
The parallel view retains its independently authored S02 4080 bytes and digest
`e8392b028ba29ec2d89fbae939f4bd6891bb2cf62f978f75e90798ada4ddf16f`.
These are synthetic examples, not additional real cases or provider-reviewed values.

## Diagnostics

New failures are `ValueError` with exact fixed messages:

| Failure | Message |
| --- | --- |
| Non-exact bytes | `P09 review document: BYTES_REQUIRED` |
| Raw/canonical/count/depth bound | `P09 review document: RESOURCE_LIMIT` |
| BOM, invalid UTF-8, escaped lone surrogate | `P09 review document: INVALID_ENCODING` |
| Syntax, duplicate decoded keys, forbidden numeric grammar | `P09 review document: INVALID_JSON` |
| Wrong root keys/type, review not object, assertions not array | `P09 review document: INVALID_SHAPE` |
| Wrong format value/type | `P09 review document: UNSUPPORTED_FORMAT` |
| Wrong version value/type | `P09 review document: UNSUPPORTED_VERSION` |

Capacity retains `attributions must contain at most 8 supplied attribution declarations`.
Valid mismatch retains `attribution at index N target does not match requested review`,
with zero-based N. Other typed Python, child/Pydantic and S01/S02 errors retain
their original source, including output-budget refusals. No broad exception wrapper
turns an owner failure into malformed JSON. The new messages interpolate no input
fragment. Owner exceptions are not converted into a safe CLI protocol; the caller
owns presentation. Unexpected programming failures remain visible. Failure has no
external mutation, publication, partial-success return or rollback effect.

## Finite composition

| Domain | Maximum |
| --- | ---: |
| Raw and canonical bytes, independently | 16777216 each |
| Assertions | 8 |
| Raw and complete normalized nodes | 74036 |
| Objects | 4651 |
| String code points, including keys | 1331268 |
| Container depth, root = 1 | 36 |
| Complete view, unchanged S02 owner | 9437184 bytes |

Each dict/list/scalar occurrence is a node, and each object key adds a string node.
Dicts count as objects; scalar leaves add no container depth. Every repeated target
counts again. S02's one requested review plus eight assertions bounds are 74028
nodes, 4650 objects, 1331211 string code points and assertion depth 34. The envelope
adds eight nodes, one object, 57 key/format code points and two container levels.
Each review retains S01's 8204 nodes, 514 objects, 143539 code points and depth 33.

Canonical UTF-8 JSON conservatively fits
`6*1331268 + 24*74036 + 1 = 9764473` bytes, below 16 MiB. Six covers worst admitted
text expansion; 24 per node reserves scalar tokens, quotes and delimiters, with
one final LF. Keep actual byte guards despite that arithmetic. S02's display bound
remains 8972288 < 9437184 bytes, without a second quotation or added prefix.

Physical raw byte/tree/depth and field/capacity witnesses are distinct from injected
guards for narrower canonical/normalized limits. Neither proves parser allocation,
peak memory, CPU, wall-time, cancellation latency or the caller's read budget.
There is no new operating-system or filesystem backend qualification.

## Compatibility, validation ownership and remaining work

All 32 preceding production files retain their S02 bytes. Current production count
is 33; no old product API, P08 v1, CLI, root export, UUID inventory or dependency
changes. The manually authored current inventory, shared package/build owners and
whole-production dependency screens retain their duties. The new test owns complete
oracles, refusal order, guards, purity and real installed-byte consumers. Installed
producer/reopen processes load every FaultAtlas module from the actual wheel
installation outside the checkout; import-only success is insufficient.

Mutable lifecycle remains in its existing owner. Candidate S03 completion stays
local with S01/S02 complete, P09 active/incomplete and no successor authorization.
The exact sealed P08 historical handoff node and its refusals remain meaningful;
current local summaries cannot borrow completion/gate clauses from later prose.
E01 build reuse retains exact code/harness/environment/input/artifact/Git binding;
inherited real file/IPC and isolated build profiles remain unchanged. Actual
command, review and protected-publication outcomes belong in external receipts.

The original 17 source-qualified obligations and S07/S08 interpretation, timing,
review and supersession constraints retain their original fields and owners.
P02's original decision points and P03's absent deadline/consequence fields are
not rewritten. Supplied references and P03 relationship primitives establish no
effective review policy. Historical attribution, direct cache-causation evidence,
identity, support/confidence meaning and lifecycle prerequisites remain unresolved.
P07/P08 empirical responsibilities do not move. The stronger route outcomes,
managed file/CLI delivery, P09 closure, S04 and P10 remain separately unapproved.
