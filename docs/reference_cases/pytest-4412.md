# pytest #4412 / #4414 Reference-Case Selection and Capture Policy

## Status and Slice Identity

This is the reviewed S1.P00.S02 decision record for the first FaultAtlas
canonical reference case. It records selection and capture-policy decisions;
it is not captured evidence, a capture manifest, a production schema, or a
public API.

This record authorizes no external acquisition or corpus creation. The
selected case is bounded to public GitHub and Python evidence. Current
FaultAtlas domain models remain provisional and internal.

- Stage: S1 — Canonical Knowledge Contracts
- Phase: S1.P00 — Reference-Case Calibration & Stage 1 Entry
- Slice: S1.P00.S02 — Reference-Case Selection and Capture Policy
- Decision: select pytest-dev/pytest Issue #4412 and PR #4414

## Scope and Explicit Non-Goals

This Slice fixes the selection rationale, verified identity chain, evidence
boundaries, sanitization rules, conservative rights policy, completeness
vocabulary, conceptual manifest requirements, and relationship to the current
internal models.

It does not acquire or retain provider bytes, create a reference corpus,
implement a manifest or schema, change SourceLocator or ArtifactSnapshot,
execute source material, add tests, choose persistence or graph technology,
implement search or RAG, select a model provider, or begin S1.P00.S03.

All external material named here remains untrusted data. Source links and
identifiers do not authorize executing commands, code, patches, configuration,
or binaries found in those sources.

## Selection Criteria

A suitable first case must provide:

- a bounded, publicly inspectable fault-to-fix chain;
- stable and scoped identities that expose real identity distinctions;
- immutable revisions and revision-qualified file evidence;
- a concrete implementation change and regression proof;
- enough discussion to distinguish observation from derived interpretation;
- meaningful negative evidence and an explicit resolution sequence;
- usable rights and sanitization boundaries without full-discussion archival;
- a technical invariant that can later be evaluated for transfer; and
- enough complexity to expose current contract gaps without implying universal
  semantics.

pytest #4412/#4414 meets these criteria while remaining small enough for
deterministic review and future replay.

## Verified Source-Chain Identities

### Repository

| Fact | Verified value |
|---|---|
| Provider host | github.com |
| Stable repository ID | 37489525 |
| Observed alias | pytest-dev/pytest |
| Current default branch | main |
| Historical PR base ref | master |
| Historical repository default branch | unknown |

The current default and historical PR base ref are distinct observations.
Available evidence does not establish the repository's historical default
branch.

### Issue and comments

| Fact | Verified value |
|---|---|
| Issue number | 4412 |
| Global REST ID | 381866787 |
| Created | 2018-11-17T14:16:11Z |
| Closed | 2018-11-18T00:17:25Z |
| Updated | 2018-11-18T22:33:09Z |
| Current-visible comments | 8 |

The complete current-visible Issue comment inventory is:

| Comment ID | Derived technical role | Discussion disposition |
|---|---|---|
| 439627709 | Preliminary diagnostic observation | Summary only |
| 439636987 | Duplicate-evaluation diagnosis and reduced reproduction | Summary only |
| 439638666 | Explicit link to PR #4414 | Necessary attributed short excerpt may be retained later |
| 439692236 | Nontechnical acknowledgement | Prose omitted; metadata retained |
| 439722704 | Apparent post-fix failure | Summary only; linked material remains external |
| 439729234 | Independent fresh-run success | Summary only |
| 439731167 | Stale rewritten-bytecode hypothesis | Necessary attributed short excerpt may be retained later |
| 439732047 | Fresh-clone and cache-clearing resolution | Necessary attributed short excerpt may be retained later |

These role labels are derived interpretations, not provider-supplied roles.

### Pull request and review

| Fact | Verified value |
|---|---|
| PR number | 4414 |
| Global REST ID | 231744068 |
| Created | 2018-11-17T18:44:04Z |
| Merged and closed | 2018-11-18T00:17:25Z |
| Updated | 2018-11-18T16:36:36Z |
| Approval review ID | 176071572 |
| Approval submitted | 2018-11-17T23:54:20Z |

