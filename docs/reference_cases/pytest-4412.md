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
implementation remains deferred to its preserved future owners.

## S1.P00.S10 Integration and Phase Closure

`S1.P00.S10` publishes the case-specific phase-closure layer at
`reference_corpus/pytest-4412/closures/s1-p00-phase-closure/`. Its canonical
JSON directly locks all 17 immutable S04-S08 files; its exact sidecar locks
the JSON; and its Markdown is a synchronized derived view. The append-only
chain remains acquisition, correction, case, gap analysis,
identity/revision/provenance decision, snapshot/compatibility decision,
deterministic tests, and phase closure. No earlier layer is rewritten.

The S09 tracked tests remain active. The S10 tests independently lock the new
closure bytes, replay the upstream locks and evidence pointers, prove ledger
ordering and chain acyclicity, validate all exit criteria and deferred owners,
and reject bounded corruptions. Offline wheel and sdist inspection continues
to exclude the full reference corpus and retained historical LICENSE.

P00 establishes that stable identity differs from mutable aliases, Git object
identity differs from revision role, source identity differs from provenance,
exact bytes differ from normalized representations, correction is append-only,
negative evidence is first-class, and deterministic offline replay is
practical. It does not generalize the single case to private, enterprise,
multi-provider, non-Git, or cross-repository behavior, and it does not define
a production Evidence Envelope, reader/writer/migration contract, persistence,
ingestion, retrieval, graph, transfer, model-provider, or RAG implementation.

The closure carries 25 normalized deferred semantic subjects with valid
immediate and preserved Phase owners while retaining every still-live S07 and
S08 source reference. `S1.P01` is eligible to begin with identity primitives
only, but it remains not started. The closure is not a universal phase-closure
schema or a production API.

The four commit, one tree, and four blob Git SHA-1 values already retained by
the case now serve as the nine canonical S1.P02.S01 Git object identity test
vectors. The retained-artifact SHA-256 remains a separate artifact digest; it
is not reinterpreted as Git object identity, and the pytest #4412 corpus is
unchanged.

S1.P02.S02 adds the four context-relative revision roles and an ordered
commit-parent topology record. The canonical roles bind base
`4c9cde74ab40027b5761ab9e002af116a4a20df3`, head
`690a63b9218f72662cd3a67c6c200b758c88ce12`, merge first parent
`5fab0ca3127bc895b611cc03bb3af1ebf9a0dbed`, and merge
`10cdae8e38ec448b7133cf163dca587ad806d262` to separate commit identities.
The merge topology preserves parents in exact order: first
`5fab0ca3127bc895b611cc03bb3af1ebf9a0dbed`, then
`690a63b9218f72662cd3a67c6c200b758c88ce12`. The recorded base remains
distinct from parent zero. These internal semantic records add no repository,
ref, path, provenance, or graph claim, and the pytest #4412 corpus remains
unchanged.

S1.P02.S03 uses the locked case without fabricating a complete canonical ref
observation. The corpus directly retains ref lexeme `starred_with_side_effect`
with head SHA `690a63b9218f72662cd3a67c6c200b758c88ce12`; the later head-ref
deletion is separately observed. Treating that SHA as the former target is a
reviewed derivation over those observations. The original head repository
identity remains unknown, and no ref namespace is retained. Provider event
time `2018-11-18T00:17:28Z` is deletion-event evidence, not FaultAtlas
observation time. Repository- and namespace-qualified ref subjects and
observation times used by S03 tests are therefore explicitly synthetic.

S1.P02.S04 projects four canonical revision-qualified path vectors from the
locked acquisition’s directly observed head-path inventory under stable
repository identity `github` / `37489525`: `LICENSE`,
`src/_pytest/assertion/rewrite.py`, `testing/test_assertrewrite.py`, and
`changelog/4412.bugfix.rst`, each bound only to commit
`690a63b9218f72662cd3a67c6c200b758c88ce12`. Diff-header and locator
occurrences remain retained-artifact or deterministic-derivation evidence. The
qualified-path value itself claims no existence, entry kind, file mode,
blob/tree identity, content digest, ref, role, topology, coordinates, or
history. Its bounded UTF-8 path lexeme is preserved exactly without case,
Unicode, or separator normalization; non-UTF-8 Git path bytes remain
unsupported, and lexical, cross-repository, cross-revision, and SHA-256
coverage is explicitly synthetic.

