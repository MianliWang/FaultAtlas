# pytest #4412 / #4414 Acquisition Procedure and Manifest-Boundary Plan

## Status and Authority

This is the reviewed `S1.P00.S03` acquisition plan for the first FaultAtlas
canonical reference case. It is documentation, not executed acquisition
evidence, a production schema, or a public API. It authorizes no HTTP request,
provider-response capture, corpus creation, or byte retention.

The canonical case remains `pytest-dev/pytest` Issue `#4412` and PR `#4414`.
The existing S02 decision record remains authoritative for selection, rights,
privacy, sanitization, inclusion, omission, and completeness policy. A future
`S1.P00.S04` Gate requires a new exact path allowlist and explicit authorization
before it may make requests or retain bytes.

- Stage: S1 — Canonical Knowledge Contracts
- Phase: S1.P00 — Reference-Case Calibration & Stage 1 Entry
- Slice: S1.P00.S03 — Acquisition Procedure and Capture Manifest Plan

## Scope and Non-Goals

This record fixes the acquisition ordering, provider-representation
terminology, connector and REST responsibilities, API and media controls,
request-budget behavior, timestamps, retention classes, byte identity,
pagination, integrity checks, and the boundary between an S04 acquisition
record and the later S05 case manifest.

It does not call GitHub, capture provider responses, create a reference corpus,
compute case-artifact digests, implement a manifest or schema, change current
models, add source or tests, select credentials, or begin S04. All named
external material remains untrusted data and must never be executed.

## Governing Capture Policy

The S02 record, `docs/reference_cases/pytest-4412.md`, governs this plan. Its
locked source-chain facts include:

- stable repository ID `37489525` and observed alias `pytest-dev/pytest`;
- Issue number/global ID `4412`/`381866787` and visible comment IDs
  `439627709`, `439636987`, `439638666`, `439692236`, `439722704`,
  `439729234`, `439731167`, and `439732047`;
- PR number/global ID `4414`/`231744068`; top-level comment IDs `439644573`,
  `439686203`, and `439706171`; one review; zero inline review comments; one
  commit; and three changed files;
- approval review `176071572`, whose body is exactly empty and which applies to
  the patch/head commit;
- recorded base `4c9cde74ab40027b5761ab9e002af116a4a20df3`;
- patch/head `690a63b9218f72662cd3a67c6c200b758c88ce12`;
- merge commit `10cdae8e38ec448b7133cf163dca587ad806d262`;
- advanced merge first parent `5fab0ca3127bc895b611cc03bb3af1ebf9a0dbed`;
- fixed path/blob pairs
  `src/_pytest/assertion/rewrite.py`/`7b9aa5006544c160f584f1e8fc3f7771ef6e5e99`,
  `testing/test_assertrewrite.py`/`a02433cd62ab19ebb54b42b50c299e59e48de00e`,
  and `changelog/4412.bugfix.rst`/`7a28b610837873eeff2a16582de6d5a035820552`.
- Historical license blob `629df45ac405532c107eb233217bc2ac1ad70c88`.

Discussion remains metadata-and-summary-first. No discussion excerpt is
planned for S04. Exact code, test, changelog, diff, and license evidence remains
subject to the historical MIT license policy and explicit byte-retention
authorization. Intentional omission, empty content, unavailability, and
unknown history remain distinct states.

## Terminology for Provider Representations

`raw` is an endpoint-specific representation selector, not a general assertion
that a response is retained as exact bytes.

### Raw-Markdown JSON representation

For Issue, PR, comment, and review endpoints,
`application/vnd.github.raw+json` still denotes a JSON representation. Here
`raw` means that Markdown body fields are unrendered; it does not mean raw HTTP
provider bytes. These responses remain transient under the adopted retention
policy.

### Raw Git-blob byte representation

For the Git blob endpoint, `application/vnd.github.raw+json` denotes the blob
content bytes. Those bytes may be retained exactly only after the revision,
path, blob, media, encoding, and license checks pass.

The requested `Accept` selector, the observed response `Content-Type`, provider
selection metadata such as `X-GitHub-Media-Type`, and the retained entity-body
classification are separate observations. A syntactically valid generic
response type such as `text/plain` may describe the blob content and need not
echo the requested custom media type. When the complete entity body matches
the locked byte length, SHA-256, and Git blob identity, is not a JSON envelope,
and any provider selection metadata is compatible with `raw`, that generic
response type is retained as a warning rather than treated as a representation
conflict. Missing, duplicate, malformed, or explicitly contradictory media
metadata remains a hard failure.

### Exact compare-diff byte representation

For compare commits, `application/vnd.github.diff` denotes the entity body
chosen as the exact retained diff. The endpoint template is exactly:

`GET /repos/pytest-dev/pytest/compare/{base}...{head}`

The separator contains three literal ASCII periods. Abbreviated SHAs,
typographic ellipses, and mutable ref names are forbidden for canonical
capture.

