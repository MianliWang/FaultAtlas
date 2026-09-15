# S1.P09.S02 — Supplied review attribution and source association

## Accepted scope

The user accepted design A and requested execution of the preceding S02 draft.
The accepted decision record is `P09-POST-S01-20260915-A`, 69501 bytes,
SHA-256 `2970325f839ec6dd4433309c1890649b3bdddb3c17a5eefc7fd609db17e2c9a8`;
the implementation draft is 30710 bytes, SHA-256
`7c1fc2050ef148a010ed5e0ed0f411ad8dda3ed7dab9207055eb4abfebe09cc3`.
The independent expected view is 4080 bytes, SHA-256
`e8392b028ba29ec2d89fbae939f4bd6891bb2cf62f978f75e90798ada4ddf16f`.
These describe preserved external design inputs, not runtime dependencies or
self-predicted test/publication results. Original unactivated labels remain history.

S02 adds a supplied attribution assertion around one complete existing
`SuppliedAssessmentReview` and one pure consumer. It separately exposes the
original review's supplier, the new assertion's supplier, the attributed reviewer
label and an optional full source-record reference. It changes no S01 value,
view, entry point or format. This is value binding, not occurrence identity.

SD02's accepted choices use a nullable reviewer label, a nullable complete durable
record reference, original-order competing/duplicate assertions, eight records
and a 9 MiB complete view. No provider-account model or source importer is added.
SD01 remains the earlier S01 decision, not blanket future attribution authority.

The previously recorded Phase-start/calibration ledgers and original S01 completion
JSON were unavailable during the accepted planning task; they were not recreated.
The historical activation, exact v2 component and published S01 owners supplied
the bounded design context. Old HTTP 422/null-target and historical attribution
limits remain; new synthetic examples are not historical provider-reviewed
FaultAtlas values. Tests validate the new contract, not archival recovery.

## Value and roles

`faultatlas.domain.assessment_review_attribution` exports exactly
`SuppliedAssessmentReviewAttribution`, with these required fields in order:

| Field | Type | Meaning |
| --- | --- | --- |
| `review` | `SuppliedAssessmentReview` | Complete existing canonical review, including its assessment |
| `reviewer` | strict string or `None` | Claimed reviewer label; null explicitly declares unknown |
| `source` | `DurableEvidenceRecordReference` or `None` | Record reference offered for this new assertion; null means none supplied |
| `attribution` | `AssessmentAttribution` | Supplier label and rationale for this assertion |

All fields are required without aliases/defaults; only `reviewer` and `source`
are nullable. Present reviewer text is 1–128 Unicode code points, UTF-8 encodable
and not whitespace-only. Other characters and surrounding whitespace survive.
The string `"unknown"` is a label, distinct from null. The existing attribution
owner retains its supplier/rationale bounds of 128/4096 code points.

The model is frozen/strict, forbids extras, always revalidates instances and
validates defaults. Python model children must have their declared types; native
JSON reconstructs through public owners, preserving nested review tuple/default
rules. Unchecked constructed/copied children are revalidated. No recursive list
conversion, private validator reuse or override of equality/Pydantic entry points.

The reviewer field names whoever this new assertion claims made the supplied
judgment. It does not automatically name the source author or establish that
anyone examined the assessment. Relaying/summarizing must not impersonate an
original reviewer or invent original rationale; a new summary is newly authored
and uncertain attribution remains unknown or explicitly qualified by its supplier.
The original review supplier and new assertion supplier are separate declarations.
Neither labels nor record references authenticate people, accounts or independence.

`ProviderGlobalId`, source-object identity and identity field states retain their
existing meanings; no account/user identity or generic label-state owner is added.
There is no new UUID, clock, status enum, registry or schema version. Model JSON
round trips are value representation, not a new durable-byte or review-file protocol.

## Pure consumer and binding

`faultatlas.assessment_review_attribution` exports only:

```python
def inspect_assessment_review_attributions(
    review: SuppliedAssessmentReview,
    attributions: tuple[SuppliedAssessmentReviewAttribution, ...],
) -> str:
    ...
```

Both arguments are explicit. Require the declared review type and
`type(attributions) is tuple`; check 0–8 capacity before iteration. Lists,
generators, tuple subclasses and arbitrary iterables are not coerced or consumed.
Revalidate the requested review and every assertion/child, then match the entire
review value in original order. Reject the first invalid member or valid mismatch;
return only a complete result after all checks succeed.

Matching includes review scope/judgment/original attribution and all nested
assessment values and order under existing owner equality. Unchanged basis,
narrow scope, same label or same digest never exempts a valid change. Equal
independent reconstructions match; raw JSON whitespace/key ordering is not identity.
Inherited default/null/omitted semantics are unchanged. Malformed children keep
their owner errors, distinct from independently valid mismatching targets.

Exact pure-API `ValueError` messages:

```text
review must be a SuppliedAssessmentReview
attributions must be a tuple
attributions must contain at most 8 supplied attribution declarations
attribution at index N must be a SuppliedAssessmentReviewAttribution
attribution at index N target does not match requested review
P09 review attribution inspection output budget exceeded (9 MiB)
```

N is zero-based. Existing child/Pydantic/S01 errors are not collapsed into these
messages. Equal original review occurrences share attribution eligibility; the API
does not distinguish copy 1 from copy 2. Display positions are not persistent IDs.
Keep exact duplicates, competing reviewer labels/references and input order, with
no conflict detection, sorting, latest-wins, independence test or winner.

