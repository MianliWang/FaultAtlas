# S1.P09.S01 — Supplied assessment review and pure inspection

## Accepted design basis and scope

ACTIVATION-01 separately accepted `CAL-P09-20260915-A` and SD01, then activated
the English S01 v2. The external calibration ledger is 215435 LF bytes with
SHA-256 `b52ac5382ac490bb8dd603779a6dfd9e1b5c9e40ef7d4a8f8e568f3543cb1820`;
the accepted v2 is 52073 LF bytes with SHA-256
`cdc7f5036de7bfd43c867c8dae6b3ed55cce793b4185fd75abe96b8f5f947cdf`.
The dispatch digest is
`4dcf289c2c8eedf61cbc802fcb369dfaacd80ea91b5d4374e5e2b5e9f52c45d3`.
Original draft/acceptance-pending labels remain historical observations in those
preserved external artifacts. They are not runtime or offline-test dependencies.

The accepted design analysis concerns one retained pytest-4412/PR4414 case and
two different Bitcoin technical cases, PR15986 and PR33724. It supports exact
target binding, declared coverage, supplied judgments/attribution and preservation
of parallel records. It does not establish statistical calibration, complete
historical attribution, verified cache causation or correctness of those projects.
Old-commit 422 responses, null historical review targets and missing original
scope/rationale remain limitations. Newly authored assessment/review examples
are not historical provider-reviewed FaultAtlas values. Tests exercise synthetic
values and declared semantics, not replay of external evidence.

SD01 accepts this first library consumer as a review declaration and inspection
increment: no review-state transition, authoritative lifecycle or common confidence
model. All 17 inherited original records retain their identities, subjects,
states, owners, consequences and decision points. No P07/P08 exception transfers,
and no stronger causal/completeness/review conclusion is authorized. The next
product step requires separate P09 scope planning; no successor Slice is selected.
Actual validation and protected-publication results belong in external receipts.

## Public value

`faultatlas.domain.assessment_review` exports only `SuppliedAssessmentReview`.
Its four ordered fields are required, non-null, without aliases or defaults:

| Field | Type | Meaning |
| --- | --- | --- |
| `assessment` | `SuppliedAssessment` | Entire canonical supplied target under its existing owner's equality/order semantics |
| `scope` | strict string | Supplied declaration of what the reviewer says they examined |
| `judgment` | strict string | Opaque supplied judgment; no inferred category or verdict |
| `attribution` | `AssessmentAttribution` | Supplied record label and rationale, using the existing owner |

Scope and judgment have 1–4096 Unicode code points, must be UTF-8 encodable and
not whitespace-only. Other whitespace and characters are preserved. The existing
attribution owner retains supplier's 128-code-point and rationale's 4096-code-point
limits. The model is frozen/strict, forbids extra fields, always revalidates model
instances and validates defaults. Python children must have their declared types;
normal native JSON reconstructs through the public child owner, preserving its
tuple/default language. No recursive list coercion, private validator reuse,
custom equality/hash, identity, time, status or schema version is added.

The record supplier label need not name the reviewer or actual caller. A relayed
statement may attribute a review to a person in supplied prose; that attribution
does not authenticate identity, authorship or independence. Missing original
review rationale cannot be invented. A new supplier may explicitly describe its
absence in a newly authored record without impersonating the old review's author.

Normal Pydantic dump/reconstruction operations represent values, without a new
durable-byte format, file envelope, codec or persistence guarantee. The review is
outside and non-mutating of the target assessment.

## Pure consumer and exact target

`faultatlas.assessment_review` exports only:

```python
def inspect_assessment_reviews(
    assessment: SuppliedAssessment,
    reviews: tuple[SuppliedAssessmentReview, ...],
) -> str:
    ...
```

Require the declared assessment type and `type(reviews) is tuple`; check capacity
0–32 before iteration. No list/iterator/generator/tuple-subclass conversion occurs.
Revalidate the requested assessment and each complete review through their owners,
then compare the entire target value. Process records in order and reject the
first invalid member or mismatching target before returning a complete view.

Matching includes source/target/scope/context, conditions/materials, root and nested
attribution, opinions, conflicts, overall opinion and ordered members. A valid
change to an opinion or attribution mismatches despite an unchanged basis or narrow
scope declaration. Independent reconstruction of the same canonical value matches;
raw JSON whitespace/key order does not define new target identity. The original
owner decides default/null/absent/empty/omitted equivalence or distinction.
Malformed targets retain owner validation errors; a valid mismatch is distinct.

Exact pure-API `ValueError` messages are:

```text
assessment must be a SuppliedAssessment
reviews must be a tuple
reviews must contain at most 32 supplied reviews
review at index N must be a SuppliedAssessmentReview
review at index N target does not match requested assessment
P09 review inspection output budget exceeded (16 MiB)
```

`N` is zero-based. Existing Pydantic/owner/P08 inspection errors retain their
source. No exception wrapper erases that distinction.

Order, contrary prose, identical supplier labels and complete duplicate records
survive. Display positions are not identity, priority or independent evidence.
Empty reviews do not imply unknown, unsupported, negative or successful review;
explicit statements containing those words remain separate opaque records.
There is no conflict detection, voting, latest-wins, withdrawal or supersession.