### Normalized connector representation

Connector output is orientation and cross-check data. It is never described as
raw GitHub HTTP bytes, and a connector-combined surface cannot establish REST
pagination completeness.

### Common REST controls

- Host: `api.github.com`
- Method: `GET` only
- API header: `X-GitHub-Api-Version: 2026-03-10`
- Default JSON media type: `application/vnd.github+json`
- Exact compare-diff media type: `application/vnd.github.diff`
- Exact Git-blob media type: `application/vnd.github.raw+json`
- Exact-byte content encoding: absent or `identity`, requested with
  `Accept-Encoding: identity`

API-version omission is forbidden. S04 must revalidate support for
`2026-03-10`; a `410` response for an unsupported version is a hard stop. No
Authorization header, cookie, private access, credential-bearing parameter, or
browser-rendered HTML may supply canonical machine evidence. A redirect that
changes representation authority is a hard stop. S04 must lock a
byte-preserving HTTP client and its exact version.

Every `{base}` or `{head}` placeholder in this plan expands to the applicable
full locked SHA above. It never denotes an abbreviated SHA, mutable ref, or
typographic shorthand.

## Source and Endpoint Inventory

`Exact` means retained provider bytes, `transient` means inspected but deleted,
and `normalized` means selected derived fields are retained in the acquisition
record. `Transient plus normalized` means the response is deleted and only
selected normalized fields persist. All REST routes use the common controls
above.

