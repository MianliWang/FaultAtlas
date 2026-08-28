# FaultAtlas Roadmap

This document is the repository authority for FaultAtlas Stage, Phase, and
Slice numbering. It records the current program status and rolling plan; it
does not copy the complete external master roadmap or commit every
aspirational Slice as scheduled work.

## Terminology

- **Stage**: a broad product-capability horizon, identified as `S0` through
  `S9`.
- **Phase**: a bounded capability or preparatory objective within a Stage,
  identified as `Sx.Pyy`.
- **Slice**: the smallest independently gated unit of work within a Phase,
  identified as `Sx.Pyy.Szz`.
- **Gate**: the authorization boundary for orienting, planning, implementing,
  or publishing a Slice. Gate authorization does not carry into another Gate.

## Current status

- **S0** has an established governed operational baseline: repository
  governance, packaging, a minimal CLI, locked development tooling, tests, and
  CI. This status does not assert that every aspirational S0 item from earlier
  external planning has been implemented.
- **S1** is active. Preparatory Phase `S1.P00` is operationally complete;
  `S1.P01` is complete: `S1.P01.S01` through `S1.P01.S06` and the
  `S1.P01.S05.C01` correction are complete. `S1.P02` is complete.
  `S1.P02.S01` is complete, `S1.P02.S02` is complete, `S1.P02.S03` is
  complete, `S1.P02.S04` is complete, `S1.P02.S05` is complete, and
  `S1.P02.S06` is complete. `S1.P02.S07` is complete. `S1.P03` is complete;
  `S1.P03.S01` is complete, `S1.P03.S02` is complete, `S1.P03.S03` is
  complete, `S1.P03.S04` is complete, and `S1.P03.S05`, `S1.P03.S06`,
  `S1.P03.S07`, `S1.P03.S08`, and `S1.P03.S09` are complete. `S1.P04` is
  complete; `S1.P04.S01` is complete, `S1.P04.S02` is complete,
  `S1.P04.S03` is complete, `S1.P04.S04` is complete,
  `S1.P04.S05` is complete, `S1.P04.S06` is complete,
  `S1.P04.S07` is complete, `S1.P04.S08` is complete, and
  `S1.P04.S09` is complete, and `S1.P04.S10` is complete.
  `S1.P04` is complete.
  `S1.P05` is active and incomplete; `S1.P05.S01`, `S1.P05.S02` including the
  `S1.P05.S02.C01` correction, `S1.P05.S03`, `S1.P05.S04`, `S1.P05.S05`,
  `S1.P05.S06`, `S1.P05.S07`, `S1.P05.S08` including the `S1.P05.S08.C01`
  correction, and `S1.P05.S09` are complete, and
  `S1.P05.S10` is next and not started.
  `S1.P06` through `S1.P10` remain not started.
- **S2-S9** are not implemented.

## Program stages

- **S0 — Governed Foundation**
- **S1 — Canonical Knowledge Contracts**
- **S2 — Source Ingestion & Normalization**
- **S3 — Exact & Lexical Retrieval**
- **S4 — Hybrid Retrieval & Evaluation**
- **S5 — Repository & Evolution Graph**
- **S6 — Pattern Extraction & Transfer**
- **S7 — Artifact Synthesis & Validation**
- **S8 — Multi-model & Advanced RAG**
- **S9 — Productization, Security & Scale**

## S1.P00 — Reference-Case Calibration & Stage 1 Entry

The objective of `S1.P00` is to calibrate FaultAtlas identity, revision,
provenance, and evidence-boundary decisions against one bounded real-world
case before formalizing the Stage 1 contracts. pytest-dev/pytest Issue
`#4412` and PR `#4414` form the accepted canonical candidate. Their external
objects and payloads are not part of this documentation Slice.

`S1.P00.S01`, `S1.P00.S02`, and `S1.P00.S03` are complete.
`S1.P00.S04` is published and operationally complete. Its contractual closure
is provided by the corrective `S1.P00.S04.C01` acquisition-closure addendum.
`S1.P00.S05`, `S1.P00.S06`, `S1.P00.S07`, `S1.P00.S08`, `S1.P00.S09`, and
`S1.P00.S10` are complete. S04 and its corrective C01 remain closed, as do
S05-S10. The protected S10 publication closes `S1.P00`; `S1.P01` is complete,
including `S1.P01.S01` through `S1.P01.S06` and the `S1.P01.S05.C01`
correction. `S1.P02` is complete. `S1.P02.S01` is complete,
`S1.P02.S02` is complete, `S1.P02.S03` is complete, `S1.P02.S04` is complete,
`S1.P02.S05` is complete, and `S1.P02.S06` is complete.
`S1.P02.S07` is complete. `S1.P03` is complete; `S1.P03.S01` is complete,
`S1.P03.S02` is complete, `S1.P03.S03` is complete, `S1.P03.S04` is complete,
`S1.P03.S05`, `S1.P03.S06`, `S1.P03.S07`, `S1.P03.S08`, and `S1.P03.S09`
are complete. `S1.P04` is complete; `S1.P04.S01` is complete,
`S1.P04.S02` is complete, `S1.P04.S03` is complete, `S1.P04.S04` is
complete, `S1.P04.S05` is complete, `S1.P04.S06` is complete,
`S1.P04.S07` is complete, `S1.P04.S08` is complete, and
`S1.P04.S09` is complete, and `S1.P04.S10` is complete.
`S1.P04` is complete.
`S1.P05` is active and incomplete; `S1.P05.S01`, `S1.P05.S02` including the
`S1.P05.S02.C01` correction, `S1.P05.S03`, `S1.P05.S04`, `S1.P05.S05`,
`S1.P05.S06`, `S1.P05.S07`, `S1.P05.S08` including the `S1.P05.S08.C01`
correction, and `S1.P05.S09` are complete, and
`S1.P05.S10` is next and not started.
`S1.P06` through `S1.P10` remain not started, and `S2-S9`
remain unimplemented.

Non-goals include source ingestion, persistence, retrieval implementation,
repository graphs, RAG, model routing, artifact synthesis, services, UI, and
declaring provisional models to be public or complete contracts.

The current `S1.P00` Slice sequence is:

1. `S1.P00.S01` — Roadmap and Terminology Reconciliation (complete)
2. `S1.P00.S02` — Reference-Case Selection and Capture Policy (complete)
3. `S1.P00.S03` — Acquisition Procedure and Capture Manifest Plan (complete)
4. `S1.P00.S04` — Immutable Reference Evidence Capture (published and
   operationally complete; contractual closure provided by corrective
   `S1.P00.S04.C01`)
5. `S1.P00.S05` — Case Manifest and Relationship Lock (complete)
6. `S1.P00.S06` — Current-Contract Gap Matrix (complete)
7. `S1.P00.S07` — Identity, Revision, and Provenance Decision (complete)
8. `S1.P00.S08` — Snapshot Boundary and Compatibility Decision (complete)
9. `S1.P00.S09` — Deterministic Corpus Tests (complete)
10. `S1.P00.S10` — Integration and Phase Closure (complete; closes `S1.P00`)

## S1.P01 — Identity Primitives

The complete `S1.P01` Slice sequence is:

1. `S1.P01.S01` — Provider and Repository Identity Foundation (complete)
2. `S1.P01.S02` — Source Object Identity and Typed Identifiers (complete)
3. `S1.P01.S03` — Identity States, Lifecycle, and Conflict (complete)
4. `S1.P01.S04` — Legacy SourceLocator Compatibility Mapping (complete)
5. `S1.P01.S05` — Identity Contract Corpus (complete)
- `S1.P01.S05.C01` — Ambiguous Identity Union Round-Trip and Contract
  Assurance Correction (complete)
6. `S1.P01.S06` — Integration and Phase Closure (complete; closes `S1.P01`)

S01-S04 implement only internal provider, repository, and source-object
identity; typed provider authorities and identifiers; time-qualified repository
alias observations; explicit identity field states and unresolved typed
conflicts; lifecycle/availability observations of known source identities; and
explicit, loss-aware legacy `SourceLocator` compatibility mapping. S05 locks
that behavior in a versioned, source-only internal contract corpus. S05.C01
adds an append-only correction: ambiguous scalar-root generic states reject,
while compatibility round trips retain exact types through explicit domain
discrimination. S06 publishes the internal, case-calibrated Phase closure and
establishes S1.P02 readiness. Mutable aliases remain separate from stable
identity. S1.P02.S01 now supplies intrinsic Git commit, tree, and blob
identities only. S1.P02.S02 adds context-relative revision-role assignments
and exact ordered commit-parent topology as separate internal records.
S1.P02.S03 adds repository-, authority-, and time-qualified mutable ref
observations while preserving immutable commit identity. S1.P02.S04 adds
revision-qualified repository paths, and S1.P02.S05 adds separate bounded
line, byte, and diff-hunk locators. S1.P02.S06 publishes the internal,
source-only revision and locator contract corpus without adding a production
reader, resolver, or persistence contract. At the S1.P02 closure boundary,
retrieval provenance, conflict resolution, lifecycle transition history,
evidence envelopes, and migration remained unimplemented.