S1.P02.S05 classifies the three retained-diff coordinate layers without
collapsing them. Offsets and lengths are direct exact-byte facts; old/new hunk
spans are deterministic derivations from exact unified-diff headers; and the
applicable new-file line ranges remain reviewed derived interpretation. The
three exact byte selections are `(165, 77)`, `(439, 394)`, and `(1018, 622)`
within the immutable 1640-byte diff locked by SHA-256
`dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312`.
Their artifact line spans are respectively `6–7`, `12–21`, and `26–45`, using
one-based inclusive lines; byte selections use zero-based half-open spans.
UTF-8 and LF describe the retained diff representation. The reviewed
revision-line vectors remain `1–1`, `946–950`, and `416–427`; they are not
relabelled as raw provider facts. Locator records do not prove existence,
applicability, role, relationship, or history, and the artifact parent lock is
not an Evidence Envelope or production reader.

S1.P02.S06 publishes a versioned, internal, source-only revision and locator
contract corpus with valid, invalid, and exact-replay vectors kept separate.
The replay vectors reproduce the retained artifact bytes, selected-byte
digests, exact unified-diff headers, and deterministic old/new hunk spans
offline. Reviewed applicable-line ranges remain separately classified as
reviewed derived interpretation and are not stored as production applicability
semantics. The corpus adds no production reader, locator resolver, persistence
contract, or public API; S1.P02.S07 Phase closure is not included.

`S1.P02.S07` publishes the internal, case-calibrated revision/locator Phase
closure at
`reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/`
without rewriting the canonical pytest #4412 artifacts or the immutable S06
contract corpus, and without adding production revision/locator behavior, a
corpus reader, locator resolver, Evidence Envelope, persistence contract, or
public API. Current status: the case-calibrated `S1.P01` Identity Primitives
Phase is complete. `S1.P02` is complete and `S1.P02.S01` through
`S1.P02.S07` are complete. `S1.P03` is active: `S1.P03.S01` is complete,
`S1.P03.S02` is complete, `S1.P03.S03` is complete, `S1.P03.S04` is complete,
`S1.P03.S05`, `S1.P03.S06`, and `S1.P03.S07` are complete. `S1.P03.S08` is
next and not started, and `S1.P03.S09` is not started.

## S1.P03.S01 Retrieval Request Identity and Authority Foundation

The locked case supports 32 canonical request IDs, but zero canonical full
request references. The S01 assurance coverage therefore uses two explicitly
synthetic full request references, one for GET and one for POST. The observed
request-method vocabulary is GET-only; POST remains synthetic and is not
relabelled as an observation.

For each canonical request, run ID, ordinal, and request-start time are
directly retained. The lowercase `get` and the query-free route path are
deterministic projections from the retained uppercase method and safe request
target. The retrieval authority is locked at the case level, but the immutable
original request records do not bind it per request. S01 consequently does not
fabricate canonical authority-qualified request references.

## S1.P03.S02 Request Controls and Response Representation Observations

The locked acquisition directly supports request media, API version, response
completion, status, observed media, and null content encoding as separate
primitive or partial facts. Ordinal 32 records requested
`application/vnd.github.raw+json`, observed `text/plain`, and the ordered
`charset=utf-8` parameter. This mismatch is preserved without reconciliation.

No immutable request record contains structured `query_parameters` or an
explicit response-representation state. S02 therefore claims no canonical full
request-controls or response-observation model: complete examples are clearly
synthetic, while canonical tests remain bound to exact source pointers and only
construct directly supported request IDs and primitives. GraphQL-compatible
POST remains synthetic because all retained original and supplemental requests
are GET.

The internal S02 models preserve ordered duplicate query names, keep requested
and observed media distinct, require strict asserted-UTC response completion,
and link an observation to exactly one request ID. They retain no response body
bytes, length, digest, arbitrary headers, exact artifact, acquisition run,
adapter, or Evidence Envelope. Legacy `ArtifactSnapshot` remains unchanged.

## S1.P03.S03 Exact Retained Artifacts and Digest Scope