| ID | Logical object and endpoint/action | Representation and pagination | Retention | Identities and times | Completeness and failure disposition |
|---|---|---|---|---|---|
| E1 | Repository; connector repository lookup for orientation, then `GET /repos/pytest-dev/pytest` | JSON singleton; non-paginated | Transient plus normalized | Repository/global and optional node IDs; observed alias; provider repository times | ID must equal `37489525`; identity conflict is hard, unavailability is partial, alias/default drift is warning or partial |
| E2 | Historical license metadata; `GET /repos/pytest-dev/pytest/license?ref={head}`, with `GET /repos/pytest-dev/pytest/contents/LICENSE?ref={head}` as the declared metadata fallback | JSON singleton; non-paginated | Transient plus normalized | License identity, path, revision, blob ID where exposed; no provider event time, so request/response times only | Must resolve `LICENSE` at the full head SHA to `629df45ac405532c107eb233217bc2ac1ad70c88`; conflict is hard, unavailability is partial |
| E3 | Issue singleton; connector Issue lookup, then `GET /repos/pytest-dev/pytest/issues/4412` | Raw-Markdown JSON singleton; non-paginated | Transient plus normalized; body omitted | Number `4412`, global ID `381866787`, optional node ID, created/updated/closed times | Must be an Issue in repository `37489525`; identity conflict is hard, unavailability is partial |
| E4 | Issue comments; connector discovery, then `GET /repos/pytest-dev/pytest/issues/4412/comments` | Raw-Markdown JSON; `per_page=100`, provider `Link` traversal | Transient plus normalized; bodies omitted | Comment and parent IDs; created/updated times | Pagination-complete `8/8`; duplicate/parent conflict is hard, interruption is partial |
| E5 | Issue timeline; `GET /repos/pytest-dev/pytest/issues/4412/timeline` | JSON events; `per_page=100`, provider `Link` traversal | Transient plus normalized | Event IDs where exposed, actors, referenced objects/commits, event times | Pagination-complete 24 current-visible events; parent/revision conflict is hard, missing terminal evidence is partial |
| E6 | PR singleton; connector PR lookup, then `GET /repos/pytest-dev/pytest/pulls/4414` | Raw-Markdown JSON singleton; non-paginated | Transient plus normalized; body omitted | Number `4414`, global ID `231744068`, base/head/merge identities and lifecycle times | Locked repository and revision roles must match; identity/revision conflict is hard, unavailability is partial |
| E7 | PR top-level comments; connector discovery, then `GET /repos/pytest-dev/pytest/issues/4414/comments` | Raw-Markdown JSON; `per_page=100`, provider `Link` traversal | Transient plus normalized; bodies omitted | Comment and parent IDs; created/updated times | Pagination-complete `3/3`; duplicate/parent conflict is hard, interruption is partial; connector output is not completeness evidence |
| E8 | PR timeline; `GET /repos/pytest-dev/pytest/issues/4414/timeline` | JSON events; `per_page=100`, provider `Link` traversal | Transient plus normalized | Event IDs where exposed, refs, commits, lifecycle times | Terminal page required; parent/revision conflict is hard, interruption is partial; head-ref deletion remains an observation |
| E9 | Reviews; connector review discovery, then `GET /repos/pytest-dev/pytest/pulls/4414/reviews` | Raw-Markdown JSON; `per_page=100`, provider `Link` traversal | Transient plus normalized; exactly-empty body state retained as metadata | Review `176071572`, reviewer, head commit, submitted time | Pagination-complete `1`; review/head conflict is hard, interruption is partial |
| E10 | Inline review comments; `GET /repos/pytest-dev/pytest/pulls/4414/comments` | Raw-Markdown JSON; `per_page=100`, provider `Link` traversal | Transient plus normalized; bodies omitted | Comment, parent, path, and commit IDs; created/updated times | Pagination-complete `0`; any returned-item parent conflict is hard, interruption is partial; zero differs from unavailable |
| E11 | PR commits; `GET /repos/pytest-dev/pytest/pulls/4414/commits` | JSON; `per_page=100`, provider `Link` traversal | Transient plus normalized | Commit SHA; author/committer times | Pagination-complete `1`, below the 250-commit ceiling; commit/count conflict is hard, interruption/truncation is partial |
| E12 | Changed-file inventory; connector filename discovery, then `GET /repos/pytest-dev/pytest/pulls/4414/files` | JSON; `per_page=100`, provider `Link` traversal | Transient plus normalized; JSON patch text not retained | Paths, statuses, and blob IDs where exposed; no provider event time, so request/response times only | Pagination-complete `3`, below the 3000-file ceiling; path/blob conflict is hard, interruption/truncation is partial |
| E13 | Canonical base/head comparison metadata; connector comparison orientation, then `GET /repos/pytest-dev/pytest/compare/{base}...{head}` | JSON comparison; follow a provider continuation if exposed | Transient plus normalized | Full base/head, merge-base, commit identities and provider commit times | Declared comparison must match the locked full SHAs; mismatch/truncation is hard, unavailability is partial |
| E14 | Canonical compare diff; same full-SHA compare endpoint | `application/vnd.github.diff`; non-paginated entity body | Exact diff plus normalized descriptor | Full base/head identities; no provider event time for the diff body, so request/response times only | Exact entity body must cover the three expected paths; ambiguity or truncation is hard, unavailability is partial |
| E15 | PR-diff cross-check; connector diff lookup, then `GET /repos/pytest-dev/pytest/pulls/4414` with diff media | Provider PR-diff representation; non-paginated | Transient only; optional non-replayable digest | PR identity; no provider event time for the diff body, so request/response observation times only | Semantic path/hunk disagreement with E14 is hard; unavailability is partial; byte equality is not required |
| E16 | Commit and Git-commit topology; connector commit discovery, `GET /repos/pytest-dev/pytest/commits/{sha}`, and `GET /repos/pytest-dev/pytest/git/commits/{sha}` | JSON singletons for locked revisions; non-paginated | Transient plus normalized | Commit, parent, and tree SHAs; author/committer times | Base/head/merge/first-parent roles must match S02; SHA/parent/tree conflict is hard, unavailability is partial |
| E17 | Non-recursive tree/path/blob resolution and exact historical LICENSE; `GET /repos/pytest-dev/pytest/git/trees/{tree_sha}` component by component, then `GET /repos/pytest-dev/pytest/git/blobs/629df45ac405532c107eb233217bc2ac1ad70c88` | Tree JSON plus raw Git-blob bytes; each request is non-paginated and no recursive tree is used | Tree responses transient/normalized; LICENSE exact | Revision, path, tree/blob identity; no provider event time for tree/blob content, so request/response times only | All fixed blobs must match S02; LICENSE byte and Git-object checks must pass; unavailability is partial and identity mismatch is hard |
| E18 | Changed-file raw content; `GET /repos/pytest-dev/pytest/git/blobs/{blob_sha}`, with `GET /repos/pytest-dev/pytest/contents/{path}?ref={head}` as a declared secondary route | Raw file/blob representation; non-paginated | Disabled and intentionally omitted by default; if separately enabled, inspect transiently and retain only normalized locator data—never complete file bytes | Full revision, path, blob ID, and request/response times if later authorized; no provider event time | Default omission is complete by policy; if enabled, unavailability is partial and revision/blob mismatch is hard; complete changed files remain prohibited |

General endpoint failures include access or rate-limit responses, missing or
removed API versions, server failure, malformed representations, unexpected
redirects, and identity conflicts. Access or rate interruption is not recorded
as object absence. No canonical fallback may silently replace E14 or E17.

## Connector and REST Responsibilities

| Concern | Authority |
|---|---|
| Orientation and compact discovery | Connector, only when available without private access |
| Provider identity and current metadata | Version-pinned REST representation |
| Provider timestamps | Version-pinned REST fields and event objects |
| Pagination and current-visible completeness | REST pages and provider `Link` relations |
| Exact retained bytes | REST compare-diff and raw Git-blob representations |
| Source relationships | S05 derived records citing immutable acquisition evidence |
| Browser HTML | Human attribution and navigation only |

Connector-normalized values remain separate observations. Conflicting values
are never silently merged. An unresolved stable-identity or revision conflict
is a hard failure. Metadata drift is recorded with both observations and may
produce a warning or partial status, but one value may not overwrite another
without an evidence-backed resolution.