Scope is a declaration, not verified coverage. No structured review-to-material
field exists: names and locators in review text are prose, even if absent from
the target inventory. The target's durable references remain declarations. No
material bytes are fetched or proved available/examined. A same-value match does
not establish freshness, withdrawal status or later-policy applicability.

## Complete view

Each new string is recoverably ASCII-escaped JSON, including DEL as `\u007f`.
Control/bidi/command/URL text remains inert. The output uses LF and one final LF:

1. `Supplied assessment reviews - non-authoritative inspection`
2. `Complete target assessment:`
3. The unchanged public `inspect_assessment` complete target view exactly once,
   including its existing final LF, without a second quotation or private renderer.
4. `Supplied review records: N`
5. Empty: `Reviews: none supplied; no review judgment inferred`. Otherwise:
   `Review targets: all supplied records match the complete requested assessment value`,
   then these lines for every one-based position K, with Q indicating JSON quotation:

```text
Review K
Supplied scope (coverage declaration only): Q(scope)
Supplied judgment: Q(judgment)
Supplied record supplier: Q(attribution.supplier)
Supplied rationale: Q(attribution.rationale)
```

Every output ends with these literal lines:

```text
Scope is supplied prose; structural checks do not verify examination coverage.
Attribution is supplied: the record supplier label need not name the reviewer; reviewer identity and independence are not established.
Material names in review text are prose; no material selection, access or support is validated.
A matching value does not establish freshness, withdrawal status or later-policy applicability.
No authentication, approval, score, winner, review lifecycle or persistence is inferred.
End of complete review view
```

There are no blank separator lines, streamed partial successes or truncation.
Empty reviews have no all-targets-matched line. Complete independently authored
Pattern and Invariant views and inputs live in
`tests/test_assessment_review_inspection.py`; they were bound to the accepted v2
Appendix A before the new renderer existed, not generated as golden output.

## Finite composition and limits

The conservative complete-display bound is:

```text
8 MiB + 32 * (4096 + 4096 + 4096 + 128) * 12 + 8192
= 13,164,544 bytes < 16,777,216 bytes
```

This assumes the P08 8 MiB view is embedded once without requotation, at most
12 ASCII bytes per Unicode code point for new text, and the exact labels/quotes/
LFs fit the 8192-byte allowance. Their independent counts are 4904 bytes at 32
records and 689 at zero. The actual UTF-8 output cap is checked before return;
the inherited P08 output refusal is preserved.

Each complete P08 assessment retains its 8192-node, 512-object, 131072-string-code-
point and depth-32 normalized bounds, plus 64 conditions, 128 materials, 128
opinions and 64 conflicts. A review wrapper adds 12 nodes, two objects, at most
12416 prose code points and 51 field-name code points; the child is one level
deeper. Up to 33 logical complete targets across the requested argument and 32
records compose to finite value size; no second generic budget walker is needed.

Each review target is revalidated and compared in full, and the public P08
inspector revalidates its target/basis again. These repeated bounded traversals
have a cost; no object-identity trust or speculative cache bypasses them.
Display and normalized-value bounds are not raw-parser, peak-memory, CPU,
wall-clock or operating-system guarantees.

## Preserved owners and inherited obligations

The source-qualified original records remain in these immutable owners:

| Primary owner | Selected original entries |
| --- | --- |
| `reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json` | `/deferred_register/items/11`, `/12`, `/14`, `/17`, `/20`, `/21` |
| `reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json` | `/deferred_register/items/20`, `/21`, `/22`, `/23`, `/35` |
| `reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json` | `/deferred_register/items/24`, `/25`, `/26`, `/27`, `/28` |
| `reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure/closure.json` | `/deferred_register/entries/5` |

Their original subjects are not narrowed to generic contracts. P00 confidence
requires multiple reviewed cases and explicit design before model definition;
claim-review-state retains its explicit lifecycle/multiple-case condition and
prohibition on treating case-local labels as production authority. Historical
actor/review completeness and stale-cache causation remain unknown with their
original direct-evidence and before-conclusion restrictions. P01 keeps original
operational-completion conditions; P02 keeps its original
`S1.P02.S07_phase_closure` decision points; P03's absent consequence/deadline
fields are not invented.

The selected S07 reviewed-interpretation layer still separates interpretation
identity, producer/reviewer, evidence and timestamps from source events; later
review/supersession must preserve prior versions. S08 confidence/review/extended
supersession stays with P09. P08 attribution already exists and is reused here;
this does not complete those broader responsibilities. P07/P08 empirical unknowns
keep their own owners, consequences and decision points.

All 28 pre-S01 production files, P08 format/file APIs/CLI and package-root exports
are unchanged. Only the two new modules join the production inventory. Current
lifecycle expectations remain in their existing test owner; the exact old P08
handoff node remains a meaningful check of sealed history, separate from current
P09 active/S01-complete/no-successor authorization. No corpus root or dependency
is added. Runtime/package/installed and publication evidence remain separately
recorded outcomes, not self-certified contract facts.