## S1.P02 — Revision-qualified Locators

The complete `S1.P02` Slice sequence is:

1. `S1.P02.S01` — Git Object Identity Foundation (complete)
2. `S1.P02.S02` — Revision Roles and Ordered Commit Topology (complete)
3. `S1.P02.S03` — Mutable Ref Observations and Lifecycle (complete)
4. `S1.P02.S04` — Revision-qualified Repository Paths (complete)
5. `S1.P02.S05` — Line, Byte, and Diff-Hunk Locators (complete)
6. `S1.P02.S06` — Revision and Locator Contract Corpus (complete)
7. `S1.P02.S07` — Integration and Phase Closure (complete; closes `S1.P02`)

`S1.P02` is complete. S01 implements internal, hash-algorithm-qualified Git
commit, tree, and blob identity. S02 implements separate context-relative
revision-role assignments and ordered commit-parent topology. S03 implements
immutable, repository-qualified observations of mutable revision refs. S04
implements exact, case-sensitive, non-normalizing revision-qualified repository
paths in a bounded UTF-8 textual subset; non-UTF-8 Git path bytes remain
unsupported. S05 implements distinct one-based inclusive line spans, zero-based
half-open byte spans, revision-line and exact-artifact-byte locators, old/new-side
diff-hunk locators, and an explicitly discriminated bounded-locator union. The
seven-Slice sequence remains fixed: S06 is complete and publishes only the
versioned, internal, source-only revision/locator contract corpus; S07
publishes the internal, case-calibrated Phase closure. `S1.P03` is complete
and its S01-S09 sequence is closed. No production corpus reader, locator
resolver, or persistence contract exists.

## S1.P03 — Evidence Envelope

The complete Phase sequence is:

1. `S1.P03.S01` — Retrieval Request Identity and Authority Foundation (complete)
2. `S1.P03.S02` — Request Controls and Response Representation Observations
   (complete)
3. `S1.P03.S03` — Exact Retained Artifacts and Digest Scope (complete)
4. `S1.P03.S04` — Acquisition Runs and Evidence Membership (complete)
5. `S1.P03.S05` — Transformations, Corrections, and Supersession
   (complete)
6. `S1.P03.S06` — Completeness, Omissions, and Publication Provenance
   (complete)
7. `S1.P03.S07` — Evidence Envelope Composition and Legacy Adapter
   (complete)
8. `S1.P03.S08` — Evidence Contract Corpus (complete)
9. `S1.P03.S09` — Integration and Phase Closure (complete; closes `S1.P03`)

S01 establishes
internal acquisition-run and request-attempt identity plus explicit retrieval
authority, method, origin-relative route path, and strict UTC start time. S02
adds explicit ordered request controls and immutable response-representation
metadata linked to request identity, while keeping requested and observed media
separate. S03 adds exact artifact content identity with explicit digest
algorithm, digest scope, and byte length, plus request-linked
exact-unmodified-byte retention records. S04 adds explicit terminal run status
and an ordered, bounded membership sequence linking each request identity to
optional request, response, and exact-artifact evidence. It preserves unknown
optional components separately from known-empty artifact membership and does
not infer historical completeness from terminal status. S05 adds path-free,
content-addressed durable-record references and explicit artifact or durable-
record transformations whose operation, version, lossiness, reversibility,
ordered inputs, and ordered outputs remain explicit. Correction is additive
and distinct from supersession, and both preserve every referenced prior
record. The canonical pytest #4412 replay contains exactly one S04.C01
correction, zero canonical transformations, and zero canonical supersessions;
positive transformation and supersession behavior is covered only by clearly
synthetic examples. S06 adds strict, explicitly scoped completeness
requirements and outcomes, including two satisfied retained-artifact
requirements followed by fifteen source-ordered intentional omissions.
Complete with declared omissions is not universal completeness, and
acquisition-run terminal status remains separate from evidence completeness.
S06 also records protected-PR publication provenance for the exact acquisition
and correction durable records, preserving stable repository identity,
reviewed head versus squash revision, explicit reviewed-tree/squash-tree
equality, PR CI versus natural main CI, and subject immutability. It claims no
complete hidden or private history. S07 adds strict, in-memory Evidence Envelope
composition over these already-typed records while preserving `None` as an
unrepresented component inventory and `()` as known empty only within the
envelope. The canonical current envelope contains one acquisition run, zero
transformations, one correction, one completeness assessment, and the ordered
acquisition and correction publications. It keeps unchanged `ArtifactSnapshot`
v1 values behind the outer wrapper and uses an explicit versioned adapter for
lossless legacy wrapping and fail-closed legacy projection. No publication
provenance is asserted for S07 itself. The existing S01-S06 modern evidence
records embed no artifact payloads. A legacy-wrapping S07 envelope can carry
the bounded `ArtifactSnapshot.payload_text` only as part of the unchanged
legacy snapshot; the models perform no I/O. S08 publishes the versioned,
internal, source-repository-only evidence contract corpus that freezes S01-S07:
deterministic valid, invalid, and replay vectors; the canonical pytest #4412
`EvidenceEnvelope` replay; the synthetic legacy adapter replay; and a test-only
executor and target registry. Its bytes are excluded from packaged artifacts.
S08 adds no production corpus reader, writer, validator, or persistence, and
claims no durable `EvidenceEnvelope` byte contract. Readers, writers, storage,
persistence, migration, canonical envelope bytes, repository snapshots,
confidence and review, and adapters beyond the explicit in-memory legacy
boundary remain deferred to their preserved later owners. S09 integrates
S01-S08 in the internal, case-calibrated Phase closure, locks the evidence
corpus and its leaf-closure assurance, and establishes S1.P04 entry readiness
without adding production behavior. At that sealed closure, S1.P04 was
eligible to begin and its implementation state was `not_started`.

## S1.P04 — Repository Snapshot Model

`S1.P04` is complete. The complete Phase sequence is:

1. `S1.P04.S01` — Immutable Repository Snapshot Subject Identity (complete)
2. `S1.P04.S02` — Repository Snapshot Root-Tree Binding (complete)
3. `S1.P04.S03` — Repository Snapshot Path-Object Binding (complete)
4. `S1.P04.S04` — Repository Snapshot Path-Binding Collection (complete)
5. `S1.P04.S05` — Repository Snapshot Declared Path Scope (complete)
6. `S1.P04.S06` — Declared Path Scope Coverage Witness (complete)
7. `S1.P04.S07` — Repository Snapshot Fact Evidence Association (complete)
8. `S1.P04.S08` — Deferred-Subject Disposition (complete)
9. `S1.P04.S09` — Repository Snapshot Contract Corpus (complete)
10. `S1.P04.S10` — Repository Snapshot Model Phase Closure (complete;
    closes `S1.P04`)

`S1.P04.S01` through `S1.P04.S10` are complete.
S01 defines the immutable snapshot subject identity as stable
`RepositoryIdentity` plus immutable `GitCommitIdentity`; mutable refs remain
observations and are not snapshot identity. S02 adds the separate strict,
immutable `RepositorySnapshotRootTreeBinding` from that unchanged subject
identity to a supplied intrinsic `GitTreeIdentity`. The tree is not part of
S01 snapshot identity. The binding is evidence-neutral: construction enforces
typed values and matching commit/tree hash algorithms but does not prove from
Git object bytes that the commit references the tree. Distinct snapshot
subjects may bind the same intrinsic tree and remain distinct.

S03 adds the separate strict, immutable `RepositorySnapshotPathBinding` from
that unchanged subject identity and one exact `GitRepositoryPath` to one
supplied intrinsic `GitBlobIdentity` or `GitTreeIdentity`. The object position
is a closed union discriminated by the existing intrinsic Git object kind, so
no separate semantic entry-kind field exists; `GitCommitIdentity` is excluded
and gitlink-like commit-at-path data fails closed. Construction enforces typed
values and requires the bound object hash algorithm to match the snapshot
revision algorithm. The association is supplied and evidence-neutral: it does
not establish path existence, repository membership, reachability from the S02
root tree, Git tree-entry correctness, or evidence provenance. S03 introduces
no Git file mode, executable state, symbolic-link or gitlink semantics,
membership collection, ordering, duplicate-path or collision detection,
completeness, absence, evidence linkage, Git or filesystem I/O, or
persistence. The repository root is not a path binding: `GitRepositoryPath`
admits neither the empty path nor `.`, and the root remains represented solely
by `RepositorySnapshotRootTreeBinding`. A child directory path may bind to a
`GitTreeIdentity` without claiming that its children have been materialized.
Exact P02 path semantics are inherited unchanged, so case-distinct and
NFC/NFD-distinct spellings remain distinct bindings. One binding is
independently meaningful and no snapshot aggregate exists.