## Deterministic Acquisition Sequence

Requests are strictly serial. A hard failure stops the affected canonical
procedure. A partial-result condition permits only bounded diagnostic
continuation and makes complete sealing impossible unless the procedure below
explicitly authorizes a whole-surface retry.

| Step | Required inputs | Generated observations | Retained artifacts or data | Failure category | Diagnostic continuation | Complete sealing possible? |
|---|---|---|---|---|---|---|
| 1. Baseline and policy reconciliation | Published S02/S03 commit and clean authorized FaultAtlas branch | Baseline, branch, policy-version, and allowlist agreement | Policy and baseline references only | Hard on any conflict | No | Yes, only after a clean pass |
| 2. Run initialization | Approved run-ID rule, path allowlist, procedure version, and HTTP client/version | Run ID, run-start UTC, and tool/procedure identity | Normalized run metadata | Hard on an existing path or unapproved tool | No | Yes, only after a clean pass |
| 3. Repository and license metadata | E1–E2 routes and locked repository/head IDs | Transient repository and license responses plus connector cross-checks | Normalized repository/license observations | Hard on identity conflict; partial on unavailability | No further provider acquisition if root identity is unverified | Yes only if required observations pass |
| 4. Issue observation A | E3 route and locked Issue IDs | Transient first Issue singleton | Normalized parent observation A | Hard on identity conflict; partial on unavailable response | Do not acquire Issue children; independent immutable diagnostics may continue after partial only | Yes only if A passes |
| 5. Issue child surfaces | Successful step 4 and E4–E5 routes | Transient ordered comment/timeline pages | Normalized child observations and pagination evidence | Hard on parent/ID conflict; partial on page failure | Independent PR/revision diagnostics may continue after partial | Yes only after this attempt or its one allowed retry passes |
| 6. Issue observation B | Completed Issue child attempt | Transient second Issue singleton and mutation comparison | Normalized parent observation B and attempt outcome | Hard on identity conflict; first mutation retries; second mutation is partial | Independent PR/revision diagnostics may continue after partial | Yes only after a stable attempt |
| 7. PR observation A | E6 route and locked PR/revision IDs | Transient first PR singleton | Normalized parent observation A | Hard on identity/revision conflict; partial on unavailable response | Do not acquire PR children; independent immutable diagnostics may continue after partial only | Yes only if A passes |
| 8. PR child surfaces | Successful step 7 and E7–E12 routes | Transient ordered comment, timeline, review, commit, and file pages | Normalized child observations and pagination evidence | Hard on parent/ID conflict; partial on page failure | Independent revision/artifact diagnostics may continue after partial | Yes only after this attempt or its one allowed retry passes |
| 9. PR observation B | Completed PR child attempt | Transient second PR singleton and mutation comparison | Normalized parent observation B and attempt outcome | Hard on identity/revision conflict; first mutation retries; second mutation is partial | Independent revision/artifact diagnostics may continue after partial | Yes only after a stable attempt |
| 10. Commit topology and blob locators | Locked revisions and E16–E17 metadata routes | Transient commit, Git-commit, and non-recursive tree responses | Normalized topology and revision-qualified path/blob observations | Hard on SHA/parent/path/blob conflict; partial on unavailable representation | Independent artifact diagnostics may continue after partial; none after hard failure | Yes only if all required topology/locators pass |
| 11. Canonical compare JSON and diff | Locked full base/head SHAs and E13–E14 routes | Transient compare JSON and exact diff entity body | Normalized comparison plus exact `base-to-head.diff` | Hard on identity, ambiguity, or truncation; partial on unavailability | LICENSE diagnostics may continue after partial; none after hard failure | Yes only if comparison and exact diff pass |
| 12. PR-diff cross-check | E15 route and successful canonical diff | Transient PR-diff representation and semantic comparison | Normalized cross-check outcome; no PR-diff artifact | Hard on semantic disagreement; partial on unavailability | Other independent diagnostics may continue after partial; none after hard failure | Yes only if the required cross-check passes |
| 13. Historical LICENSE | Locked head/path/blob and E17 blob route | Exact LICENSE entity body and byte-preservation metadata | Exact `LICENSE` plus normalized descriptor | Hard on revision/blob/digest mismatch; partial on unavailability | Other independent diagnostics may continue after partial; none after hard failure | Yes only if exact LICENSE passes |
| 14. Bounded hunk locators | Exact diff and three locked paths | Deterministic byte/line slice calculations | Three normalized locators and slice digests; no duplicate files | Hard on ambiguous or invalid locator | No further acquisition; cleanup/reporting only | Yes only if all three locators pass |
| 15. Omissions and unsupported surfaces | S02 policy and all acquisition outcomes | Policy-to-outcome classification | Normalized intentional, unknown, unavailable, inaccessible, and unsupported records | Hard on omission/failure or source/derived misclassification | Cleanup/reporting only after hard failure | Yes only if every required disposition is explicit |
| 16. Artifact and normalized-record digests | Exact artifacts, slices, and deterministic normalization rules | Byte lengths, scoped hashes, and candidate normalized bytes | Artifact/slice digest records and candidate acquisition data | Hard on mismatch, unstable normalization, or inability to hash | Cleanup/reporting only | Yes only if every required digest passes |
| 17. Consistency checks | All retained and normalized observations | Results of every classified integrity check | Normalized check results | Apply hard, partial, warning, or unsupported classification literally | Only predeclared bounded diagnostics may continue after partial; none after hard failure | Yes only with no hard or partial condition |
| 18. Seal and cleanup | Successful checks or an explicitly separate partial run | Canonicalization result, cleanup evidence, and seal UTC | Canonical `acquisition.json`, sidecar digest, and already retained exact artifacts | Hard on canonicalization, sidecar, or cleanup failure; otherwise status is complete or partial | No | Complete only when every required component passed; partial may seal only as a distinct diagnostic run |