The top-level PR comment inventory is 439644573, 439686203, and 439706171.
The first is Codecov bot output; the latter two are social discussion. Their
bodies are omitted while their source identities and omission reasons remain
required metadata.

Approval 176071572 is tied to the patch/head commit. Its body is exactly empty
and contains no written rationale. The approval decision must not be expanded
into rationale that the source did not provide.

### Revision chain and lifecycle

| Revision role | Full SHA | Observed time or qualification |
|---|---|---|
| Recorded PR base | 4c9cde74ab40027b5761ab9e002af116a4a20df3 | 2018-11-17T16:20:29Z |
| Patch/head commit | 690a63b9218f72662cd3a67c6c200b758c88ce12 | 2018-11-17T18:42:51Z |
| Merge commit | 10cdae8e38ec448b7133cf163dca587ad806d262 | 2018-11-18T00:17:24Z |
| Merge first parent | 5fab0ca3127bc895b611cc03bb3af1ebf9a0dbed | Commit-qualified observation |

The recorded PR base and merge first parent are different because the base
advanced before merge. Neither SHA replaces or invalidates the other.
Patch/head and merge commits are separate evidence objects. The PR merge event
occurred one second after the merge commit timestamp.

Branch names are mutable observations, not immutable revisions. The former
head ref was deleted, but deletion of the ref does not invalidate the
preserved patch/head SHA.

### Relevant files, fixed blobs, and license

| Revision-qualified path | Fixed blob |
|---|---|
| src/_pytest/assertion/rewrite.py | 7b9aa5006544c160f584f1e8fc3f7771ef6e5e99 |
| testing/test_assertrewrite.py | a02433cd62ab19ebb54b42b50c299e59e48de00e |
| changelog/4412.bugfix.rst | 7a28b610837873eeff2a16582de6d5a035820552 |

The historical license blob at the patch/head revision is
629df45ac405532c107eb233217bc2ac1ad70c88.

## Canonical-Case Decision and Limitations

pytest #4412/#4414 is the first canonical FaultAtlas reference case because it
provides:

- stable repository ID versus mutable alias;
- repository-scoped numbers versus global object IDs;
- Issue, PR, comment, review, commit, blob, file, and diff identities;
- recorded base, patch head, advanced merge parent, and merge commit;
- exact implementation, regression-test, changelog, diff, and license
  evidence for later separately authorized capture;
- approval tied to the exact patch head;
- an apparent-failure, independent-success, stale-cache-hypothesis, and
  resolution sequence; and
- the bounded transferable invariant that transformation or instrumentation
  must preserve evaluation count and execution order for side-effecting
  expressions.

The case does not establish universal or multi-provider identity,
private-source behavior, repository rename or transfer history, GitHub
Enterprise behavior, complete edit or deletion history, multi-language
generality, or persistence, graph, search, RAG, and model contracts.

## Capture Taxonomy