The locked acquisition directly supports two exact retained-artifact records.
Request ordinal 30 retained the 1,640-byte `artifacts/base-to-head.diff` HTTP
entity body with scope `github-compare-diff-http-entity-body` and SHA-256
`dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312`.
Request ordinal 32 retained the 1,096-byte `artifacts/LICENSE` Git blob content
with scope `git-blob-content` and SHA-256
`a1ebce15afc7b5cf98c7c6de512d1959d4bf61db8c6bf2f111286d483b40a997`.
Both acquisition entries classify retention as `exact_unmodified_bytes`.

The S03 records preserve explicit SHA-256 algorithm, digest scope, exact byte
length, and request linkage. Request identity, response media, source and Git
identity, and storage location remain outside exact artifact identity. The
LICENSE Git blob SHA-1 remains independently verified as
`629df45ac405532c107eb233217bc2ac1ad70c88`; it is not a field of the S03
artifact model.

The production records are metadata-only and perform no artifact I/O. They
embed no payload bytes or text, add no storage reader or writer, do not adapt
legacy `ArtifactSnapshot`, and do not introduce transformation, completeness,
or Evidence Envelope semantics.

## S1.P03.S04 Acquisition Runs and Evidence Membership

The canonical acquisition directly supports one terminal run with ID
`run-0001-s04-v1-base-4c9cde74-head-690a63b9`, explicit status `complete`,
start `2026-07-24T11:03:15.269222Z`, and final acquisition seal
`2026-07-30T08:28:22.796982Z`. The final seal is the published assurance seal;
the older `2026-07-24T11:03:31.873934Z` value remains prior reconciliation
state and is not substituted for it.

The run contains 32 contiguous request memberships whose existing composite
request identities use the common run ID and ordinals `1` through `32` in
tuple order. The immutable source does not support complete canonical request
references, controls, or response observations, so those optional membership
components remain `None` rather than being reconstructed from partial facts.

The declared exact-retention policy and inventory jointly support known-empty
tuples for ordinals `1` through `29` and `31`. Ordinal `30` contains only the
1,640-byte compare diff identity with scope
`github-compare-diff-http-entity-body` and SHA-256
`dca87a4df1edb2d1acb3fc821724483ee874c2feba6525b2c21e79cb3e8f7312`;
ordinal `32` contains only the 1,096-byte LICENSE identity with scope
`git-blob-content` and SHA-256
`a1ebce15afc7b5cf98c7c6de512d1959d4bf61db8c6bf2f111286d483b40a997`.
Here `()` means no retained exact artifact under this run's declared policy;
it does not claim that no real-world evidence or response representation
existed. `None` remains a distinct unknown membership state.

Terminal status is explicit and does not infer historical or provider
completeness, optional-component population, transformations, corrections,
supersession, omissions, publication provenance, storage, or envelope
semantics. Those relationships remain outside S04 membership; S05 models them
separately without changing the canonical run or any S04 membership fact.

## S1.P03.S05 Transformations, Corrections, and Supersession

S05 adds strict, path-free durable-record references that identify exact bytes
by declared format, version, canonicalization, SHA-256 digest, and byte length.
Transformations relate exact-artifact or durable-record subjects through
ordered inputs and outputs while keeping operation, operation version,
lossiness, and reversibility explicit. A transformation record describes a
derivation only: it executes no operation and neither mutates nor replaces an
input.

Correction and supersession are separate explicit durable-record
relationships. A correction is additive and preserves both its target and its
distinct correction record; it does not imply supersession. A supersession
identifies distinct prior and succeeding records without deleting the prior
record, selecting a global current value, or implying migration.

The canonical pytest #4412 replay constructs exactly one correction. Relation
`s04-c01-acquisition-closure` links the authoritative 61,283-byte acquisition,
SHA-256 `1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318`,
to the distinct 60,832-byte correction addendum, SHA-256
`44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2`,
at the correction's directly observed creation time
`2026-07-30T19:17:09.655780Z`. The acquisition remains authoritative and
accessible; C01 neither replaces nor supersedes it.

Both retained artifacts have empty source transformation arrays, so canonical
transformation count remains zero. No durable-record supersession is observed,
so canonical supersession count also remains zero. The unpublished
pre-publication candidate rewrite remains a recorded procedural immutability
nonconformance, not a fabricated transformation or supersession precedent.
Positive transformation and supersession examples are explicitly synthetic.