An immutable full-SHA surface may be acquired after a mutable-surface partial
failure to preserve diagnostics, but the run remains partial. Pages and
responses from different attempts are never spliced.

## Request Budget and Rate-Limit Policy

S04 must lock a complete request graph before its first request. That graph
must enumerate:

- the exact baseline request count;
- one exact combined worst-case request count that assumes both one whole
  Issue-surface retry and one whole PR-surface retry occur in the same run;
- the separate Issue-retry and PR-retry contributions to that combined count;
- every commit and non-recursive tree traversal request;
- exact diff and LICENSE retrieval;
- transient consistency cross-checks; and
- any provider continuation already implied by the bounded procedure.

S04 must also choose a numeric safety margin after the concrete HTTP client
and request graph are known. S03 intentionally does not choose that number.
Before starting each indivisible segment, the remaining allowance must be at
least that segment's worst-case request count plus the safety margin.
Indivisible segments are the bracketed Issue attempt, bracketed PR attempt,
immutable topology/artifact segment, and any separately declared cross-check
segment.

Record these response fields when available:

- `x-ratelimit-limit`
- `x-ratelimit-remaining`
- `x-ratelimit-used`
- `x-ratelimit-reset`
- `x-ratelimit-resource`
- `retry-after`

If the remaining allowance is insufficient, stop before issuing the segment
and record an incomplete acquisition. A rate-limit response is also an
incomplete acquisition, not an object-not-found result. S04 must not add
credentials, sleep and resume, or automatically retry a rate-limited request.
The allowed whole-surface mutation retries do not authorize rate-limit retries.
Any such behavior requires a separate Gate.

## Timestamp Semantics

| Timestamp | Authority and meaning | Retention rule |
|---|---|---|
| Run start | FaultAtlas clock when the acquisition run begins | UTC with `Z` |
| Request start | FaultAtlas clock immediately before one request | Separate per request |
| Response completion | FaultAtlas clock after the complete response is observed; this is acquisition observation time | Separate from provider events |
| Provider created/updated/closed/merged | Provider fields or events | Exact provider lexeme plus separately normalized UTC |
| Review submitted | Provider review field | Exact lexeme plus normalized UTC |
| Commit author | Provider Git commit author value | Preserve exact offset and precision plus normalized UTC |
| Commit committer | Provider Git commit committer value | Preserve separately from author time |
| Merge-commit time | Merge commit's provider/Git value | Distinct from PR merged event |
| PR merged event | Provider PR/timeline observation | Distinct even when near the merge-commit time |
| Transformation time | FaultAtlas clock when an approved transformation occurs | Present only when a transformation exists |
| Acquisition seal | FaultAtlas clock after checks and transient cleanup | Final run timestamp |

Provider timestamp lexemes are retained where observed. UTC normalization does
not replace them or fabricate precision. Explicit `null`, missing field,
unavailable representation, and unsupported timestamp are different states.
`retrieved_at` or response completion records observation time and never
substitutes for a provider event time.

## Retention Strategy

The adopted policy is hybrid retention.

After separate S04 authorization, retain exactly:

- canonical base-to-head compare-diff bytes; and
- historical MIT `LICENSE` Git-blob bytes.

Do not retain raw Issue or PR JSON, comment or review JSON, discussion prose,
bot responses, linked SymPy material, or complete changed files. Selected
source metadata, request/acquisition records, pagination, completeness,
omissions, limitations, artifact locators, and digest records are retained as
normalized or derived acquisition data.

The implementation, regression-test, and changelog hunks are byte slices into
the retained diff. Each locator records the parent artifact digest, zero-based
byte offset, byte length, diff-line range, repository-relative path,
applicable new-file line range, and slice SHA-256. They are not duplicated as
independent source files.

Provider responses may be inspected and hashed transiently. When their bytes
are not retained, their digests are explicitly non-replayable and cannot prove
the original response without those bytes. A normalized record is derived and
is never labeled a provider response.