S04 adds the separate strict, immutable
`RepositorySnapshotPathBindingCollection` with exactly two semantic fields: the
unchanged subject identity and a required bounded ordered tuple of at most 4096
already-published `RepositorySnapshotPathBinding` values. The bound is declared
inline on the field annotation rather than as a module constant, so the
reviewed module assignment surface stays exactly `__all__`. Every child must
carry exactly the collection's snapshot subject, and no exact repository path
may occur more than once within one collection; a repeated path rejects whether
its object is identical or different, without sorting, merging, or
deduplication. The empty tuple is valid and aggregates zero supplied bindings;
it does not assert that the repository, the snapshot, or the root tree is
empty, that acquisition proved absence, or that the snapshot is complete. The
explicit subject field keeps an empty collection meaningful. Supplied order is
preserved exactly and is part of value equality, so reversing the supplied
sequence yields a distinct value; that difference is representational only and
carries no Git-tree, lexical, canonical, or repository structural meaning. No
`binding_count` field exists, because no separately supplied count fact exists
and the length is deterministically derived. Two independent collections over
one subject may overlap on paths and both remain valid.

S06 adds the separate strict, immutable
`RepositorySnapshotDeclaredPathScopeCoverage` with exactly two semantic fields:
one supplied `RepositorySnapshotDeclaredPathScope` and one supplied
`RepositorySnapshotPathBindingCollection`. It is a positive-only witness. It
exists only when the declared scope is non-empty, both children carry exactly
the same snapshot subject, and every exact declared path also appears as the
exact path of a supplied binding. An empty declared scope remains a valid S05
value, but no coverage witness may be vacuous. Matching is by exact
`GitRepositoryPath` equality alone: no object kind, digest, Git mode, root
tree, prefix, normalization, or case folding participates, so a blob-backed and
a tree-backed binding cover a declared path equally. Collection supersets are
allowed — bindings outside the declared scope neither help nor hinder, and S06
makes no claim about them at all. Coverage validity does not depend on the
supplied order of either child, while the witness preserves both supplied
values unchanged, so ordinary value equality still distinguishes supplied
orders; no custom equality is introduced and neither child is sorted or
modified.

Successful construction is the entire assertion. S06 stores no status, boolean,
count, covered-path tuple, uncovered-path tuple, or per-path outcome. A
declared path with no supplied binding receives no production name and no
state: it is not absent, missing, unknown, unavailable, inaccessible, omitted,
deleted, or unresolved, and an uncovered pair simply yields no value. The
absence of a witness asserts nothing. S06 claims no repository membership, path
existence, root-tree reachability, snapshot completeness, whole-repository
completeness, or evidence verification, reuses no S1.P03 completeness type, and
creates no `snapshot` to `evidence` dependency.

`S1.P02` assigns `S1.P04` exactly four deferred subjects, not three:
`deferred:17` repository snapshot aggregation, `deferred:18` snapshot
completeness, `deferred:19` default-branch observation, and `deferred:20`
repository membership aggregation. An earlier revision of this document
said three and omitted `deferred:19`; that count was wrong and is corrected
here. The sealed `S1.P02` closure register was always correct and is
unchanged. S04 addresses `deferred:17`. Snapshot completeness is broader
than what S05 and S06 establish: S05 supplies only a declared denominator,
and S06 proves scope-relative structural coverage of supplied values rather
than snapshot or whole-repository completeness. Repository membership
aggregation is not established at all, because neither aggregating supplied
bindings, declaring a path scope, witnessing that a declared scope is
covered, nor associating a fact with a retained record is a membership,
existence, or reachability claim. `deferred:19` is likewise unaddressed:
S01 through S07 required no default-branch designation and published none,
because mutable refs are not snapshot identity. S08 dispositions all four,
together with the `S1.P00`, `S1.P01`, and `S1.P03` subjects that `S1.P04`
also inherited.
Prefix, ancestry, descendant, blob-at-prefix, file/directory collision, and
tree topology consistency are deliberately absent, so canonical prefix chains
such as `src`, `src/_pytest`, `src/_pytest/assertion`, and
`src/_pytest/assertion/rewrite.py` coexist without any reachability claim. The
repository root is still not a path binding and remains represented solely by
`RepositorySnapshotRootTreeBinding`, which S04 neither contains nor requires.

S05 adds the separate strict, immutable `RepositorySnapshotDeclaredPathScope`
with exactly two semantic fields: the unchanged subject identity and a required
bounded ordered tuple of at most 4096 exact `GitRepositoryPath` values. The
bound is declared inline on the field annotation, so the reviewed module
assignment surface stays exactly `__all__`. The scope is supplied by its
caller and is never derived from acquisition leaves, traversal observations,
root-tree observations, request records, retained diffs, S04 bindings, or any
inferred repository state; the retained canonical acquisition declares no path
scope of its own. It covers exact paths only — never a wildcard, glob, prefix,
subtree, recursive, or whole-repository scope, none of which the retained
evidence could support, because no complete tree-entry manifest was retained.
Declared path order is preserved exactly and participates in value equality, so
reversing a declaration yields a distinct value; that difference is
representational only and carries no Git-tree, lexical, canonical, or
repository structural meaning. No exact path may be declared twice in one
scope; a repeated path rejects without sorting, merging, or deduplication,
while two independent scopes may freely declare overlapping paths. The empty
tuple is valid and declares zero paths.

S05 declares a denominator; it performs no accounting. Declaring a path asserts
nothing whatever about that path — not existence, membership, resolution,
reachability, binding coverage, availability, or evidence support — and an
undeclared path is simply undeclared, never absent, missing, unknown, or
unavailable. S05 never compares declared paths against a
`RepositorySnapshotPathBindingCollection`, holds no reference to one, and
assigns no state to a declared path that has no binding. It introduces no
status, outcome, assessment, coverage, or count field, reuses no S1.P03
completeness type, and creates no `snapshot` to `evidence` dependency. Scoped
accounting over a declared scope and a binding collection is deferred.

S07 adds the first cross-domain relation, `RepositorySnapshotFactEvidenceLink`,
in the separate bridge module `faultatlas.domain.snapshot_evidence_link`. It has
exactly two semantic fields: one supplied `fact` and one supplied
`evidence_record`. The bridge exists because neither published side may own the
edge: `faultatlas.domain.snapshot` stays evidence-neutral and
`faultatlas.domain.evidence` stays predecessor-locked, and both remain
byte-identical. The new module imports both and neither imports it, so the only
`snapshot` to `evidence` edge in production is the bridge's own.

The claim is LEVEL 1 association and nothing more: the caller associates this
supplied published snapshot fact with this supplied durable evidence-record
reference. It does not assert that the record was read, parsed, or inspected,
that the record contains, supports, corroborates, derives, verifies, or proves
the fact, or that the fact is correct or authoritative. S07 introduces no
support role, strength, status, confidence, reviewer, review state, or
verification outcome, and every association carries the same deliberately weak,
uniform meaning.

The `fact` position is a closed union of exactly `RepositorySnapshotRootTreeBinding`
and `RepositorySnapshotPathBinding`, each of which corresponds directly to a
retained normalized observation. `RepositorySnapshotIdentity`,
`RepositorySnapshotPathBindingCollection`,
`RepositorySnapshotDeclaredPathScope`, and
`RepositorySnapshotDeclaredPathScopeCoverage` are rejected as `fact`. The
reason is provenance, not type-surface minimization: no retained record
declares the exact S04 aggregate or its supplied order, the S05 scope is
entirely caller supplied and absent from the retained acquisition, and S06 is a
deterministic relation over a caller scope and a supplied collection. A flat
record-level association to any of those would manufacture provenance, and
linking every child of a collection still does not make the collection itself
evidence-linked, so collection-level and coverage-level provenance stay
unmodelled.

The referenced record is exactly one `DurableEvidenceRecordReference`,
identified as a whole. S07 defines no JSON pointer, semantic path, field
locator, byte span, request, artifact, or envelope that would locate a fact
inside that record, and byte offsets are not a substitute for one:
`ArtifactByteLocator` addresses exact bytes rather than semantic JSON fields.
JSON-pointer usage elsewhere remains corpus and closure assurance metadata, not
a production surface. Each link carries exactly one record, so associating one
fact with two records is two independent link values; no `evidence_records`
tuple, ordering, duplicate, or bound semantics for multi-source support exists,
and the same fact or the same record recurring across independent links is
never rejected. The canonical witnesses are the S02 root-tree fact and all nine
S03 path bindings for pytest-dev/pytest at revision
`690a63b9218f72662cd3a67c6c200b758c88ce12`, each associated independently with
the retained canonical acquisition record.