S05 introduces no migration, completeness, omission, publication provenance,
storage, persistence, reader, writer, adapter, or Evidence Envelope semantics.
Production records perform no I/O, legacy `ArtifactSnapshot` remains unchanged,
and S05 does not begin S06. `S1.P03.S06` and `S1.P03.S07` are complete;
`S1.P03.S08` is next and not started, and `S1.P03.S09` is not started.

## S1.P03.S06 Completeness, Omissions, and Publication Provenance

S06 adds strict internal completeness records whose meaning is bounded by an
explicit evidence scope. Acquisition-run terminal status remains a separate
fact and does not imply evidence completeness. The canonical assessment has ID
`s04-c01-declared-evidence-scope`, scope ID
`pytest-4412-s04-declared-retention-scope`, assessed time
`2026-07-30T19:17:09.655780Z`, and status
`scope_satisfied_with_declared_omissions`. Its subject is the published
acquisition durable-record reference.

The canonical requirement order is:

1. `retained_compare_diff`
2. `retained_historical_license`
3. `issue_body`
4. `issue_comment_bodies`
5. `issue_timeline_nested_prose`
6. `pr_body`
7. `pr_comment_bodies`
8. `pr_timeline_nested_prose`
9. `review_prose_except_exact_empty_state`
10. `inline_review_comment_bodies`
11. `commit_messages_names_and_emails`
12. `changed_file_patch_fields`
13. `complete_changed_file_bytes`
14. `raw_provider_json`
15. `transient_pr_diff_bytes`
16. `incidental_personal_profile_fields`
17. `credentials_tokens_and_local_paths`

The first two requirements are `satisfied` and cite the acquisition durable
record. The final fifteen are `intentionally_omitted`, retain omission IDs of
the form `s04-c01.omission.<requirement_id>`, and use reason
`declared-retention-policy`. Each structured omission cites the correction
durable record as its structured source and the acquisition durable record as
the supporting original declaration. No omitted content is copied into an
omission or completeness record.

The acquisition durable record has format `faultatlas-acquisition`, version
`1`, canonicalization `json-sort-keys-compact-utf8-lf-v1`, byte length `61283`,
and SHA-256
`1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318`.
The correction durable record has format
`faultatlas-pytest-4412-acquisition-closure-addendum`, version `1`, the same
canonicalization, byte length `60832`, and SHA-256
`44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2`.

Publication provenance uses stable FaultAtlas repository identity provider
`github` plus provider repository ID `1303365003`; a mutable repository alias
is not publication identity. Acquisition publication
`s1-p00-s04-acquisition-publication` has the acquisition durable record above
as its immutable subject and records PR `#9`, reviewed head
`32f51f569ec554573f29bfa4d49b4f9d40d555c7`, reviewed tree
`fffb04451520453cd00b4c2fc4acf1edd2147d5e`, squash revision
`fb9b7061c2cf70bb6d4bdceb8fd023c2bfbce32b`, published tree
`fffb04451520453cd00b4c2fc4acf1edd2147d5e`, and publication time
`2026-07-30T08:38:04Z`. Its successful PR check is workflow `CI`, context
`validate`, event `pull_request`, run `30527236496`, job `90820902687`, attempt
`1`, at the reviewed head. Its distinct successful natural-main check is
workflow `CI`, context `validate`, event `push`, run `30527462427`, job
`90821631028`, attempt `1`, at the squash revision.

Correction publication `s1-p00-s04-c01-correction-publication` has the
correction durable record above as its immutable subject and records PR `#10`,
reviewed head `60400fcb301e108dbd14477ec6bb30b42157f12d`, reviewed tree
`c50f510c38bb2f56c0b38f14b9f8cb7a09075703`, squash revision
`8ece1cfa49c718345028bc6d03aca5e4fcdf434c`, published tree
`c50f510c38bb2f56c0b38f14b9f8cb7a09075703`, and publication time
`2026-07-30T19:42:46Z`. Its successful PR check is workflow `CI`, context
`validate`, event `pull_request`, run `30575877780`, job `90983907152`, attempt
`1`, at the reviewed head. Its distinct successful natural-main check is
workflow `CI`, context `validate`, event `push`, run `30576009699`, job
`90984355320`, attempt `1`, at the squash revision.