## Digest and Byte-Identity Rules

SHA-256 is required for:

- the exact compare diff;
- the exact historical LICENSE;
- each bounded diff slice;
- any later separately authorized sanitized artifact;
- canonical S04 `acquisition.json`; and
- later canonical S05 `case.json`.

Digest scopes are:

- `github-compare-diff-http-entity-body`
- `git-blob-content`
- `artifact-byte-slice`
- `normalized-acquisition-json`
- `normalized-case-json`

The S04 historical LICENSE descriptor uses `git-blob-content`, and the
`acquisition.sha256` sidecar uses `normalized-acquisition-json`. These names
are controlled vocabulary; composite or ad hoc synonyms are not permitted.

Transfer framing is excluded. The HTTP entity body is retained exactly after
requiring absent or identity content encoding. No newline conversion, Unicode
normalization, decoding/re-encoding, whitespace repair, or byte-order mark is
allowed. Record exact byte length, response content type, and content encoding.

Durable normalized JSON uses UTF-8 without a byte-order mark,
lexicographically ordered object keys, source order for arrays, LF line
endings, and one trailing LF. The sidecar digest avoids self-reference and is
not part of the JSON it hashes.

Original and sanitized bytes receive distinct digests connected by a
transformation record. Equal digests do not collapse separate acquisition
runs or request identities. SHA-256 establishes equality with the hashed
bytes; it does not establish provider authorship, authenticity, ownership, or
legal permission.

For LICENSE, additionally verify the Git object identity calculation:

`SHA-1(b"blob " + decimal_byte_length + b"\0" + exact_license_bytes)`

The result must equal `629df45ac405532c107eb233217bc2ac1ad70c88`.
This check establishes Git object identity, not GitHub authorship.

## Pagination, Mutation, and Completeness

Every paginated surface begins with `per_page=100` on its initial request.
Record the request ordinal, response status, page evidence, safe provider
`Link` relations, item IDs, and source order. Follow the provider's
`rel="next"` target exactly; only the initial URL is constructed locally, and
later-page URLs are never constructed manually. A successful terminal response
must record the absence of `rel="next"`.

Detect duplicate stable IDs, preserve provider source order, and reconcile
provider counts where exposed. Never combine pages from separate acquisition
attempts.

Required bounded results are:

- Issue comments: `pagination-complete`, `8/8`;
- Issue timeline: `pagination-complete`, 24 current-visible events;
- PR top-level comments: `pagination-complete`, 3;
- reviews: `pagination-complete`, 1;
- inline review comments: `pagination-complete`, 0;
- PR commits: `pagination-complete`, 1; and
- PR changed files: `pagination-complete`, 3.

Bracket Issue children with Issue observations A and B. Bracket PR children
with PR observations A and B. Relevant changes to parent `updated_at`, counts,
state, base/head, or merge identity discard that whole surface attempt. At
most one whole Issue-surface retry and one whole PR-surface retry are allowed.
A second detected mutation produces a partial acquisition and blocks complete
sealing.

Endpoint completeness proves only the declared current-visible surface. It
does not prove the absence of deleted, hidden, private, permission-filtered,
or prior edited representations.

## Consistency and Integrity Checks

### Hard failures

- The pinned API version is unsupported, an authority-changing redirect occurs,
  provider metadata or the entity body contradicts the selected representation,
  or content encoding is neither absent nor identity. For a raw Git-blob
  request, contradictions include a JSON envelope or a provider media selector
  that explicitly selects a non-raw representation; a valid generic response
  `Content-Type` alone is not a contradiction.
- Required response `Content-Type` metadata is missing, duplicated, malformed,
  or explicitly incompatible with the verified entity-body representation.
- Every object must resolve to repository ID `37489525`.
- Repository-scoped Issue/PR numbers must remain distinct from global IDs.
- Issue comments, PR comments, reviews, and inline comments must have the
  expected parent.
- Review `176071572` must apply to head
  `690a63b9218f72662cd3a67c6c200b758c88ce12`.
- The PR must report one commit and three changed files.
- Canonical diff filenames must match the changed-file inventory.
- Recorded base, patch/head, advanced merge first parent, and merge commit must
  retain their distinct roles and locked SHAs.
- The merge commit must contain the patch/head as the expected parent and
  preserve `5fab0ca3127bc895b611cc03bb3af1ebf9a0dbed` as its distinct first
  parent.
- The three fixed file paths and historical LICENSE path must resolve to their
  locked blobs.
- Every retained artifact and slice must match its byte length and digest.
- Empty body, missing field, intentional omission, acquisition failure, and
  unavailable representation must remain distinct.
- Raw-Markdown JSON, raw Git-blob bytes, exact diff, normalized metadata,
  sanitized material, and derived interpretation must not be mislabeled.

### Partial-result conditions

- A rate-limit interruption occurs, or the pre-segment remaining budget cannot
  be established as sufficient.