The stronger evidence available for `LICENSE` — a normalized acquisition
relation, exact retained bytes, and a verified Git-blob digest — is deliberately
not modelled here. Widening the first association to carry it would require
separate proposition-specific semantics that S07 does not define. The target
fact is embedded by value, so S07 requires no durable snapshot bytes, record
digest, registry, identifier, persistence, or serialization, and introduces no
P10 dependency. It performs no I/O, resolves nothing, and never inspects the
record it references. Evidence association is not membership proof, path
existence, root-tree reachability, or snapshot completeness, and it licenses no
absent, unknown, unavailable, inaccessible, omitted, missing, or not-found path
state; the canonical evidence contains no negative repository-path observation.
Snapshot completeness and repository membership aggregation both remain open
after S07, and confidence, review, and interpretation provenance remain owned by
`S1.P09`.

S08 is governance-only. It changes no production source, adds no production
module, and implements no deferred product semantics; the production Python
source count remains 11. It publishes one append-only decision artifact,
`reference_corpus/contracts/repository-snapshot/decisions/s08-deferred-subject-disposition/decision.json`,
with derived Markdown and a SHA-256 sidecar, and it dispositions every deferred
subject `S1.P04` inherited.

`S1.P04` inherited exactly seven such subjects, not three: one from `S1.P00`
(`gap:s05-known:historical-default-branch-unknown`), one from `S1.P01`
(`deferred:p01:p04-repository-snapshot-aggregation`), four from `S1.P02`
(`deferred:17` through `deferred:20`), and one from `S1.P03` (`deferred:01`
repository snapshot model). Each is dispositioned exactly once, and each cites
its predecessor by exact path, JSON pointer, and SHA-256.

Three are addressed by published work. `deferred:p01:p04-repository-snapshot-aggregation`
and `deferred:17` are satisfied by S04, whose bounded ordered collection is the
aggregation those items reserved. `deferred:01` is satisfied, boundedly, by S01
through S07: the repository snapshot model now exists, while every published
non-generalization is preserved.

`deferred:18` snapshot completeness is split. Its bounded portion — a declared
exact-path scope and scope-relative positive structural coverage of supplied
bindings — is satisfied by S05 and S06. Its stronger remainder,
whole-repository snapshot completeness, is not implemented and is not claimed:
it is carried forward as `evidence_insufficient` with immediate owner `S2` and
preserved long-term semantic owner `S5`, because the retained canonical
acquisition records six non-recursive traversals and retains no tree-entry list
for any of them, so no authoritative enumeration of repository content exists.

`deferred:20` repository membership aggregation is carried forward whole as
`evidence_insufficient` to `S2` and `S5`, for the same evidentiary reason
together with the absence of verified root-tree reachability. `deferred:19`
default-branch observation is carried forward as `unsupported_current_scope` to
`S1.P05`, because a default-branch designation is a mutable-ref and history
fact rather than snapshot identity. The `S1.P00` historical default branch
keeps its state exactly — `unknown_pending_additional_evidence` — and only its
ownership moves, to `S2`; `S1.P04` never relied on historical default-branch
identity, no production source references a default branch, and the unknown is
never replaced by the repository's current default branch, which the retained
acquisition observed only at its own observation time.

The result is `self_owned_open == 0`: no unresolved subject remains owned by
`S1.P04`, and every carried-forward subject names a valid later owner. S08
closes inherited ownership, not the Phase. It is redisposition, not correction:
the `S1.P00`, `S1.P01`, `S1.P02`, and `S1.P03` closures were correct at
publication, remain byte-identical, and their original ownership and state
statements remain historically true.

S09 publishes the deterministic repository-snapshot contract corpus under
`reference_corpus/contracts/repository-snapshot/v1`, freezing the published
S01 through S07 product surface and the non-generalizations S08 finalized. It
adds no product semantics, changes no production source, and adds no production
module; the production Python source count remains 11. The corpus is
source-repository-only and is excluded from both the wheel and the sdist.

The corpus is one unified nine-file set — `manifest.json`, `valid-vectors.json`,
`invalid-vectors.json`, and `replay-vectors.json`, each with a SHA-256 sidecar,
plus a derived `contract.md` that carries no sidecar and is never an independent
authority. It spans exactly the two `S1.P04`-owned production modules,
`faultatlas.domain.snapshot` and `faultatlas.domain.snapshot_evidence_link`, and
records `faultatlas.domain.evidence`, `faultatlas.domain.identity`, and
`faultatlas.domain.revision` as supporting authorities that `S1.P04` does not
own. Its seven target symbols are exactly the seven published models;
`DurableEvidenceRecordReference` and the identity and revision types are support
targets, never `S1.P04` product symbols.

The inventory is 50 valid, 82 invalid, and 26 replay vectors — 158 in total over
16 fixtures. Every vector declares a distinct semantic partition, so no vector
restates another. The valid and invalid families cover all seven symbols,
including the strict/frozen surface, nested revalidation, the 4096 cardinality
bound and its rejection at 4097, path uniqueness, shared-subject agreement,
algorithm consistency, the closed blob-or-tree union with commit-at-path failing
closed in both Python and JSON input, frozen assignment and nested
revalidation of validation-bypassing children for every one of the seven
models, and the published Python and JSON input
boundary per model: typed Python input accepted, dumped mappings rejected, JSON
reconstruction accepted, strict tuple-versus-list behavior, and swapped or
foreign children rejected. Rejection vectors lock only structured information —
failure category, error location, error location mode, and error type — never
error prose, and where a discriminatorless union reports one error per branch
the location is matched as a stable prefix so that no pydantic-internal branch
label becomes contract.

Three semantic families are locked deliberately. The empty-inventory triple
records that an empty S04 collection and an empty S05 scope are both valid while
an S06 witness over an empty scope is not. The ordering family records that S04
and S05 preserve supplied order as part of value equality while S06 validity is
order-insensitive and the witness still preserves both supplied children
exactly. The superset family records that a four-path scope over the
nine-binding collection and a nine-path scope over the same collection are both
valid, while a nine-path scope over the four-binding collection is rejected —
and that rejection stores no absent, missing, unknown, or uncovered path, because
production assigns no such state.

Replay is chained rather than flattened, and each vector declares the provenance
of its own layer: the S01 subject and the S02 and S03 facts as
`retained_normalized_observation`, the S04 aggregate and S05 scopes as
`caller_supplied_selection`, S06 coverage as `deterministic_derivation`, and the
ten S07 associations as `caller_supplied_association`. These classifications are
corpus and test metadata and create no production vocabulary. The retained
canonical acquisition holds four normalized leaves and six non-recursive
traversals and no tree-entry manifest, so replay reconstructs the published
supplied values only and asserts no whole-repository enumeration, no verified
membership, and no root-tree reachability. The corpus never claims an
evidence-derived repository snapshot.

S07 remains LEVEL-1 association only, established positively by the exact
two-field shape, by rejection of a support role, a fact-level JSON pointer, a
verification flag, and a multi-record support collection, and by the manifest
non-goals. `S1.P04.S08` remains governance authority: it is referenced through
`source_decisions` alongside the `S1.P03` closure and the retained acquisition
record, and it is never vectorized as product behavior.

S10 closes `S1.P04`. It is closure and governance only: it changed no production
source, added no production module, and introduced no product semantics; the
production Python source count remains 11. It publishes one sealed closure
candidate at
`reference_corpus/contracts/repository-snapshot/closures/s1-p04-phase-closure`,
whose `closure.json` is the sole durable semantic authority, with a derived
non-authoritative `closure.md` and a sidecar locking the JSON alone.

The closure references rather than duplicates its authorities. It records 77
locks: 11 closure-baseline observations of the current production surface, which
are observations and not ownership claims, and 66 immutable inputs covering the
S09 corpus, the S08 decision triple, and every `S1.P00` through `S1.P03` closure,
corpus, correction, decision, and retained artifact. It locks neither `uv.lock`
nor this roadmap, following the same boundary its predecessors used.

`S1.P04` owns exactly seven product symbols across `faultatlas.domain.snapshot`
and `faultatlas.domain.snapshot_evidence_link`. `faultatlas.domain.evidence`,
`faultatlas.domain.identity`, and `faultatlas.domain.revision` remain supporting
authorities that `S1.P04` does not own, and the closure does not re-own them.

The closure register finalizes the S08 disposition as seven `S1.P04`-local
entries citing their S08 records by path, JSON pointer, and digest: three
addressed, one split, and three carried forward, reaching `self_owned_open == 0`
with owners `S2` three times immediate, `S5` twice long-term, and `S1.P05` once.
No subject remains owned by `S1.P04`. The historical default branch is still
unknown and still owned by `S2`, and no current observation was substituted for
it.

Contract-corpus assurance records the sealed S09 values: nine files, 50 valid,
82 invalid, and 26 replay vectors totalling 158 over 16 fixtures, seven-of-seven
symbol coverage, a test-only executor, package exclusion, no production
capability, and unknown target, operation, and marker all rejected. The
canonical vertical is summarized without composing any product object and keeps
its four provenance classes distinct — retained normalized observation, caller
supplied selection, deterministic derivation, and caller supplied association —
with `flattened_evidence_derived_snapshot_claimed` false and the retained
evidence limits preserved: four normalized leaves, six non-recursive traversals,
and no tree-entry manifest.