Both publications use method `protected_pull_request_squash_merge`. For each,
reviewed head and squash revision remain distinct while reviewed and published
trees are explicitly equal. PR CI and natural main CI remain separate checks.
Publication does not mutate, correct, transform, or supersede its
durable-record subject and creates no latest or current pointer.
The publication records contain no branch name, machine-local path, raw URL,
actor profile, credential, review prose, payload, or storage location.

Complete with declared omissions means only that every requirement in this
declared 17-requirement scope has a controlled outcome. It does not establish
complete provider history or the absence of deleted, edited, hidden, private,
or permission-filtered records. S06 adds no reader, writer, storage,
persistence, migration, adapter, or Evidence Envelope, and production code
performs no I/O. No publication provenance is asserted for S06 itself.
`S1.P03.S06` is complete.

## S1.P03.S07 Evidence Envelope Composition and Legacy Adapter

S07 adds the strict, frozen, in-memory `EvidenceEnvelope` composition model over
existing typed S01-S06 records without inheritance, flattening, persistence
closure, or cross-layer inference. Its seven component inventories are
`legacy_snapshots`, `request_memberships`, `acquisition_runs`,
`transformations`, `record_relationships`, `completeness_assessments`, and
`publications`. For each inventory, `None` means that the envelope does not
represent that component inventory, while `()` means known empty only inside
this envelope composition. The two states remain distinct in semantic JSON,
and neither claims global or historical absence.

The canonical current P03 envelope has `legacy_snapshots=None`,
`request_memberships=None`, one-element `acquisition_runs`,
`transformations=()`, one-element `record_relationships`, one-element
`completeness_assessments`, and two ordered `publications`. It contains exactly:

1. acquisition run `run-0001-s04-v1-base-4c9cde74-head-690a63b9`;
2. zero canonical transformations;
3. correction `s04-c01-acquisition-closure`;
4. completeness assessment `s04-c01-declared-evidence-scope`; and
5. publication `s1-p00-s04-acquisition-publication` followed by publication
   `s1-p00-s04-c01-correction-publication`.

The nested values remain the exact standalone records. The envelope has no
envelope ID, does not require referenced durable bytes to be embedded, and is
not declared canonical durable bytes. No transformation, supersession,
precedence, latest or current state, source identity, or other relationship is
inferred from composition. No publication provenance is asserted for S07
itself.

Legacy `ArtifactSnapshot` v1 remains unchanged behind the outer envelope
wrapper. The explicit adapter ID is
`legacy-artifact-snapshot-v1-envelope-adapter`, and its version is `1`.
Wrapping one validated legacy snapshot preserves that exact source snapshot,
sets `legacy_snapshots` to the one-element tuple, leaves every modern inventory
as `None` rather than `()`, and returns `losslessly_mappable` with no reasons.
The adapter does not resolve the legacy `SourceLocator` or fabricate stable
repository identity, retrieval authority, request or response facts, exact
artifact identity, completeness, transformations, or publication provenance.

Projection back to legacy v1 is explicit and fail closed:

- exactly one legacy snapshot with every modern inventory `None` is
  `losslessly_mappable` and returns that exact snapshot;
- exactly one legacy snapshot with any modern inventory present, including an
  explicitly known-empty `()`, is `partially_mappable`, returns no snapshot,
  and reports `modern_components_not_representable`;
- no represented legacy snapshot (`None` or `()`) is `not_mappable`, returns no
  snapshot, and reports `legacy_snapshot_absent`; and
- multiple legacy snapshots are `not_mappable`, return no snapshot, and report
  `multiple_legacy_snapshots_not_representable`.

The canonical current P03 envelope therefore projects as `not_mappable` with
`legacy_snapshot_absent`; no diff, LICENSE, acquisition, correction,
completeness, or publication fact is coerced into a legacy snapshot. S07 adds
no migration, persistence, storage, reader, writer, canonical envelope bytes,
format registry, repository snapshot, confidence or review, contract corpus,
or service API. `S1.P03.S07` is complete, `S1.P03` remains active,
`S1.P03.S08` is next and not started, and `S1.P03.S09` is not started.