- A required endpoint or page fails after the allowed procedure.
- Terminal pagination evidence or a required current-visible item/count remains
  missing after the allowed whole-surface retry.
- A mutable surface changes twice.
- A required exact artifact is unavailable without an identity contradiction.
- Transient cleanup or complete acquisition sealing cannot be proven.

### Warnings

- Repository alias or current default branch drifts while stable identity
  remains unchanged.
- Optional node IDs, cache validators, or provider precision are absent or
  differ without changing the locked source chain.
- A valid response `Content-Type` differs from the requested Git-blob custom
  media type while the raw selection, complete entity bytes, SHA-256, and Git
  blob identity are independently verified without contradiction.
- A first mutable-surface attempt is discarded and the one allowed retry
  succeeds.

### Known unsupported verification

- Complete edit or deletion history, hidden/private objects, and historical
  default branch.
- Provider authorship proven solely from a digest or Git object ID.
- Rationale for the exactly-empty approval.
- Universal, multi-provider, private-source, or GitHub Enterprise behavior.
- Claims, confidence, causal adjudication, or transfer validity.

Derived negative-evidence relationships must cite comments `439722704`,
`439729234`, `439731167`, and `439732047`. Their apparent-failure,
independent-success, stale-cache-hypothesis, and resolution roles are derived
interpretations, not provider-authored facts.

## Acquisition Record and Case Manifest Boundaries

S04 and S05 own separate immutable layers. A generic `manifest.json` is not
used.

### S04 acquisition record

Under a later exact allowlist, S04 creates:

- `acquisition.json`
- `acquisition.sha256`
- `artifacts/base-to-head.diff`
- `artifacts/LICENSE`

`acquisition.json` owns the acquisition run identity; policy and procedure
references; repository and source-object observations; endpoint and request
records; observation and provider timestamps; pagination and completeness;
retained artifact descriptors; omissions and limitations; byte-slice
locators; and acquisition-level contract gaps. Provider parent identifiers
may be recorded as observations for integrity checks, but S04 does not lock
case-level relationship interpretation.

At successful S04 closure, `acquisition.json` is canonicalized,
`acquisition.sha256` is computed, and the acquisition record, sidecar, and
exact artifacts become immutable. S05 must not modify them. A partial
diagnostic acquisition uses a separately identified run directory and explicit
partial state; it never overwrites a complete or earlier run.

### Published S04 correction addenda

The future-tense S03 plan above remains historical planning context; current
program status is recorded in `docs/roadmap.md`. A local seal does not establish
publication or operational closure.

`S1.P00.S04.C01` records that a locally committed, sealed pre-publication S04
candidate was semantically reconciled in place before final publication. The
repair changed two classification fields and the canonical record bytes, but
not the live observation fields or retained artifact bytes; the acquisition's
reversible ledger preserves the prior candidate identity. This rewrite remains
a procedural immutability nonconformance rather than accepted practice.

The published S04 acquisition is authoritative, and its run directory,
acquisition record, sidecar, and retained artifacts are now immutable. No
further in-place correction is permitted. A later correction must be a
separately identified, append-only acquisition-layer record outside the run
directory that directly locks the authoritative published acquisition digest
and neither replaces nor silently reinterprets the acquisition.

For this case, the correction lives under
`reference_corpus/pytest-4412/corrections/s04-c01-acquisition-closure/` as
`correction.json` and `correction.sha256`. Supplemental observations in a
correction retain their own request and observation timestamps and provenance;
they are not backdated or represented as observations from the original S04
run. Current-visible provider state does not prove complete historical state.

Correction records may supplement or disposition acquisition metadata, but
they do not own case identity, observed-versus-derived relationship
classification, negative-evidence ordering, or the relationship lock reserved
for S05. S05 must reference the authoritative acquisition and each applicable
correction without modifying either.

### S05 case manifest

S05 creates separate files, provisionally named:

- `case.json`
- `case.sha256`

`case.json` references one or more immutable S04 acquisition records. It owns
case identity, source relationships, observed-versus-derived relationship
classification, negative-evidence ordering, final selection linkage,
relationship lock, and case-level known gaps. S05 does not rewrite S04
records, sidecars, or artifacts.

Formal filenames and schemas remain provisional until their authorized later
Gates, but the append-only semantic boundary between S04 acquisition evidence
and S05 case relationships is binding for S04 planning.

## Future Artifact Layout

The provisional minimum layout is:

```text
reference_corpus/
└── pytest-4412/
    ├── acquisitions/
    │   └── <run-id>/
    │       ├── acquisition.json
    │       ├── acquisition.sha256
    │       └── artifacts/
    │           ├── base-to-head.diff
    │           └── LICENSE
    └── case/
        ├── case.json
        └── case.sha256
```

Each authorized S04 Gate may create only one acquisition run directory; S05
owns the case directory. Exact artifacts and normalized metadata are
physically distinct.
No `raw/` directory exists because raw provider JSON is not retained. No
`derived/` directory exists unless a later Gate authorizes derived artifacts.
There is no mutable `latest` pointer, and no run directory may be overwritten.