Twenty-three non-generalizations are recorded, projected from the published S08
and S09 boundaries rather than invented, and twenty-four exit criteria are
satisfied with none unsatisfied. The closure is a sealed publication candidate:
it records no pull request, reviewed head, squash SHA, or natural-main run of its
own, because none exists when its bytes are sealed, and it states so explicitly.
Its own publication evidence lives in Git history, GitHub, and the final
execution report.

`S1.P05` is `eligible_to_begin` with implementation state `not_started` and zero
unresolved blockers across nine satisfied prerequisites. Eligibility is not
commencement. The closure publishes six handoff constraints `S1.P05` inherits:
mutable refs remain observations and never snapshot identity; the snapshot
subject remains a stable `RepositoryIdentity` plus an immutable
`GitCommitIdentity` that history may reference but must not redefine;
`deferred:19` default-branch observation is owned by `S1.P05` while the
historical default branch stays unknown and owned by `S2`; whole-repository
completeness and repository membership remain transferred to `S2` and `S5` and
cannot be derived from `S1.P04` values; the S07 evidence association is LEVEL 1
only and must not be implicitly upgraded; and the published `S1.P04` contracts
and the repository-snapshot v1 corpus are frozen, so semantic change requires
the append-only correction or versioning mechanism rather than silent mutation.

Repository membership aggregation; snapshot and whole-repository completeness;
dispositional outcomes for a declared path lacking a binding; entry kind, mode,
symlink, and gitlink semantics; prefix, ancestry, and tree topology
consistency; absence; Git or filesystem I/O; and persistence or durable
serialization remain deferred. Evidence linkage is delivered only at the S07
level: one caller-supplied association between one published S02 or S03 fact
and one durable evidence record, taken as a whole. Everything stronger remains
deferred — semantic location of a fact inside a record, fact-level support,
verification, corroboration, derivation, proposition-specific exact-byte
relations, support role and strength, multi-record support collections,
collection-level and coverage-level provenance, and the confidence and review
provenance owned by `S1.P09`. `S1.P05` through `S1.P10` remain not started;
`S1.P04.S10` closure makes `S1.P05` `eligible_to_begin` while its
implementation state remains `not_started`. The subjects S08 transferred to
`S2`, `S5`, and `S1.P05` establish ownership only and confer no eligibility
on any receiving phase.

No provisional `S1.P04` sequence remains. The Slice count was fixed
retrospectively at Phase closure at ten, as `S1.P03` (nine) and `S1.P02`
(seven) did before it. The production offline-composition object once listed
in that provisional sequence was never authorized and was never built; the
evidence-linked offline vertical is demonstrated in the S09 corpus and its
chained replay instead, and `S1.P04` publishes no production aggregate
composing it.

Git mode, executable, symbolic-link, gitlink, prefix and topology consistency,
and known-absence semantics remain evidence-gated and unscheduled; no future
Slice is guaranteed for them without supporting evidence. The retained
canonical path-resolution evidence records no Git file mode for any leaf or
traversal, and it contains no negative path observation from which absence
could be derived.

Every `S1.P04` Slice received its own read-only orientation before
implementation, and no `S1.P04` Slice remains. Whether a later Slice ever
explains why a declared path lacks a binding, and what vocabulary such an
explanation would require, is undecided, and nothing here decides it.

The `S1.P04` closure gate required the S1.P02-deferred repository-membership
subject to be dispositioned, not resolved. `S1.P04.S08` dispositioned it as
`evidence_insufficient` with immediate owner `S2` and preserved long-term
owner `S5`, and `S1.P04.S10` records that disposition with
`self_owned_open == 0`. The gate is satisfied by explicit transferred
ownership; the subject itself remains unresolved and is not claimed
otherwise.

## S1.P05 — Development History Model

`S1.P05` is active and incomplete. `S1.P05.S01`, `S1.P05.S02` including the
`S1.P05.S02.C01` correction, `S1.P05.S03`, `S1.P05.S04`, `S1.P05.S05`,
`S1.P05.S06`, `S1.P05.S07`, `S1.P05.S08` including the `S1.P05.S08.C01`
correction, and `S1.P05.S09` are complete, and
`S1.P05.S10` is next and not started.

`S1.P05.S01` publishes one new production module,
`faultatlas.domain.history`, exporting exactly
`PullRequestRevisionRoleBinding`. The binding supplies the context that the
published `S1.P02` `RevisionRoleAssignment` deliberately leaves open: a role is
context-relative, and the binding names the pull request the role holds with
respect to. Its two fields embed published predecessor values whole —
`pull_request` is the `S1.P01` `NumberedSourceObjectIdentity` and
`role_assignment` is the `S1.P02` `RevisionRoleAssignment` — so neither the
subject identity nor the role-to-revision pairing is restated. The binding
carries no schema version of its own; each embedded value keeps the version it
publishes.

No development-subject identity is defined here. `NumberedSourceObjectIdentity`
already is the canonical identity of one repository-scoped Issue or Pull
Request under the locked `S1.P00.S07` decision, which records the
repository-scoped number as the primary identity component and the provider
global REST ID as an alternate typed identifier rather than part of the
identity key. `S1.P05` reuses that published identity directly and defines no
subject alias, subclass, wrapper, duplicate triple, or renamed kind enum.

The subject position accepts a pull request only. An Issue is a valid numbered
source object but records no base or head revision, so admitting one would make
an unwitnessable state constructible. The role is narrowed to `base` and
`head`, the two roles a pull request itself records; merge and merge-first-parent
are reached through merge and topology semantics and are not bound here.

The canonical witnesses are pytest-dev/pytest Pull Request `#4414` under
repository global id `37489525` bound to base revision `4c9cde74` and to head
revision `690a63b9`.

`S1.P05.S01` asserts nothing further. It does not claim that the pull request
or the revision exists, is visible, or is reachable. It does not claim that the
revision resides in the pull request's own repository: a head revision may be
authored in a fork whose repository is separately observed, absent, or no
longer known, so the two positions share no repository coherence check. It
records no ref name, branch, or default-branch designation; no ancestry,
descendance, parent topology, or reachability; no comparison, diff, or change
set; no merge, review, approval, or CI or test-run semantics; no timestamp or
chronology; and no relation between an Issue and a Pull Request. Completeness
is not claimed, and an absent binding asserts nothing. The Slice is
evidence-neutral, leaves the `S1.P04` record-level evidence association exactly
where it stands, and performs no Git or GitHub I/O.

`S1.P02` `deferred:19` default-branch observation is owned by `S1.P05` but is
not implemented by `S1.P05.S01`; the historical default branch remains unknown
and owned by `S2`. The six `S1.P04` handoff constraints are inherited
unchanged, and the published `S1.P04` contracts, the repository-snapshot v1
corpus, and all `S1.P00`-`S1.P03` artifacts remain frozen.

`S1.P05.S02` extends `faultatlas.domain.history` with `ChangedPathStatus`,
`PullRequestChangedPath`, and `PullRequestChangeSet`. A change set carries the
two published `S1.P05.S01` bindings of one pull request together with the paths
its caller supplies as changed between them. The base and head positions are
the bindings themselves: the ordered pair is already exactly what those two
bindings express, so no separate comparison subject is introduced to hold them.
Both bindings must name the same pull request and each must carry its own role.

A changed path names one `S1.P02` `GitRepositoryPath`, one supplied `S1.P02`
`GitBlobIdentity` for that path on the head side, and one supplied status. The
status vocabulary is closed to `added` and `modified`, the two statuses the
retained material supplies; removed, renamed, and copied are absent rather than
reserved, because no supplied value describes one. Only a head-side object is
carried, so a change set names what a path is said to hold afterwards and says
nothing about what it held before. No content, diff, patch, hunk, or line is
present in any form.

A change set is bounded to between one and 4096 changed paths, preserves its
caller's supplied order exactly without attaching meaning to it, and rejects a
repeated path without deduplication. Its base and head revisions must differ.
It claims no completeness: it is exactly the paths its caller supplied, never
those of a comparison, a commit, or a repository. It expresses no merge base,
no ahead or behind count, no ancestry, descendance, reachability, or parent
topology, and no repository-snapshot membership or path existence. It remains
evidence-neutral, and exact retained comparison bytes belong to a later
association.

`S1.P05.S02.C01` corrects two boundaries that the published `S1.P05.S02`
contract left open. `S1.P05.S02` admitted an empty change set and described it
as supplying zero changed paths rather than asserting that nothing changed.
Because the value never expresses completeness, an empty collection could not
state that nothing changed either, so it said nothing at all while still
appearing to be a change record; at least one changed path is now required, and
supplying none is not a change set rather than an empty one. `S1.P05.S02` also
admitted a change set whose base and head named the same revision, which has no
between for changed paths to describe; the two revisions must now differ. Both
corrections narrow the accepted inputs only. No published symbol, field,
status value, or claim is added, removed, or restated, and the `S1.P05.S02`
publication history stands unrewritten.