| Category | Authority boundary | Exact bytes | Digest | Transformations | Required provenance | Future model input | Placement |
|---|---|---|---|---|---|---|---|
| Source object | Provider-hosted logical identity and observed state | Not applicable | Not required for identity alone | Identity values are not rewritten | Provider, stable ID, scoped number, repository, canonical URL, observation context | Only through a representation | Future identity layer; only a GitHub Issue fits current SourceLocator |
| Source representation | What the provider returned at a stated acquisition time, not eternal truth | Required only when claimed as raw | Required when raw bytes are retained | None when labeled raw | Endpoint, API/media version, status, acquisition time, pagination, limitations | Eligible as bounded untrusted input | ArtifactSnapshot only when its Issue/JSON constraints fit |
| Captured artifact | Exact bytes retained by FaultAtlas | Required | Required | Not allowed; a change creates a new artifact | Revision-qualified source, media type, acquisition procedure, license | Eligible as bounded untrusted input | Later artifact or evidence layer |
| Sanitized capture | Transformed bytes plus their declared ledger, not the original | Sanitized bytes required | Sanitized digest required; original digest when permitted | Only deterministic, ledgered transformations | Source representation, procedure version, every transformation | Eligible only with sanitized status | ArtifactSnapshot may flag redaction; ledger belongs outside it |
| Normalized metadata | Deterministic derived field representation, never provider bytes | Canonical persisted bytes required when durable | Required when durable | Versioned normalization allowed | Field mapping, source identities, normalization version | Eligible with derived label | Later manifest or outer evidence layer |
| Derived interpretation | Human- or model-produced summary, claim, invariant, relationship, or classification | Source bytes are not implied | Required only for a durable interpretation artifact | Correction creates a new version | Producer, procedure/model, time, cited evidence, review state | Eligible with derived label | Later claim, invariant, confidence, or review layer |
| Negative evidence | Absence, rejection, supersession, failure, uncertainty, or not-applicable state within a bounded procedure | Depends on supporting carrier | Depends on supporting carrier | The underlying observation is not rewritten | Searched surface, procedure, completeness, supporting sources | Eligible with boundary and uncertainty labels | Later outer relationship or claim layer |

Normalized connector output is normalized metadata or a normalized source
representation. It is never labeled raw provider bytes.

## Inclusion and Exclusion Policy

### Required exact capture in a later separately authorized Slice

- unified base-to-head diff;
- bounded implementation hunk;
- bounded regression-test hunk;
- bounded changelog hunk; and
- historical MIT license bytes.

The bounded hunks are locators into the unified diff, not authorization to
duplicate complete changed files.

### Required metadata

Future capture retains repository, Issue, PR, comment, review, commit, blob,
branch/ref, canonical URL, and provider timestamp metadata. It also retains
the exactly-empty approval-body state and an omitted-source inventory with an
omission reason for each excluded source.

### Discussion treatment

Discussion is represented by derived summaries by default. Only necessary,
attributed short excerpts may be retained. The operational retention cap is
25 words per discussion object. This operational limit is not a legal
safe-harbor claim.

### Explicit omissions

The case omits avatars, unnecessary emails, full terminal transcripts, local
filesystem paths, memory addresses, token-like query values, Codecov body and
bot payloads, social or praise prose, screenshots, linked SymPy file
contents, and full changed files.

External linked material remains link-only unless a later Gate separately
authorizes and verifies its identity, necessity, rights, and sanitization.
Intentional omission is recorded as omission, not unavailability.

## Deterministic Sanitization and Transformation-Ledger Requirements

Apply transformations in this order:

1. token and query values;
2. email addresses;
3. absolute local-user paths;
4. contextual memory addresses; and
5. separately approved incidental personal material.

Use the marker `[FAULTATLAS_REDACTED:<TYPE>:<NNNN>]`.

- Number distinct values by first occurrence per type and artifact.
- Repeated identical values reuse the same marker.
- A pre-existing marker collision is a stop condition.
- Repository-relative paths remain when technically relevant.
- Commit and blob SHAs are identities, not memory addresses.
- Evidence strings receive no Unicode normalization.
- Exact captures preserve whitespace, Unicode, ordering, and line endings.
- Sanitized captures preserve all non-target content and require their own
  SHA-256 digest.
- Retain the original digest when legally and operationally permitted.
- Normalized metadata is derived, versioned, and never raw. A deterministic
  normalized JSON representation uses UTF-8 without a byte-order mark,
  lexicographically ordered object keys, source order for arrays, LF line
  endings, and one trailing LF.

Every future transformation requires a ledger entry that identifies the
source object, affected field or original byte range, transformation type,
reason, replacement marker, original digest when permitted, sanitized digest,
procedure/tool and version, and UTC transformation time. This record defines
requirements only; it does not design the ledger schema.

## License, Attribution, Privacy, and Discussion-Prose Policy

Revision-qualified repository code, tests, diff, changelog, and license are
handled under the historical MIT license. Any later exact retention must
preserve the revision, canonical source, license identity, and required
copyright and permission notice.