Corpus paths remain source-repository-only and excluded from distributions.
S04 must stop if that exclusion cannot be confirmed without an out-of-scope
packaging change.

## Relationship to Current Internal Models

`SourceLocator` remains limited to a GitHub Issue, carries a repository alias
rather than stable repository identity, and retains unresolved `object_id`
semantics between a repository-scoped Issue number and a global REST ID. It
cannot identify a repository as its own stable source object, nor can it
identify the PR, comments, reviews, commits, blobs, revision-qualified files,
artifacts, or relationships required here.

`ArtifactSnapshot` remains bound to an Issue locator and
`application/json`. It has one UTC `retrieved_at`, accepts UTF-8 text up to
1,048,576 bytes, and validates SHA-256 over the UTF-8 encoding of
`payload_text`. It has no endpoint, API/media-version, request, response,
pagination, provenance, transformation, or artifact-relationship vocabulary.
The adopted S04 corpus does not force normalized Issue JSON into that model,
and transient provider JSON is not a durable `ArtifactSnapshot`. Unified diff
and LICENSE media do not fit it.

Acquisition provenance, transformations, artifact and digest relationships,
omissions, revision locators, and case relationships remain outside both
current models. S03 informs identity primitives in S1.P01,
revision-qualified locators in S1.P02, and evidence-envelope decisions in
S1.P03; it implements none of them and changes no current API.

## S1.P00.S04 Prerequisites and Stop Conditions

### Prerequisites

Before S04 begins, require:

- S03 published on `main`;
- explicit approval to retain the MIT-governed diff and LICENSE bytes;
- confirmation of the zero-discussion-excerpt policy;
- an exact run ID and path allowlist;
- an exact byte-preserving HTTP client and version;
- a locked request graph, maximum request count, and numeric safety margin;
- locked rate-limit-header and interruption handling;
- revalidation of API version and media behavior;
- byte-preserving behavior tested without retaining case data;
- confirmed exclusion of corpus paths from distributions;
- exact acceptance checks and transient-cleanup behavior;
- no credential, cookie, private-access, or external-execution requirement;
  and
- a clean repository baseline matching the separately authorized S04 Gate.

### Stop conditions

Stop instead of working around the condition if any prerequisite is absent;
the local baseline or Git state changes; S02 conflicts with provider evidence;
the API version returns `410` or a required public route is unavailable; rate
budget is insufficient; content encoding is neither absent nor identity; exact
bytes cannot be tied to revision, path, blob, media, encoding, and license; an
existing run would be overwritten; the append-only S04/S05 boundary would be
violated; pagination or mutation cannot be bounded; raw,
normalized, sanitized, omitted, and derived states cannot remain distinct; a
redirect changes authority; discussion prose would cross the retention
boundary; private access, credentials, cloning, or external execution becomes
necessary; an S04 acquisition would require changing an earlier acquisition;
or source, test, schema, dependency, packaging, CI, environment, persistence,
graph, retrieval, RAG, or model work becomes necessary.

## Primary Documentation Links

- [GitHub REST API versions](https://docs.github.com/en/rest/about-the-rest-api/api-versions)
- [GitHub REST API pagination](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api)
- [GitHub REST API rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [Get a repository](https://docs.github.com/en/rest/repos/repos#get-a-repository)
- [Get an Issue](https://docs.github.com/en/rest/issues/issues#get-an-issue)
- [List Issue comments](https://docs.github.com/en/rest/issues/comments#list-issue-comments)
- [List Issue timeline events](https://docs.github.com/en/rest/issues/timeline#list-timeline-events-for-an-issue)
- [Get a pull request](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request)
- [List pull-request reviews](https://docs.github.com/en/rest/pulls/reviews#list-reviews-for-a-pull-request)
- [List pull-request review comments](https://docs.github.com/en/rest/pulls/comments#list-review-comments-on-a-pull-request)
- [List pull-request commits](https://docs.github.com/en/rest/pulls/pulls#list-commits-on-a-pull-request)
- [List pull-request files](https://docs.github.com/en/rest/pulls/pulls#list-pull-requests-files)
- [Compare two commits](https://docs.github.com/en/rest/commits/commits#compare-two-commits)
- [Get a commit](https://docs.github.com/en/rest/commits/commits#get-a-commit)
- [Get a Git commit object](https://docs.github.com/en/rest/git/commits#get-a-commit-object)
- [Get a Git tree](https://docs.github.com/en/rest/git/trees#get-a-tree)
- [Get a Git blob](https://docs.github.com/en/rest/git/blobs#get-a-blob)
- [Get repository content](https://docs.github.com/en/rest/repos/contents#get-repository-content)
- [Get a repository license](https://docs.github.com/en/rest/licenses/licenses#get-the-license-for-a-repository)