The canonical witness is pytest-dev/pytest Pull Request `#4414` from base
`4c9cde74` to head `690a63b9` with exactly three supplied changed paths:
`changelog/4412.bugfix.rst` added, and `src/_pytest/assertion/rewrite.py` and
`testing/test_assertrewrite.py` modified.

A standalone comparison-boundary contract was considered and dropped. The
retained `commit_comparison` record's own identity is exactly its base and head
revisions, which `S1.P05.S01` already publishes as two bindings, so such a
contract would have grouped published values without adding a witnessed fact.
Its remaining fields are either the change facts now carried here or the
deterministic ahead, behind, and merge-base derivations that remain deferred
with `S1.P02` `deferred:22` ancestry and reachability.

`S1.P05.S03` extends `faultatlas.domain.history` with
`PullRequestReviewRevisionApproval`, supplying the edge the published review
identity leaves open. The `S1.P00.S07` decision links a pull-request review to
its stable repository, its parent pull request, and the revision it reviewed;
the published `S1.P01` `ProviderScopedSourceObjectIdentity` carries the first
two inside its parent and carries no revision at all. It is the only
provider-scoped kind whose `S1.P00.S07` linkage exceeds what `S1.P01`
implements, so the missing edge is a `S1.P05` responsibility. An approval names
that revision, and no second review identity is defined.

Its two fields are the published `S1.P01` review identity and the published
`S1.P02` `GitCommitIdentity`. The review position accepts a pull-request review
only; the parent pull request is not restated, because the published identity
already carries it and already requires it to be a pull request. The revision is
bound directly rather than through a `S1.P05.S01` binding: the canonical review
approved the revision that is also the recorded pull-request head, but that
coincidence is a deterministic derivation about one case rather than a property
of reviews, and a review of an intermediate revision would be unrepresentable
if the head role were required.

Approval is carried by the relation itself rather than by a state field. The
retained material supplies exactly one approval disposition, so a vocabulary of
one member would add nothing, and naming dispositions that nothing supplies
would invent them. An approval is a historical occurrence, not a current state:
its caller states that this review approved this revision, and nothing states
that the approval still stands or was never dismissed. Complete historical
review state is not established by any retained material.

An approval records no submission time, no review body or rationale, and no
reviewer. A body observed to be exactly empty is not an absence of reason, and
occurrence time belongs to bounded chronology. Approval here is a
provider-observed disposition and never FaultAtlas confidence, claim
acceptance, reviewed interpretation, technical correctness, test or CI outcome,
merge readiness, causation, or proof of repair. The Slice remains
evidence-neutral.

The canonical witness is pytest-dev/pytest review `176071572` under Pull
Request `#4414`, approving revision `690a63b9`.

`S1.P05.S04` extends `faultatlas.domain.history` with
`PullRequestMergeRevisionOutcome`, naming the immutable revision one pull
request merged as. Its two fields are the published `S1.P01`
`NumberedSourceObjectIdentity` and the published `S1.P02` `GitCommitIdentity`,
and the revision is bound directly: no revision role, role assignment, or
parent sequence is restated. A commit and its exact ordered parents are already
a published revision fact, so a caller needing the merge revision's parents
uses `GitCommitParentTopology` directly rather than a copy carried here.

The outcome is a historical occurrence rather than a present state. The
retained pull request supplies `state` as `closed` and no merge commit
identifier at all; the merge revision is established by the retained merged
timeline event. Nothing here reports whether a pull request is currently
merged, open, or closed, and there is no merged flag, disposition, or state
vocabulary. Only positive outcomes are expressible: an absent outcome is not a
statement that a pull request did not merge, and no vocabulary for that exists.

An outcome asserts nothing about parent count, merge strategy, or which parent
holds which position, and nothing about the revisions the pull request records
in its base or head roles. The recorded base need not be a parent of the merge
revision, nor its ancestor, nor equal to any parent: the retained canonical
material is exactly such a case, where the integration branch advanced between
the recorded base `4c9cde74` and the merge first parent `5fab0ca3`. No merge
base, ahead or behind count, ancestry, descendance, or reachability is
expressed. No merge time, merge actor, or relationship to a review is recorded,
and merging is not correctness, test or CI outcome, causation, or proof of
repair.

The canonical witness is pytest-dev/pytest Pull Request `#4414` merging as
revision `10cdae8e`.

`S1.P05.S05` extends `faultatlas.domain.history` with
`PullRequestHeadRefDeletion`, naming the mutable ref a pull request recorded
for its head revision and stating that the ref was deleted. Its two fields are
the published `S1.P05.S01` head binding and the published `S1.P02` `GitRefName`,
so the pull request, the revision the ref named, and the ref's former target
are not restated.

The published `S1.P02` `GitRefObservation` is deliberately not reused. That
contract requires a repository identity, a namespace, an observing authority,
and a FaultAtlas observation time, and the retained canonical material supplies
none of the four: the head repository field is an observed null, the original
repository is unknown, no namespace is recorded, and only a provider event time
exists. Instantiating it would have required fabricating all four, so the ref
is named rather than identified.

Those unknowns stay separate, exactly as the retained material records them. A
field observed as null is not a deleted ref, a representation that can no
longer be retrieved is not an unknown identity, and neither is the immutable
revision the head binding still carries. `GitRefName` is namespace-relative by
contract and refuses a `refs/` prefix, so it contributes only name validation
and states no namespace or repository.

A deletion is a historical occurrence rather than a present state: nothing says
the ref is currently deleted or that any representation is retrievable now, and
the absence of a deletion is not a statement that a ref still exists. There is
no lifecycle state, no availability field, and no time. One deletion is one
supplied fact, never a complete ref history, and rename, reuse, and recreation
are outside it. No branch or default-branch meaning attaches to a recorded
head-ref name, and a merge preceding a deletion is a comparison between two
observations rather than a reason for it.

The canonical witness is pytest-dev/pytest Pull Request `#4414` at head
`690a63b9` with the deleted head-ref name `starred_with_side_effect`.

`S1.P05.S06` extends `faultatlas.domain.history` with
`PullRequestHistoricalOccurrenceTime`, naming the source instant at which one
already published historical fact occurred. Its two fields are exactly one of
the three published occurrence facts — a `PullRequestReviewRevisionApproval`,
a `PullRequestMergeRevisionOutcome`, or a `PullRequestHeadRefDeletion`,
embedded whole — and one required aware instant. The subject position carries
the meaning, so no occurrence kind, event type, or discriminating field is
added: the embedded relation already is the kind.

The instant is a source occurrence time and never a FaultAtlas observation
time. `observed_at`, which the published `S1.P01` and `S1.P02` observation
values carry, records when FaultAtlas looked; the two live under different
authorities and neither supplies nor overwrites the other. No acquisition,
retrieval, or publication time is expressible here. The instant is required
and carries no condition of its own: every occurrence the retained material
supplies carries its time, so an optional instant, an availability field, and
a vocabulary for a missing time would each name an absence that nothing
supplies. That an alternate surface omits its copy of a time — as the retained
pull request timeline does for the review event — is a statement about which
record supplies a fact rather than about the fact.

One occurrence time is one point and never a sequence. No order, position,
ordinal, precedence, or comparison is expressed or implied, and equal times
across separate source surfaces carry no causal order: the retained material
records three such equal-second pairs and states for each that no cross-surface
causal order is asserted. Nothing here is a chronology, a timeline, or a
collection; an absent occurrence time is not a statement that nothing occurred;
and no occurrence or semantic-role classification vocabulary appears, both
being uniform across every retained occurrence this Slice can reach. Duration,
interval, currency, clock accuracy, skew, and monotonicity are all outside it.

The canonical witness is the pytest-dev/pytest review `176071572` approval of
revision `690a63b9`, occurring at `2018-11-17T23:54:20Z`.

`S1.P05.S07` adds the Phase's first cross-domain relation,
`PullRequestHistoryFactEvidenceLink`, in the separate bridge module
`faultatlas.domain.history_evidence_link`. It has exactly two semantic fields:
one supplied `fact` and one supplied `evidence_record`. The bridge exists
because neither published side may own the edge: `faultatlas.domain.history`
stays evidence-neutral and `faultatlas.domain.evidence` stays
predecessor-locked, and both remain byte-identical. The new module imports both
and neither imports it, so the only `history` to `evidence` edge in production
is the bridge's own. Production sources move from 12 to 13.

The claim is LEVEL 1 association and nothing more: the caller associates this
supplied published history fact with this supplied durable evidence-record
reference. It does not assert that the record was read, parsed, or inspected,
that the record contains, supports, corroborates, derives, verifies, or proves
the fact, or that the fact is correct or authoritative. No support role,
strength, status, confidence, reviewer, review state, or verification outcome
is introduced, and every association carries the same deliberately weak,
uniform meaning. The `S1.P04` closure constraint that this association is
LEVEL 1 only and must not be implicitly upgraded is inherited and honoured.