Issue, PR, comment, and review prose is not presumed covered by the repository
MIT license. Discussion retention therefore defaults to metadata, canonical
links, summaries, and minimal attributed excerpts. Public account handles and
provider user IDs are retained only where attribution or relationship
identity requires them.

Full discussion archival or model-training use requires later legal and
product-owner review. External SymPy material remains link-only. These are
conservative project rules, not broader legal conclusions.

## Completeness, Pagination, and Edit-History Policy

| State | Meaning |
|---|---|
| complete | Every component declared by a bounded acquisition procedure was acquired; this does not assert complete provider history |
| partial | At least one known expected component is absent |
| truncated | A known provider, item-count, or byte boundary cut the representation |
| redacted | Retained content was deliberately transformed |
| unavailable | An object is known, but no representation was obtained |
| deleted | Explicit provider evidence reports deletion or a tombstone |
| inaccessible | Access is denied or requires unavailable authorization |
| unknown | Available evidence cannot establish the state |
| pagination-complete | Every page in the declared endpoint was traversed and no next page remains, with counts reconciled where available |
| pagination-incomplete | A next page remains, traversal stopped, or a request failed |
| edit-history-unknown | Current content is available but complete historical versions were not exposed |

These values may compose.

The verified current-visible surfaces are:

- Issue comments: pagination-complete, 8/8;
- Issue timeline: pagination-complete for the inspected 24-event surface;
- PR top-level comments: pagination-complete, 3;
- reviews: pagination-complete, 1;
- inline review comments: pagination-complete, 0;
- PR commits: pagination-complete, 1;
- PR changed files: pagination-complete, 3; and
- unified base-to-head diff: complete for the declared comparison.

The complete discussion edit history, deleted comments not represented by
explicit provider evidence, earlier Issue and PR body versions, and
historical repository default branch remain unknown. Pagination completeness
does not prove that deleted or permission-hidden records never existed.
Intentional omission differs from unavailability.

## Proposed Manifest Field Classifications

These are conceptual fields, not schema or production type definitions.

| Conceptual field | Classification | Case-specific purpose |
|---|---|---|
| Case ID | required for this case | Stable case identity |
| Case-format version | required for this case | Version the manifest interpretation |
| Provider host | required for this case | Identify the public provider |
| Stable repository ID | required for this case | Separate repository identity from alias |
| Observed alias and observation time | required for this case | Preserve mutable alias as a timed observation |
| Source-object kinds and provider IDs | required for this case | Distinguish repository, Issue, PR, comment, review, commit, and blob identities |
| Repository-scoped numbers | required for this case | Preserve Issue and PR numbers separately from global IDs |
| Parent relationships | required for this case | Relate objects without embedding relationships in snapshots |
| Canonical URLs | required for this case | Support source verification and attribution |
| Provider timestamps and event roles | required for this case | Preserve observed lifecycle facts |
| Acquisition timestamp and procedure | required for this case | Bound every future observation |
| API and media version | required for this case | Make provider representation semantics explicit |
| Pagination and completeness | required for this case | Bound absence and collection claims |
| Base, head, merge, and merge-parent SHAs | required for this case | Preserve distinct revision roles |
| Branch/ref observations | required for this case | Record mutable refs and deletion without using them as revision identity |
| Revision-qualified file locators | required for this case | Bind path, revision, bounded location, and blob |
| Artifact paths and media types | required for this case | Locate and interpret every retained exact artifact |
| Exact-byte digests and digest scope | required for this case | Bind every retained artifact digest to declared bytes |
| Sanitization state and transformation records | required for this case | Record a transformation or an explicit empty state and prevent transformed bytes from being labeled raw |
| License metadata | required for this case | Preserve historical license identity and attribution |
| Omitted-source records | required for this case | Record deliberate exclusions and reasons |
| Negative-evidence relationships | required for this case | Preserve apparent failure, supersession, and resolution |
| Known contract gaps | required for this case | Carry ambiguity and unsupported surfaces forward |
| GraphQL node IDs | optional for this case | Secondary provider identity corroboration |
| Titles, labels, and byte lengths | optional for this case | Additional normalized metadata |
| HTTP cache validators | optional for this case | Strengthen acquisition replay when exposed |
| Commit-signature state | optional for this case | Not required to establish this chain |
| Formal schema and production types | deferred | Decided in later contract Slices |
| Claims, confidence, invariant, review, and transfer records | deferred | Owned by later outer semantic layers |
| Persistence, graph, retrieval, embedding, and model-routing fields | deferred | Outside S1.P00.S02 |
| Secrets, credentials, and private-source identifiers | explicitly unsupported | Public-only first case |
| Local paths or memory addresses as identities | explicitly unsupported | Incidental values are omitted or sanitized |
| Executable or binary external artifacts | explicitly unsupported | External execution is outside the trust boundary |
| Full discussion archive and linked external-file payloads | explicitly unsupported | Current conservative retention boundary |