Empty attributions means no declarations. A supplied declaration with null
reviewer explicitly states unknown; null source means no source association
supplied, not inaccessible/nonexistent source material. A reference may remain
supplied while its bytes are unavailable. Availability reports may appear in
opaque rationale, but are not parsed into a machine-readable state.

The source concerns the new assertion, not automatic membership in assessment
materials. Validate the complete six-field existing reference value; require no
material-universe match and perform no dereference. Raw URLs, source/account IDs,
filenames and bare hashes are not references. Association establishes no access,
support, authorship, freshness or source-event coverage. A provider review does
not prove authorship or review of newly composed FaultAtlas content. Repeating an
assertion for another reference does not establish independent corroboration.

## Exact complete view

The view starts with `Supplied review attributions - non-authoritative inspection`
and `Complete review value:`, each followed by LF. It embeds the unchanged public
S01 view for `(review.assessment, (review,))` exactly once, including its final LF,
without requotation or a copied/private renderer. Then it prints
`Attribution declarations: N`. For zero, the next line is
`Attributions: none supplied; no reviewer inferred`; otherwise it is
`Attribution targets: all declarations match the complete requested review value`.

Each one-based position K has these lines:

```text
Attribution K
Attribution assertion supplier: Q(attribution.supplier)
Attribution assertion rationale: Q(attribution.rationale)
Attributed reviewer: Q(reviewer)
Source record association: J(source)
```

Q is recoverable ASCII JSON quotation, with DEL also escaped as `\u007f`. Null
reviewer instead prints `explicitly unknown`. J is compact ASCII JSON of the
complete source owner value in owner field order: `schema_version`, `format_name`,
`format_version`, `canonicalization`, `sha256`, `byte_length`. It is not quoted
again. Null source prints `none supplied; availability not asserted`.

Every view has this exact suffix:

```text
Attribution labels are supplied claims; account identity, authorship and independence are not verified.
Source records are associated by declaration; bytes are not retrieved or verified as support.
Equality identifies the supplied review value, not a particular repeated occurrence.
No availability status, approval, confidence or review lifecycle is inferred.
End of complete review attribution view
```

All lines use LF; no blank separators, printing, streaming or truncation, and
exactly one final LF. Controls/bidi/instructions/URLs remain inert. The original
supplier, new supplier and attributed reviewer are not conflated. Complete
authored inputs and expected text live in the two new tests, without runtime
planning-file access or a renderer-generated sole oracle.

## Finite composition

The actual complete UTF-8 view cap is **9 MiB = 9,437,184 bytes**. Eight is a
bounded inspection default, not a statistical/identity threshold. Conservatively:

```text
one S01 review view <= 8 MiB + 12416*12 + 8192 = 8,545,792
whole view <= 8,545,792 + 8*((128+128+4096)*12 + 576) + 4096
           = 8,972,288 < 9,437,184 bytes
```

The reference's admitted ASCII strings have limits 160/64/160/64, with all six
keys/punctuation and up to 19 byte-length digits: at most 573 compact bytes,
reserved as 576. New fixed labels/quotes/LFs fit 4096 bytes (1688 present, 2136
with conservative null messages, 562 empty). The S01 target view is embedded once
and new Unicode scalar quotation costs at most twelve ASCII bytes per code point.
Keep the inherited output refusal and independently guard the new complete view.

Each review has normalized bounds of 8204 nodes, 514 objects, 143539 string code
points and depth 33. A wrapper adds 11 nodes, two objects, 48 key and 4352 prose
code points, plus one reference at most: 13 nodes, one object and 520 string code
points. Across one requested review and eight assertions, conservative logical
occurrence totals are 74028 nodes, 4650 objects and 1331211 string code points,
excluding a call container; assertion depth is at most 34.

Every embedded review/reference is revalidated and every review compared in full;
the S01 consumer repeats its validation too. No object-identity shortcut, cache
or second generic budget walker is introduced. Normalized/display bounds are not
raw-parser, peak-memory, CPU, wall-clock or OS-resource guarantees.

## Compatibility and remaining responsibilities

All thirty preceding production files, S01's two tests/contract/APIs, P08 file
format/CLI and package-root exports remain unchanged. Only two new modules join
the current inventory. No dependencies or corpus root are added. Current
lifecycle expectations stay in their existing owner; S01 and S02 completion
clauses remain local with P09 active and its next scope-planning gate. The exact
old P08 handoff node still checks sealed history, with its original refusals.

All seventeen source-qualified inherited records retain their original subjects,
states, owners, consequences and decision points. The proposal does not redefine
them as only generic contracts or discharge them through supplied/qualitative
wording. P00 confidence/review design and multi-case conditions, historical/causal
evidence restrictions, P01 operational-completion conditions, P02's original
`S1.P02.S07_phase_closure` points and P03's absent deadline fields remain literal.
S07 interpretation identity, producer/reviewer, immutable evidence, time and later
supersession requirements remain. P07/P08 empirical unknowns keep their owners.

This increment establishes no authentication, authorization, approval, confidence
scale, review lifecycle, persistence, source availability or historical completeness.
P09 remains active/incomplete; further scope planning and activation are separate.
Actual local/installed/package/review/PR/main results belong in the external
execution receipt, not self-certified contract fields.