The `fact` position is a closed union of exactly
`PullRequestRevisionRoleBinding`, `PullRequestChangedPath`,
`PullRequestReviewRevisionApproval`, `PullRequestMergeRevisionOutcome`,
`PullRequestHeadRefDeletion`, and `PullRequestHistoricalOccurrenceTime`, each
of which corresponds directly to a retained normalized observation.
`PullRequestChangeSet` and `ChangedPathStatus` are rejected as `fact`. The
reason is provenance, not type-surface minimization: the retained collection
declares a complete, source-ordered set of changed paths, while the published
change set carries a caller-supplied, caller-ordered tuple that deliberately
asserts no completeness, so associating one record with it would attribute a
completeness the product disclaims; and a closed status vocabulary is not a
fact. Excluding the aggregate strands nothing, because its base binding, head
binding, and each changed path remain individually linkable.

The referenced record is identified as a whole. There is no JSON pointer,
semantic path, field locator, byte span, request, artifact, or envelope, and no
`semantic_field` naming a field of the fact. That a fact's fields are drawn
from several places inside one record, or that an alternate surface within it
omits a duplicate field — as the retained pull request timeline does for the
review timestamp, and the ordinary pull request object does for the merge
revision — changes nothing here: the record is associated whole, and the
retained record already carries its own field state under `S1.P01` and `S1.P03`
authority. Each link carries exactly one record; associating one fact with two
records is two independent link values, with no ordering, precedence, primary
designation, or `evidence_records` aggregate. A correction or superseding
record is associated only when a caller supplies it, and no supersession is
followed.

The traceability this publishes is exactly one level: semantic fact to exact
immutable `DurableEvidenceRecordReference` to exact retained record bytes.
Localizing a semantic field to a record field is not available here and is
reserved for a later explicitly assigned owner.

The canonical witnesses are the eleven retained `S1.P05` facts — the base and
head bindings of pull request `4414`, its three changed paths, the review
`176071572` approval, the merge outcome `10cdae8e`, the head-ref deletion, and
the three occurrence times — each associated with the retained acquisition
record `1c29093b` of `61283` bytes. The same fact associated with the retained
additive correction `44491ee5` is a second, independent link.

`S1.P05.S08` is governance-only and changed no production source. It publishes
the sealed decision
`reference_corpus/contracts/development-history/decisions/s08-deferred-subject-disposition`,
whose `decision.json` is the sole semantic authority, with `decision.md`
derived and `decision.sha256` locking the JSON bytes. It dispositions the
twelve deferred subjects `S1.P05` inherited from `S1.P00`, `S1.P01`, `S1.P02`,
`S1.P03`, and `S1.P04` exactly once each, and introduces none of its own,
reaching `self_owned_open == 0`. Four are split into an addressed portion and a
carried-forward remainder; eight are carried forward whole. No subject is
claimed resolved that is not, and no predecessor byte is edited: each item
cites its source by exact path, JSON pointer, and SHA-256.

The disposition and state vocabulary is exactly the one `S1.P04.S08` published
— `addressed`, `split`, and `carried_forward` over `evidence_insufficient`,
`unknown_pending_additional_evidence`, and `unsupported_current_scope` — and no
new enum is introduced. Five remainders go to `S2` for acquisition, four of
those preserving `S5` as the long-term semantic owner, one goes to `S5` for
repository-graph semantics over evidence that is already retained, and six go
to `S1.P06` as FaultInstance-consuming semantics. Immediate owners are
therefore `S1.P06` six, `S2` five, and `S5` one; long-term owners are
`S1.P06` six, `S5` five, and `S2` one.

The default-branch subject is the clearest case, and it is two subjects rather
than one. `deferred:19` assigns the default-branch designation to `S1.P05`,
while the historical default branch is a separate inherited subject already
owned by `S2`, and the two are kept apart. The retained repository observation
already records `main` observed in 2026, so the designation subject is not
blocked on acquisition and is carried forward to `S5` for repository-graph
semantics over retained mutable-ref observations rather than to an acquisition
owner. The analysed pull request targeted a base ref named `master` in 2018,
which disagrees with that observation and is a base-ref lexeme rather than a
designation, so neither may be substituted for the other, and the historical
default branch at the canonical occurrence time has no retained evidence and is
not re-dispositioned here. Ancestry, rename and copy, complete
mutable-ref and path event history, a generic event or relationship framework,
and a complete discussion graph are each carried forward for the same reason:
the retained material does not supply them, and inventing a model would
manufacture source facts. `S1.P05.S08` closes no subject by assertion and
publishes no product semantics.

`S1.P05.S08.C01` corrects the owner topology of that disposition without
editing it. The published `S1.P05.S08` decision is immutable historical
provenance: its bytes are unchanged, its digest is unchanged, and it is not
regenerated. The correction publishes a separate sealed artifact under
`reference_corpus/contracts/development-history/corrections/s08-c01-deferred-subject-owner-topology`
and supersedes exactly six of the twelve disposition records by citation.

Four of the six move a generic-graph remainder from `S1.P06` to `S5`: the
development-history event model, the development-history relationship model,
`deferred:22` ancestry and reachability, and the `deferred:02`
development-history model. A generic development, relationship, or Git ancestry
graph is repository and evolution graph semantics owned by `S5`; `S1.P06`
consumes bounded facts for FaultInstance modelling and does not own a generic
Git graph. The relationship-model record is additionally promoted from
`carried_forward` to `split`, because `S1.P05.S01`, `S1.P05.S03`, `S1.P05.S04`,
and `S1.P05.S05` do publish bounded typed relations and the published record
understated that. `deferred:24` moves to `S2` immediate and `S5` long-term with
its state corrected to `evidence_insufficient`, since the blocker is retained
evidence rather than scope, and the discussion edit and deletion subject keeps
`S2` as immediate owner while its preserved long-term owner becomes `S5`.

The `deferred:p04:04` default-branch record is deliberately not corrected and
is recorded as such. Its published `S5` ownership is retained because the
retained repository observation already supplies a current designation, so the
subject is not blocked on acquisition, while the separate historical
default-branch unknown remains owned by `S2` through its own inherited subject.

The effective projection keeps all twelve inherited subjects dispositioned
exactly once with no self-introduced subject and `self_owned_open == 0`, under
`S1.P05.S08` for six subjects and `S1.P05.S08.C01` for six. Immediate owners
are `S2` six, `S5` five, and `S1.P06` one; long-term owners are `S5` eleven and
`S1.P06` one. No product semantics change and no production source changes.

`S1.P05.S09` publishes the source-only development-history contract corpus at
`reference_corpus/contracts/development-history/v1`, freezing the published
product surface before Phase closure. It changed no production source. The
corpus covers the two `S1.P05` production modules and all nine published
product symbols, derives that coverage from the live `__all__` of each module
so a later published symbol forces deliberate review, and names
`faultatlas.domain.identity`, `faultatlas.domain.revision`, and
`faultatlas.domain.evidence` as supporting authorities it does not own. The
`S1.P04` snapshot modules are outside it: no `S1.P05` value consumes them.

Nine files hold 181 vectors over 19 declared fixtures -- 48 valid, 109 invalid,
and 24 replay -- each occupying a semantic partition that is distinct in
behaviour, not merely in label. Invalid vectors
lock a failure category, an error location, a location mode, and an error type,
and deliberately lock no prose, no validator name, and no Pydantic internal
union branch label; the prefix location mode is used only for the two
discriminatorless unions, the `S1.P05.S06` occurrence union and the
`S1.P05.S07` fact union.

The canonical replay uses three provenance classifications and deliberately no
fourth: `S1.P05` publishes no deterministic derivation, so the retained ahead,
behind, and merge-base values stay deferred with `S1.P02` `deferred:22`. Eleven
history facts are individually linkable, while `PullRequestChangeSet` is
replayed as a caller-supplied composition that `S1.P05.S07` does not admit as
an evidence-link fact, and the replay preserves that asymmetry rather than
flattening every value into evidence-derived history.

`S1.P05.S08` and its append-only `S1.P05.S08.C01` correction are consumed as
source authorities and are never vectorized as product behaviour. The corpus
executor recomputes the effective disposition projection from both artifacts
rather than trusting a stored table, and both remain byte-identical.

The remaining `S1.P05` sequence is PROVISIONAL. It authorizes no future
implementation and may split, merge, renumber, or drop after later read-only
orientations. It is evidence-driven rather than fixed at ten Slices:

1. `S1.P05.S01` — Pull Request Revision Role Binding (complete)
2. `S1.P05.S02` — Pull Request Supplied Change Set (complete)
- `S1.P05.S02.C01` — Positive Change-Set Boundary Correction (complete)
3. `S1.P05.S03` — Pull Request Review Revision Approval (complete)
4. `S1.P05.S04` — Pull Request Merge Revision Outcome (complete)
5. `S1.P05.S05` — Pull Request Head-Ref Deletion (complete)
6. `S1.P05.S06` — Pull Request Historical Occurrence Time (complete)
7. `S1.P05.S07` — Pull Request History Fact Evidence Association (complete)
8. `S1.P05.S08` — Deferred-Subject Disposition (complete)
- `S1.P05.S08.C01` — Deferred-Subject Owner-Topology Correction (complete)
9. `S1.P05.S09` — Development History Contract Corpus (complete)
10. `S1.P05.S10` — Integration and Phase Closure (provisional; next, not
    started)

The Issue-to-Pull-Request pairing is retained case material classified as a
reviewed derived interpretation rather than a provider fact, and it is
deliberately not scheduled as an `S1.P05` product relation.

`S1.P06` is not eligible to begin. `S1.P05` is incomplete, and no `S1.P06`
readiness is claimed here.

## Preserved later Stage 1 phases

- **S1.P06 — Fault Instance Model**
- **S1.P07 — Pattern & Invariant Model**
- **S1.P08 — Transfer & Applicability Model**
- **S1.P09 — Provenance, Confidence & Review**
- **S1.P10 — Persistence, Serialization & Contract Corpus**

## Current-code mapping

The existing internal `SourceLocator` and `ArtifactSnapshot` models remain
pre-roadmap S1 seeds. They are not revision-qualified Git locator (`S1.P02`)
or Evidence Envelope implementations, and they are not public contracts.
The internal `faultatlas.domain.evidence` module implements the `S1.P03.S01`
request-provenance foundation and the `S1.P03.S02` request-control and bounded
response-representation metadata layer. It also implements the `S1.P03.S03`
metadata-only exact-artifact identity and request-linked retention layer, plus
the `S1.P03.S04` terminal acquisition-run and ordered evidence-membership
layer. The `S1.P03.S05` layer adds content-addressed durable-record references,
explicit artifact/record transformations, additive corrections, and separate
supersession relationships without executing transformations or performing
I/O. The `S1.P03.S06` layer adds scoped completeness requirements and outcomes,
structured omission records, complete-with-declared-omissions semantics, and
protected-PR publication provenance with separate PR and natural-main checks.
It does not embed artifact bytes or storage locations, claim complete hidden or
private history, or implement readers, writers, storage, persistence,
migration, or a corpus. The `S1.P03.S07` layer adds strict in-memory Evidence
Envelope composition, explicit unknown versus known-empty component
inventories, unchanged legacy `ArtifactSnapshot` v1 composition behind an
outer wrapper, and versioned, loss-aware legacy wrapping and projection. It
does not implement readers, writers, storage, persistence, migration,
canonical envelope bytes, repository snapshots, confidence or review, a
production contract-corpus capability, or adapters beyond that explicit legacy
boundary. `S1.P03.S08` publishes the internal, source-only evidence contract
corpus under `reference_corpus/contracts/evidence-envelope/v1` with a test-only
executor and registry; it changes no production source. `S1.P03.S08` is
complete. `S1.P03.S09` publishes the internal Phase closure under
`reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure`,
integrates S01-S08, locks the corpus and verified replay-leaf assurance, and
establishes S1.P04 readiness without changing production source. `S1.P03` and
S01-S09 are complete. The current live surface adds the pure
`RepositorySnapshotIdentity` and the supplied, evidence-neutral
`RepositorySnapshotRootTreeBinding`, `RepositorySnapshotPathBinding`, and
`RepositorySnapshotPathBindingCollection`,
`RepositorySnapshotDeclaredPathScope`, and
`RepositorySnapshotDeclaredPathScopeCoverage` values in
`faultatlas.domain.snapshot`, and the separate bridge module
`faultatlas.domain.snapshot_evidence_link`, whose sole
`RepositorySnapshotFactEvidenceLink` associates one supplied
`RepositorySnapshotRootTreeBinding` or `RepositorySnapshotPathBinding` with
one supplied `DurableEvidenceRecordReference`. `S1.P04` is complete;
`S1.P04.S01` through `S1.P04.S10` are complete. The current live surface also
adds the module `faultatlas.domain.history`, whose sole
`PullRequestRevisionRoleBinding` binds one supplied
`NumberedSourceObjectIdentity` identifying a pull request to one supplied
`RevisionRoleAssignment` in the `base` or `head` role. It reuses those
published `S1.P01` and `S1.P02` values whole, defines no development-subject
identity, carries no schema version of its own, performs no I/O, and claims no
repository containment, ancestry, comparison, change set, review, merge, ref
or default-branch designation, timestamp, evidence linkage, or completeness.
It is joined there by `ChangedPathStatus`, `PullRequestChangedPath`, and
`PullRequestChangeSet`, which carry the two bindings of one pull request
together with the paths its caller supplies as changed between them, each
naming a repository path, a head-side blob identity, and a supplied `added` or
`modified` status, with no content, comparison metric, ancestry, completeness,
or evidence claim. As corrected by `S1.P05.S02.C01`, a change set carries
between one and 4096 changed paths and requires its base and head revisions to
differ. `PullRequestReviewRevisionApproval` joins them, binding one published
pull-request review identity to the immutable revision it approved, with no
review state, timestamp, body, reviewer, revision role, evidence, or confidence
claim. `PullRequestMergeRevisionOutcome` completes the current set, naming the
immutable revision a pull request merged as, with no parent sequence, revision
role, merge state, strategy, timestamp, ancestry, or base and head coupling.
`PullRequestHeadRefDeletion` names the mutable head ref a pull request recorded
and states that it was deleted, carrying no repository, namespace, lifecycle
state, availability, or time. `PullRequestHistoricalOccurrenceTime` closes the
current set, naming the source instant at which exactly one of the published
approval, merge-outcome, or head-ref-deletion facts occurred, with no
occurrence kind, order, sequence, classification, FaultAtlas observation time,
missing-time vocabulary, or evidence linkage. The live surface also adds the
separate bridge module `faultatlas.domain.history_evidence_link`, whose sole
`PullRequestHistoryFactEvidenceLink` associates one supplied
`PullRequestRevisionRoleBinding`, `PullRequestChangedPath`,
`PullRequestReviewRevisionApproval`, `PullRequestMergeRevisionOutcome`,
`PullRequestHeadRefDeletion`, or `PullRequestHistoricalOccurrenceTime` with one
supplied `DurableEvidenceRecordReference`. `PullRequestChangeSet` and
`ChangedPathStatus` are not associable there, the record is named whole with no
pointer, field path, locator, or byte span, and no support role, strength,
verification, confidence, primary designation, or evidence-record aggregate
exists. `faultatlas.domain.history` and `faultatlas.domain.evidence` are
unchanged by `S1.P05.S07` and neither imports the bridge. Production Python
sources are 13.
`S1.P05` is active and incomplete: `S1.P05.S01`, `S1.P05.S02` including the
`S1.P05.S02.C01` correction, `S1.P05.S03`, `S1.P05.S04`, `S1.P05.S05`,
`S1.P05.S06`, `S1.P05.S07`, `S1.P05.S08` including the `S1.P05.S08.C01`
correction, and `S1.P05.S09` are complete, and
`S1.P05.S10` is next and not started.
`S1.P04.S10`
changed no production source: it published the sealed Phase closure under
`reference_corpus/contracts/repository-snapshot/closures/s1-p04-phase-closure`,
recording 77 locks, seven finalized deferred entries with
`self_owned_open == 0`, 23 non-generalizations, 24 satisfied exit criteria,
and six `S1.P05` handoff constraints. `S1.P04.S09`
changed no production source: it published the deterministic contract
corpus under `reference_corpus/contracts/repository-snapshot/v1`, freezing
the seven published models across 158 vectors with a chained,
provenance-heterogeneous replay. `S1.P04.S08` changed no
production source: it published the governance-only deferred-subject
disposition under
`reference_corpus/contracts/repository-snapshot/decisions/s08-deferred-subject-disposition`,
dispositioning all seven inherited subjects exactly once and reaching
`self_owned_open == 0`. The path binding, its collection, the declared path
scope, and the coverage witness perform no Git or filesystem I/O and claim no
repository membership, snapshot completeness, or absence; they carry no
evidence linkage of their own, which is why the association lives in the
bridge rather than in `faultatlas.domain.snapshot`.
The bridge performs no I/O either, never inspects the record it references,
and asserts only caller-supplied record-level association: no fact locator,
support role, strength, confidence, review, verification, membership,
completeness, or absence. `faultatlas.domain.snapshot` and
`faultatlas.domain.evidence` are unchanged by `S1.P04.S07` and neither
imports the bridge.

The minimal CLI and governed Python foundation belong to the S0 operational
baseline. Environment-only commits remain a development-maintenance track and
are not product Phases.

## Rolling planning

Slices in the current Phase may be detailed as evidence and decisions become
available. Later-Phase implementation details remain provisional until their
own gates. In particular, no advanced RAG approach is locked before retrieval
benchmarks justify it.