## Relationship to Current Internal Models

SourceLocator currently expresses only a GitHub Issue locator. Its object_id
semantics remain ambiguous between a repository-scoped Issue number and a
global REST object ID. S02 records but does not resolve that ambiguity.

ArtifactSnapshot may structurally carry one compatible Issue JSON
representation when its UTF-8, media-type, size, UTC timestamp, digest, and
explicit limitation requirements are met. S02 acquires no such
representation.

ArtifactSnapshot cannot express acquisition envelopes, transformations and
their digest relationships, object relationships, revision-qualified file
evidence, license records, claims, confidence, review decisions, or transfer
analysis. Missing information is documented rather than forced into current
fields.

ArtifactSnapshot remains an immutable retrieval observation. Later outer
layers own relationships, provenance, transformations, claims, confidence,
review, and transfer.

## S1.P00.S05 Case-Manifest Publication

`S1.P00.S05` publishes the case-specific relationship layer under
`reference_corpus/pytest-4412/case/` as canonical `case.json` plus its exact
`case.sha256` sidecar. The case record directly locks both the authoritative
S04 acquisition and the append-only S04.C01 correction by path and SHA-256.
The correction supplements the acquisition; it does not replace it or create a
synthetic corrected acquisition.

The manifest owns the bounded case identity, entity registry, relationship
classification, selected chronology, negative-evidence order, final selection
linkage, and case-level gaps. It keeps `observed`,
`deterministically_derived`, `reviewed_derived_interpretation`, `hypothesis`,
`unknown`, and `unsupported` distinct. Where retained cross-reference events
omit their nested target identity, the event remains observed while the
Issue/PR pair-level linkage remains a reviewed case interpretation.

The negative-evidence lock preserves this order:

1. `439722704` — apparent failure report;
2. `439729234` — independent success report;
3. `439731167` — stale-cache hypothesis; and
4. `439732047` — resolution report.

Those roles are case-derived, not provider-authored event types. The
stale-cache explanation remains an unverified hypothesis and is not promoted
to established causation.

The bounded reviewed invariant is: “Transformation or instrumentation must
preserve evaluation count and execution order for side-effecting expressions.”
It is supported only within this reviewed case evidence. Universal pattern and
transfer status remain deferred to `S1.P07` and `S1.P08`.

This manifest format remains provisional, internal, and case-specific.
Production schemas, loaders, migrations, persistence, and public APIs are not
introduced. `SourceLocator` and `ArtifactSnapshot` remain unchanged internal
seeds whose representational gaps are recorded rather than repaired in S05.

## Known Gaps, Risks, and Stop Conditions

Known gaps and risks include:

- unresolved SourceLocator object_id meaning;
- mutable repository aliases and branch/ref observations;
- recorded PR base versus advanced merge-parent distinctions;
- normalized connector representations being mistaken for raw bytes;
- incomplete edit, deletion, rename, and historical-default evidence;
- an empty approval being expanded into unobserved rationale;
- third-party bot output being mistaken for authoritative changed-file
  evidence;
- the apparent stale-cache episode being treated as a second fix defect;
- discussion, personal, or token-like material crossing the retention
  boundary; and
- one public Python/GitHub case being generalized into universal contracts.

A later Gate must stop rather than assume if a locked identity conflicts,
public read-only acquisition cannot establish the declared surface, rights for
required exact material become unclear, sanitization destroys the technical
invariant, private access or external execution becomes necessary, or work
would require an unapproved source, test, corpus, dependency, environment,
schema, model, persistence, graph, search, RAG, or provider change.

## S1.P00.S03 Prerequisites

The next Slice is:

S1.P00.S03 — Acquisition Procedure and Capture Manifest Plan

Before retaining bytes, S03 must determine:

- the exact endpoint and read-only acquisition sequence;
- connector versus REST roles;
- API and media versions;
- pagination verification;
- observation-time recording;
- raw-response retention versus transient hashing;
- procedure and tool versioning;
- current visible-count reconciliation;
- exact later artifact boundaries; and
- rights and sanitization revalidation.

S03 is planning-only unless separately authorized otherwise. It does not
revisit case selection, and this record does not begin it.

## Primary Source Links

- [pytest-dev/pytest repository](https://github.com/pytest-dev/pytest)
- [Issue #4412](https://github.com/pytest-dev/pytest/issues/4412)
- [Issue comment 439627709](https://github.com/pytest-dev/pytest/issues/4412#issuecomment-439627709)
- [Issue comment 439636987](https://github.com/pytest-dev/pytest/issues/4412#issuecomment-439636987)
- [Issue comment 439638666](https://github.com/pytest-dev/pytest/issues/4412#issuecomment-439638666)
- [Issue comment 439692236](https://github.com/pytest-dev/pytest/issues/4412#issuecomment-439692236)
- [Issue comment 439722704](https://github.com/pytest-dev/pytest/issues/4412#issuecomment-439722704)
- [Issue comment 439729234](https://github.com/pytest-dev/pytest/issues/4412#issuecomment-439729234)
- [Issue comment 439731167](https://github.com/pytest-dev/pytest/issues/4412#issuecomment-439731167)
- [Issue comment 439732047](https://github.com/pytest-dev/pytest/issues/4412#issuecomment-439732047)
- [PR #4414](https://github.com/pytest-dev/pytest/pull/4414)
- [PR comment 439644573](https://github.com/pytest-dev/pytest/pull/4414#issuecomment-439644573)
- [PR comment 439686203](https://github.com/pytest-dev/pytest/pull/4414#issuecomment-439686203)
- [PR comment 439706171](https://github.com/pytest-dev/pytest/pull/4414#issuecomment-439706171)
- [Approval review 176071572](https://github.com/pytest-dev/pytest/pull/4414#pullrequestreview-176071572)
- [Recorded PR base](https://github.com/pytest-dev/pytest/commit/4c9cde74ab40027b5761ab9e002af116a4a20df3)
- [Patch/head commit](https://github.com/pytest-dev/pytest/commit/690a63b9218f72662cd3a67c6c200b758c88ce12)
- [Merge commit](https://github.com/pytest-dev/pytest/commit/10cdae8e38ec448b7133cf163dca587ad806d262)
- [Base-to-head comparison](https://github.com/pytest-dev/pytest/compare/4c9cde74ab40027b5761ab9e002af116a4a20df3...690a63b9218f72662cd3a67c6c200b758c88ce12)
- [Fixed implementation](https://github.com/pytest-dev/pytest/blob/690a63b9218f72662cd3a67c6c200b758c88ce12/src/_pytest/assertion/rewrite.py#L946-L950)
- [Regression test](https://github.com/pytest-dev/pytest/blob/690a63b9218f72662cd3a67c6c200b758c88ce12/testing/test_assertrewrite.py#L416-L427)
- [Changelog entry](https://github.com/pytest-dev/pytest/blob/690a63b9218f72662cd3a67c6c200b758c88ce12/changelog/4412.bugfix.rst#L1)
- [Historical MIT license](https://github.com/pytest-dev/pytest/blob/690a63b9218f72662cd3a67c6c200b758c88ce12/LICENSE)

## S1.P00.S06 Current-Contract Gap Matrix Publication

`S1.P00.S06` publishes a derived, case-grounded analytical layer at
`reference_corpus/pytest-4412/analysis/s06-current-contract-gap-matrix/`.
Canonical `gap-matrix.json` is the durable semantic authority,
`gap-matrix.sha256` locks its exact bytes, and `gap-matrix.md` is a derived
human-readable view that embeds the primary JSON digest.

The analysis directly locks these immutable inputs:

- S04 acquisition SHA-256
  `1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318`;
- S04.C01 correction SHA-256
  `44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2`;
  and
- S05 case-manifest SHA-256
  `fc1439a8f9766bdf55b95e9d63f3bf19db44da1724dfb7cd2e889771384b9efa`.

The matrix covers each of the 33 S05 entities and 53 S05 relationships
exactly once, and includes 81 explicit concept rows across identity, revision
and location, evidence representation, completeness and omission, case
semantics, and compatibility and lifecycle. Coverage uses only
`representable`, `partially_representable`, `not_representable`,
`intentionally_deferred`, and `unsupported_by_current_evidence`.

Current `SourceLocator` support remains limited to an Issue-only GitHub
identity with an ambiguous numeric `object_id`. Current `ArtifactSnapshot`
support remains limited to an Issue-bound UTF-8 `application/json` text
observation with semantic Pydantic serialization. Neither current model gains
case-relationship, revision, exact-artifact, acquisition-envelope, migration,
or persistence semantics from this analysis.

The matrix routes identity, revision, and provenance questions to S07;
snapshot-boundary and compatibility questions to S08; bounded deterministic
corpus-test obligations to S09; and integration and closure obligations to
S10. Recommended S07 and S08 defaults remain
`owner_decision_required`: S06 identifies gaps and decision pressure but does
not make those decisions or implement their outcomes.

This analytical layer is internal and case-specific. It is not a universal
production schema, loader, migration contract, persistence contract, or
public API. No production model was changed, and S07 was not started.

## S1.P00.S07 Identity, Revision, and Provenance Decision Publication

`S1.P00.S07` publishes the case-calibrated decision layer at
`reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/`.
Canonical `decision.json` is the durable semantic authority,
`decision.sha256` locks its exact bytes, and derived `decision.md` embeds the
primary JSON SHA-256
`60ecb66565525cb21a924508794635072ae50e935d4791d9d91da5b6399ce866`.

The decision record directly locks these immutable inputs:

- S04 acquisition SHA-256
  `1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318`;
- S04.C01 correction SHA-256
  `44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2`;
- S05 case-manifest SHA-256
  `fc1439a8f9766bdf55b95e9d63f3bf19db44da1724dfb7cd2e889771384b9efa`;
  and
- S06 gap-matrix SHA-256
  `55dacf5193aedc5493ac369dd0e3fb74a0f59f0c1f88bab1b625a2e4f4ff5f13`
  plus derived Markdown SHA-256
  `6a569af7f9b1c691fc397e356d365664dcc14cbebe6ae589bd4501e23ac1893a`.

For this case, stable repository identity is provider `github` plus provider
repository ID `37489525`; `pytest-dev/pytest` remains a mutable, timed alias
observation. Repository-scoped Issue and PR numbers, global REST IDs, and
GraphQL node IDs have distinct typed roles. Comments and reviews use their
provider-assigned stable IDs with explicit parent scope. A public login is
attribution metadata, not repository identity.

Git commit, tree, and blob identities are object-kind-, algorithm-, and
full-digest-qualified. Base, head, merge first parent, and merge are case roles
over commit identities, and ordered parents remain evidence-bearing. Mutable
refs are timed observations rather than immutable revisions; deleting a ref
does not invalidate its target commit. Revision-qualified paths and bounded
line, byte, and hunk locators remain separate S1.P02 concerns.

The controlled field states are `present`, `observed_null`, `missing`,
`unavailable`, `inaccessible`, `deleted`, `unknown`, `unsupported`, and
`conflict`. Source authority, repository and object identity, immutable
revision or artifact, mutable alias or ref observation, request, response,
acquisition, retained artifact, transformation, correction, case relationship,
reviewed interpretation, and FaultAtlas publication remain fourteen distinct,
non-overwriting provenance layers.

Legacy `SourceLocator` remains internal, provisional, unchanged, Issue-only,
and ambiguous: `repository` is an alias and `object_id` is not retroactively
interpreted as either a repository-scoped number or a global provider ID. The
record makes only the limited S07 observation that `ArtifactSnapshot` is not a
stable source-identity carrier. S07 left its preserve, evolve, or replace
compatibility choice to S08; the S08 publication below now resolves that
choice. No S1.P01, S1.P02, or S1.P03 production implementation is included.

## S1.P00.S08 Snapshot Boundary and Compatibility Decision Publication

`S1.P00.S08` publishes the case-calibrated decision layer at
`reference_corpus/pytest-4412/decisions/s08-snapshot-boundary-compatibility/`.
Canonical `decision.json` is the durable semantic authority,
`decision.sha256` locks its exact bytes, and derived `decision.md` embeds the
primary JSON SHA-256
`f788116f3b9ea470c370a56e55eb6f37e05be200f285ac9f2572c641215f5f40`.

The record directly locks the exact S04 acquisition and retained artifacts,
S04.C01 correction, S05 case manifest, S06 gap matrix, and S07 decision. It
also locks synchronized FaultAtlas baseline
`0a997e192583aab7c6a41bc8cb9c00909e8cbcbf`, the current source and test
blobs, and the pre-S08 governing-document blobs.

Legacy `ArtifactSnapshot` schema version 1 remains unchanged, internal, and
provisional behind a future outer compositional boundary. It remains one
Issue-bound UTF-8 `application/json` text observation under its current size,
timestamp, digest, limitation-state, and strict/frozen validation behavior.
It is not reinterpreted as a complete evidence contract.

Representation observation, normalized metadata, and retained exact artifacts
remain distinct. Exact diff and LICENSE bytes are not mappable to legacy v1;
future byte-oriented evidence must preserve arbitrary exact bytes without a
UTF-8 or JSON requirement, and every digest must declare its scope. The
controlled compatibility statuses are `native`, `losslessly_mappable`,
`partially_mappable`, `not_mappable`, `unsupported_version`, and `conflict`.

Compatibility mappings are explicit, versioned, source-preserving, and
loss-aware. Future-to-legacy projection is conditional and non-default.
Migration translates contracts, correction addresses a defect, and
supersession records scoped precedence; none may overwrite an immutable
published source.

This decision introduces no production model, adapter, reader, writer,
migration, persistence contract, public API, or universal schema. S1.P03
evidence implementation and all other preserved future-phase implementations
remain deferred.

## S1.P00.S09 Deterministic Corpus Tests

`S1.P00.S09` adds tracked, offline deterministic tests for the published
S04 acquisition, S04.C01 correction, S05 case manifest, S06 gap matrix, S07
identity/revision/provenance decision, and S08 snapshot-boundary/compatibility
decision. A test-only table independently locks all 17 accepted corpus files;
it is not derived from the sidecars at test time. The tests also replay all six
canonical JSON records and sidecars, exact diff and historical LICENSE bytes,
the append-only source-lock DAG, published evidence pointers, case integrity,
and the S05-S08 semantic boundaries.

Failure-sensitivity tests corrupt only in-memory values, temporary copies, or
synthetic archive members. They do not rewrite accepted corpus files. Actual
isolated `uv build --offline --no-create-gitignore` runs prove that wheels and
sdists exclude `reference_corpus/`, every S04-S08 corpus path, and the retained
historical pytest LICENSE while preserving the FaultAtlas project LICENSE.

S09 introduces no production corpus reader, canonicalizer, validator, schema,
adapter, migration, or model change. Comprehensive production compatibility
implementation remains deferred to its preserved future owners. S10 is the
next S1.P00 Slice and has not started.
