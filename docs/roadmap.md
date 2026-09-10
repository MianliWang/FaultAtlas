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
  `S1.P05` is complete; `S1.P05.S01`, `S1.P05.S02` including the
  `S1.P05.S02.C01` correction, `S1.P05.S03`, `S1.P05.S04`, `S1.P05.S05`,
  `S1.P05.S06`, `S1.P05.S07`, `S1.P05.S08` including the `S1.P05.S08.C01`
  correction, `S1.P05.S09`, and `S1.P05.S10` are complete.
  `S1.P06` is active and incomplete; `S1.P06.S01` is complete,
  `S1.P06.S02` is complete, `S1.P06.S03` is complete,
  `S1.P06.S04` is complete, `S1.P06.S05` is complete,
  `S1.P06.S06` is complete, `S1.P06.S07` is complete including the
  `S1.P06.S07.C01` correction, `S1.P06.S08` is complete,
  `S1.P06.S09` is complete, `S1.P06.S10` is complete, and
  `S1.P06.S11` is next and not started.
  `S1.P07` through `S1.P10` remain not started.
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
`S1.P05` is complete; `S1.P05.S01`, `S1.P05.S02` including the
`S1.P05.S02.C01` correction, `S1.P05.S03`, `S1.P05.S04`, `S1.P05.S05`,
`S1.P05.S06`, `S1.P05.S07`, `S1.P05.S08` including the `S1.P05.S08.C01`
correction, `S1.P05.S09`, and `S1.P05.S10` are complete.
`S1.P06` is active and incomplete; `S1.P06.S01` is complete,
`S1.P06.S02` is complete, `S1.P06.S03` is complete,
`S1.P06.S04` is complete, `S1.P06.S05` is complete,
`S1.P06.S06` is complete, `S1.P06.S07` is complete including the
`S1.P06.S07.C01` correction, `S1.P06.S08` is complete,
`S1.P06.S09` is complete,
`S1.P06.S10` is complete, and `S1.P06.S11` is next and not started.
`S1.P07` through `S1.P10` remain not started, and `S2-S9`
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

At that sealed closure, `S1.P05` was `eligible_to_begin` with implementation
state `not_started` and zero unresolved blockers across nine satisfied
prerequisites. Eligibility was not commencement. `S1.P05` has since been
implemented and closed by `S1.P05.S10`. The closure published six handoff
constraints `S1.P05` inherited:
mutable refs remain observations and never snapshot identity; the snapshot
subject remains a stable `RepositoryIdentity` plus an immutable
`GitCommitIdentity` that history may reference but must not redefine;
`deferred:19` default-branch observation was assigned to `S1.P05`, which
`S1.P05.S08` has since carried forward to `S5`, while the historical default
branch stays unknown and owned by `S2`; whole-repository
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
provenance owned by `S1.P09`. At that sealed closure `S1.P05` through `S1.P10`
were not started, and the `S1.P04.S10` closure made `S1.P05` `eligible_to_begin`
while its implementation state was `not_started`. The subjects S08 transferred to
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

`S1.P05` is complete. `S1.P05.S01`, `S1.P05.S02` including the
`S1.P05.S02.C01` correction, `S1.P05.S03`, `S1.P05.S04`, `S1.P05.S05`,
`S1.P05.S06`, `S1.P05.S07`, `S1.P05.S08` including the `S1.P05.S08.C01`
correction, `S1.P05.S09`, and `S1.P05.S10` are complete.
`S1.P06` is active and incomplete; `S1.P06.S01` is complete,
`S1.P06.S02` is complete, `S1.P06.S03` is complete,
`S1.P06.S04` is complete, `S1.P06.S05` is complete,
`S1.P06.S06` is complete, `S1.P06.S07` is complete including the
`S1.P06.S07.C01` correction, `S1.P06.S08` is complete,
`S1.P06.S09` is complete,
`S1.P06.S10` is complete, and `S1.P06.S11` is next and not started.

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

`S1.P02` `deferred:19` default-branch observation was owned by `S1.P05` and
was not implemented by `S1.P05.S01`; `S1.P05.S08` has since carried it forward
to `S5`, and the historical default branch remains unknown and owned by `S2`.
The six `S1.P04` handoff constraints are inherited unchanged, and the published
`S1.P04` contracts, the repository-snapshot v1 corpus, and all
`S1.P00`-`S1.P03` artifacts remain frozen.

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

Three vector files hold 183 vectors over 19 declared fixtures -- 48 valid, 111 invalid,
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

`S1.P05.S10` changed no production source: it published the sealed Phase closure
under `reference_corpus/contracts/development-history/closures/s1-p05-phase-closure`,
recording 97 locks, 12 finalized deferred entries with
`self_owned_open == 0`, 32 non-generalizations, 25 satisfied exit criteria,
and 6 `S1.P06` handoff constraints. It is a sealed publication candidate: it
records no pull request, reviewed head, squash SHA, or natural-main run of its
own, because none exists when its bytes are sealed. Its own publication evidence
lives in Git history, GitHub, and the final execution report.

The `S1.P05` sequence is final. It was evidence-driven rather than fixed at ten
Slices in advance, and closed at ten:

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
10. `S1.P05.S10` — Integration and Phase Closure (complete)

The Issue-to-Pull-Request pairing is retained case material classified as a
reviewed derived interpretation rather than a provider fact, and it is
deliberately not scheduled as an `S1.P05` product relation.

At the sealed `S1.P05.S10` closure, `S1.P06` was `eligible_to_begin` with
implementation state `not_started`, and that closure establishes the readiness
on which `S1.P05` is complete. Eligibility was not commencement, and the sealed
bytes still record the state they recorded. That eligibility has since been
exercised: `S1.P06` implementation has begun with `S1.P06.S01`.

## S1.P06 — Fault Instance Model

`S1.P06` is active and incomplete. `S1.P06.S01` is complete,
`S1.P06.S02` is complete, `S1.P06.S03` is complete,
`S1.P06.S04` is complete, `S1.P06.S05` is complete,
`S1.P06.S06` is complete, `S1.P06.S07` is complete including the
`S1.P06.S07.C01` correction, `S1.P06.S08` is complete,
`S1.P06.S09` is complete,
`S1.P06.S10` is complete, and `S1.P06.S11` is next and not started.

`S1.P06.S01` publishes one new production module, `faultatlas.domain.fault`,
whose initial `__all__` is exactly `FaultInstanceIdentity` and
`FaultRepositoryContext`.

`FaultInstanceIdentity` is a named `RootModel[uuid.UUID]` that names a
caller-designated FaultAtlas knowledge subject, possibly only suspected. It
does not establish that a real-world fault exists, was observed, reproduced,
verified, or repaired, and it decides no same-defect or different-defect
equivalence. UUID assignment and collision are the caller's responsibility: the
value model cannot detect two independent callers reusing one identifier, equal
assigned identifiers are equal within this contract, and no repository or
tenant namespace is silently added. No allocator is published, no identifier is
derived from content, and an identity is not an authorization token or a
security boundary. No Issue, pull request, run, or evidence identity is
converted, matched, deduplicated, alias-merged, or looked up.

The identifier is a UUID as the locked ordinary UUID validator admits it,
including the Nil and Max UUIDs, neither of which is a missing, unknown, or
tombstone sentinel here. No generation version is required or inferred, so no
time or ordering may be read out of an identity. Pydantic's own UUID parser and
serializer are used rather than a second grammar: JSON output is a lowercase
hyphenated string, and the guarantee is a semantic round trip, not preservation
of the spelling accepted on input. Raw identity JSON is a bare scalar and is
not self-describing; untyped interchange or a union of several UUID-rooted
identities will need an explicit owning field or discriminator, which
`S1.P06.S01` deliberately does not publish.

`FaultRepositoryContext` carries exactly `fault` and `repository`, reusing the
published `S1.P01` `RepositoryIdentity` whole with its own child validation and
its own schema version. The context restates no provider, repository
identifier, alias, or schema version, and declares none of its own. Repository
context is separate from logical fault identity, so one fault subject may be
placed in several repository contexts and one repository may hold several fault
subjects. Such a placement asserts no affected, causal, owning, repair, or
applicability repository, no commit membership, no verified fault, no root
cause, no successful reproduction, no repair correctness, and no evidence
support. It carries no role, primary flag, source or evidence field, revision,
time, state, collection, completeness, ordering, or cross-repository
deduplication rule. An identity paired with a repository is not yet a complete
`FaultInstance`.

Both models declare `frozen=True`, `strict=True`,
`revalidate_instances="always"`, and `validate_default=True`; the context adds
`extra="forbid"`, which a `RootModel` has no equivalent of. Narrow
before-validators guard both immediate child positions in Python mode, so a raw
UUID, a string, a mapping, an attribute-backed lookalike, or a foreign model is
refused there while JSON mode reconstructs the declared types normally. A
context therefore round-trips through JSON but deliberately does not accept its
own `model_dump` back as Python input, because those are different input
languages. The module performs no I/O, reads no clock, and consults no registry
or environment.

`S1.P06.S02` extends `faultatlas.domain.fault` in place rather than adding a
module, so production Python sources remain 14 and the module's then-current
`__all__` became exactly `FaultInstanceIdentity`, `FaultRepositoryContext`,
`FaultReportIdentity`, and `SuppliedFaultReport`, in that order: four exports,
which `S1.P06.S03` later extended again. The two `S1.P06.S01` models are
unchanged.

`FaultReportIdentity` is a second, independent named `RootModel[uuid.UUID]`
under the same value-model configuration as `FaultInstanceIdentity`. It names
one caller-designated supplied-report record and is neither a subclass nor an
alias of the fault identity: the two stay nominally distinct even when their
scalars coincide, and nothing requires the scalars to differ. It is not an
external Issue, comment, or provider identity, not an evidence-record, run, or
fault identity, not a digest, and not a security capability. The caller
supplies the UUID; nothing generates, derives, reserves, looks up,
deduplicates, merges, or registers it, Nil and Max are ordinary values, no
generation version is required or inferred, and its JSON is the same bare
scalar string with no wrapper. Equality is equality of the assigned value
within this contract and establishes no same-source-report equivalence; no
collision or global-uniqueness policy exists.

`SuppliedFaultReport` is a frozen, strict, extra-forbidding `BaseModel`
carrying exactly `report`, `context`, `problem_statement`, and
`behavioral_deviation`, in that order. It consumes the published
`FaultRepositoryContext` whole, so the fault subject of a report is
`report.context.fault` and no fault, repository, provider, repository
identifier, or schema version is restated at report level. Both texts are
required caller-supplied prose of one to 4096 characters: leading or trailing
whitespace is refused rather than trimmed, whitespace-only text therefore
fails, text that cannot encode as UTF-8 is refused, and admitted Unicode and
interior whitespace including newlines are preserved exactly with no
lowercasing, normalization, parsing, tokenizing, classification, or rewriting.
The two texts may be identical, and the deviation text may describe returned
values, exceptions, side-effect count or ordering, callback or event ordering,
resource or timing behavior, or any combination without a closed
deviation-kind vocabulary. The 4096 limit is a character bound of this
internal contract, not a durable `S1.P10` byte-format promise.

A report and its deviation are supplied claims, not verification. Creating one
means only that the caller supplied this report identity, placed its fault
subject in this repository context, and supplied these two texts; a report may
describe a suspected, latent, unreproduced, unfixed, or cause-unknown problem.
It implies no affected repository, no existing fault, no executed or observed
deviation, no external reporter's words, no originating Issue or pull request,
no FaultAtlas verification, no known cause, no existing or correct repair, no
failed before-run or passed after-run, no reviewed expected property, and no
evidence support. `S1.P06.S02` publishes no run, outcome, expected-property,
root-cause, confidence, review, repair-candidate, source-relationship,
evidence-link, scenario, or environment model, no reusable pattern or
invariant, and no complete `FaultInstance`; those were taken up by
`S1.P06.S03` through `S1.P06.S09` and the rest remain owned by `S1.P07`,
`S1.P09`, and `S1.P10`. The two model-valued child positions are
guarded against untyped Python input exactly as the context's are, the raw
text fields carry no nominal guard, and a report round-trips through JSON
while refusing its own `model_dump` as Python input.
The module still performs no I/O.

`S1.P06.S03` extends `faultatlas.domain.fault` in place as well, so production
Python sources remain 14 and the module's current `__all__` is exactly
`FaultInstanceIdentity`, `FaultRepositoryContext`, `FaultReportIdentity`,
`SuppliedFaultReport`, `FaultScenarioIdentity`, `FaultOccurrenceIdentity`,
`SuppliedFaultScenario`, and `SuppliedFaultOccurrenceContext`, in that order:
eight exports. The `S1.P06.S01` and `S1.P06.S02` models are unchanged.

`FaultScenarioIdentity` and `FaultOccurrenceIdentity` are two further
independent named `RootModel[uuid.UUID]` values under the same value-model
configuration, neither a subclass nor an alias of each other or of the fault
and report identities. All four stay nominally distinct even when their
scalars coincide, and no cross-type scalar uniqueness is required. The caller
assigns each UUID; nothing generates, derives, reserves, looks up,
deduplicates, merges, or registers one, Nil and Max are ordinary values, no
generation version is required or inferred, and each serializes as the same
bare scalar string with no wrapper. An occurrence identity is not a test-run
identity, a CI run, a provider event, an evidence record, a timestamp, or a
digest, and an explicit occurrence identity exists precisely so that two
claimed occurrences carrying identical text remain two occurrences.

`SuppliedFaultScenario` carries exactly `scenario`, `report`, and
`scenario_statement`, consuming the published `SuppliedFaultReport` whole, so
the fault subject stays reachable at `scenario.report.context.fault` and no
fault, repository, report identity, problem statement, or behavioral deviation
is restated at scenario level. The statement is case-local supplied prose
about triggering conditions, inputs, operation, runtime setting,
repository-local conditions, environment, configuration, or preconditions. It
is not parsed into platform, language, operating-system, version,
architecture, trigger, input, or environment fields: structured reusable
applicability is `S1.P08` work, and a scenario here is case-local context, not
a cross-instance applicability rule.

`SuppliedFaultOccurrenceContext` carries exactly `occurrence`, `scenario`, and
`occurrence_context`, consuming the scenario whole. It is a caller-supplied
positive claim that one particular manifestation was encountered under that
scenario. A scenario answers under what supplied conditions a report is
relevant; an occurrence context answers what distinct supplied occurrence is
claimed under them; the `S1.P06.S02` behavioral deviation answers what
behavior is claimed to differ. None of those texts is required to differ from
another and none is compared with another.

Both are supplied claims, not verification. An occurrence context is not an
execution run and does not establish that FaultAtlas observed or reproduced
anything, that a test was run, that code was executed, that an output was
collected, that an exception happened in a FaultAtlas-controlled process, that
the report was proven, that the scenario was exhaustively specified, that a
cause is known, that a repair works, or that evidence supports the claim. Test
material, run identity, reported execution outcome, before-and-after
comparison, timeout, environment-start, flakiness, run independence, and
fail-to-pass or regression-safety semantics became `S1.P06.S06` work, and two
differing occurrence identities are not evidence that two independent runs
happened.

Occurrence is an optional separate record rather than a flag, so a report may
stand alone, may carry one scenario or several, and a scenario may carry no
occurrence, one, or several. A suspected, latent, or unreproduced fault
therefore never has to invent an occurrence, and no boolean says whether the
fault occurred. The absence of an occurrence record means only that none is
present in this composition: not that the fault is known not to have occurred,
nor that occurrence is impossible, inapplicable, unavailable, or disproved,
and no sentinel, status, or `None` stands for any of those.

`S1.P06.S03` records no time for a claimed occurrence. A fault occurrence may
have no known precise instant, and no occurred-at, observed-at, reported-at,
reproduced-at, started-at, or ended-at field exists. The published `S1.P05`
`PullRequestHistoricalOccurrenceTime` is a source instant for an already
published pull-request history fact; it is neither reused, imported, aliased,
nor reinterpreted here and is not a generic fault-occurrence time. A positive
chronology relation is later work needing a concrete consumer and explicit
missing-state semantics first.

Both new texts are required supplied prose of one to 4096 characters under the
same rule as the `S1.P06.S02` texts: leading or trailing whitespace is refused
rather than trimmed, whitespace-only text fails, text that cannot encode as
UTF-8 is refused, and admitted Unicode and interior whitespace including
newlines are preserved exactly with no lowercasing, normalization, parsing,
tokenizing, or classification. The rule is stated separately on each field
rather than through a shared public alias or generic prose framework, and the
4096 limit is a character bound of this internal contract, not a durable
`S1.P10` byte-format promise. The two model-valued child positions of each new
record are guarded against untyped Python input exactly as their predecessors
are, an embedded record is revalidated under its own published schema, the raw
text fields carry no nominal guard, and each record round-trips through JSON
while refusing its own `model_dump` as Python input. Neither model consults a
registry: two records carrying one scenario or occurrence identity with
differing contents are not reconciled here, and `S1.P06.S03` published no
source relationship, evidence link, root cause, repair, confidence, review,
reusable pattern or invariant, and no complete `FaultInstance`. The bounded
source and history relationships came next, in `S1.P06.S04`, and the repair
candidates in `S1.P06.S05`; the evidence link became `S1.P06.S09` work, and
the rest remain owned by `S1.P07`, `S1.P08`, `S1.P09`, and `S1.P10`. The
module still performs no I/O.

`S1.P06.S04` adds one new production module,
`faultatlas.domain.fault_source_relationship`, whose `__all__` is exactly
`FaultReportSourceObjectAssociation` and `FaultReportHistoryFactAssociation`,
so production Python sources move from 14 to 15. It is a cross-domain bridge
from the fault domain to the published `S1.P01` source-object identities and to
the bounded `S1.P05` history facts. `faultatlas.domain.fault`,
`faultatlas.domain.identity`, `faultatlas.domain.history`, and
`faultatlas.domain.history_evidence_link` are unchanged by it and none of them
imports it.

Both models carry exactly two fields and one deliberately weak, uniform
meaning: the caller associates these two supplied values. Each anchors on the
published `SuppliedFaultReport` rather than on a bare `FaultInstanceIdentity`,
because an identity alone is only a caller-designated subject while the report
is the smallest published value carrying the caller's problem statement and
behavioral deviation. The fault subject stays reachable at
`association.report.context.fault`, nothing is restated at association level,
and a suspected or unreproduced report needs no scenario and no occurrence
record before it can carry either association.

`FaultReportSourceObjectAssociation` carries `report` and `source_object`,
admitting exactly `NumberedSourceObjectIdentity` and
`ProviderScopedSourceObjectIdentity`, which are reused whole and together cover
every published `S1.P01` object kind: issue, pull request, issue comment, pull
request comment, pull request review, pull request review comment, and timeline
event. A bare `RepositoryIdentity` is not admitted, because repository
placement is already carried by the report's own `FaultRepositoryContext`, and
no commit, tree, blob, ref, or path identity is admitted. The source object's
repository is deliberately not required to equal `report.context.repository`: a
cross-repository association is accepted and infers no affected repository, no
origin repository, no ownership, no causation, and no applicability.

`FaultReportHistoryFactAssociation` carries `report` and `history_fact`,
admitting exactly the same six published facts the `S1.P05.S07` evidence link
admits — `PullRequestRevisionRoleBinding`, `PullRequestChangedPath`,
`PullRequestReviewRevisionApproval`, `PullRequestMergeRevisionOutcome`,
`PullRequestHeadRefDeletion`, and `PullRequestHistoricalOccurrenceTime` —
reused whole with no `S1.P05` field, enum, role, revision, timestamp, path, or
source identity redefined. Three published symbols are excluded for three
distinct reasons that are not collapsed into one: `ChangedPathStatus` is a
closed vocabulary rather than a fact; `PullRequestChangeSet` is outside the
`S1.P05.S07` fact boundary because its base and head composition, path tuple,
and supplied order are caller-composed with no retained record establishing
completeness, and `S1.P06.S05` may consume it explicitly later rather than have
this Slice move that boundary silently; and
`PullRequestHistoryFactEvidenceLink` is itself the `S1.P05` evidence
association, which nesting here would blur with source association and risk
implicitly upgrading.

Association is not proof, support, causation, or repair correctness. A source
association does not say why the object is related and establishes no
origination, evidence support, verification, independent observation,
reproduction, cause, contained repair, primacy, or authority, so no `role`
field guesses among them. A history association does not mean the fact proves
the fault, is causally responsible, is a repair, or that a merge fixed
anything; approval is not FaultAtlas confidence, a changed path is not an
affected path, a deleted head ref caused nothing, and a source occurrence
instant is not a fault-occurrence instant. The `S1.P05.S07` LEVEL-1 evidence
association is neither reached nor upgraded, and the embedded fact keeps
exactly its own published semantics.

No relationship vocabulary is created. There is no relationship kind or type,
no subject-predicate-object triple, no graph node or edge, no inverse,
transitive, or completeness semantics, no relationship identifier or registry,
and no source-object-to-source-object relation is created. The published
`S1.P01` `ProviderScopedSourceObjectIdentity` already carries its own `parent`
numbered object, so a review admitted at `source_object` reaches the pull
request containing it; that containment is predecessor semantics `S1.P06.S04`
neither creates, extends, nor reads. Two independent associations from one
report to Issue #4412 and to pull request #4414 therefore construct no
Issue-to-pull-request pairing and imply none: the retained pairing stays a
reviewed derived interpretation, and sharing one report is not a transitivity
rule. No ancestry or reachability graph and no complete development history is
owned here, and the `S1.P05` contracts and the development-history v1 corpus
stay frozen.

Each association is one value, so one report may hold associations to several
sources and independently to several history facts, and one source object may
be associated with two reports whose embedded fault identities differ without
merging those two fault subjects. No collection, ordering, uniqueness rule, or
precedence exists, absence of an association asserts only that none is supplied
here rather than that a relation is absent, unknown, unavailable, or disproved,
and equality is ordinary Pydantic model equality with no override. Both models
declare `frozen=True`, `extra="forbid"`, `strict=True`,
`revalidate_instances="always"`, and `validate_default=True`; every
model-valued position is closed to untyped Python input, including both union
positions, where strictness alone cannot express the closure; JSON reconstructs
the published children normally so each value round-trips through JSON while
refusing its own `model_dump` as Python input; and one narrow private transport
guard decodes the occurrence-time member's instant leaf through the same
aware-datetime grammar the published model applies to JSON. The module performs
no I/O.

`S1.P06.S04` implements the bounded relationship responsibility the effective
`S1.P05.S08` and `S1.P05.S08.C01` handoff assigns to `S1.P06`, publishing two
named associations and no relationship vocabulary: it owns the bounded
domain relationships `FaultInstance` needs and consumes the bounded
`S1.P05` history facts without redefining them, while owning no generic Git
ancestry or reachability graph, reading `S1.P05` as no complete development
history, and implicitly upgrading no LEVEL-1 evidence association. Formal
disposition and readiness for the inherited subject became `S1.P06.S10`
work.

`S1.P06.S05` adds one new production module, `faultatlas.domain.fault_repair`,
whose `__all__` is exactly `FaultRepairCandidateIdentity`,
`SuppliedFaultRepairCandidate`, `FaultRepairCandidateRevisionAssociation`, and
`FaultRepairCandidateChangeSetAssociation`, in that order, so production Python
sources move from 15 to 16. `faultatlas.domain.fault`,
`faultatlas.domain.fault_source_relationship`, `faultatlas.domain.history`, and
`faultatlas.domain.revision` are unchanged by it and none of them imports it.

`FaultRepairCandidateIdentity` is a fifth independent named
`RootModel[uuid.UUID]`, neither a subclass nor an alias of the fault, report,
scenario, or occurrence identities, and all five stay nominally distinct even
when one scalar is assigned to all five. The caller assigns the UUID; nothing
generates, derives, reserves, looks up, deduplicates, merges, or registers one,
and no identifier is derived from a pull-request number, a commit digest,
change-set content, a report identity, or a fault identity. Nil and Max are
ordinary values, no generation version is required or inferred, the JSON form is
the ordinary bare UUID string with no wrapper or adapter, and equality, hashing
and ordering are left as Pydantic defines them.

`SuppliedFaultRepairCandidate` carries exactly `candidate`, `report`, and
`repair_statement`, consuming the published `SuppliedFaultReport` whole, so the
fault subject stays reachable at `candidate.report.context.fault` and no fault,
repository, report identity, problem statement, or behavioral deviation is
restated at candidate level. The statement is supplied prose of one to 4096
characters under the `S1.P06.S02` rule: leading or trailing whitespace is
refused rather than trimmed, whitespace-only text fails, and admitted Unicode
and interior whitespace including newlines are preserved exactly with no
normalization, parsing, or classification.

A repair candidate is a proposal, not an outcome. Designating one establishes no
known root cause, no implementation, no application, no merge, no deployment, no
passing test, no avoided regression, no fixed fault, and no evidence support, and
no status, confidence, correctness, verification, review, or outcome field
exists. It requires no scenario and no occurrence, so a proposal may be made
about a suspected, latent, unreproduced, or cause-unknown report, and it requires
no root cause either: a repair may target an observed behavioral deviation while
the cause is still unknown, which is why no cause, explanation, or hypothesis
field exists. Test material, reported outcomes and comparability became
`S1.P06.S06` work, case-local explanation and hypothesis became `S1.P06.S07`
work, the fault-evidence bridge became `S1.P06.S09` work, and generic review,
support and confidence calculus remains `S1.P09` work.

A candidate is complete without any implementation. `S1.P06.S05` separates the
proposal from the concrete material deliberately, so a purely conceptual
candidate carrying no revision and no change set is a valid value, which is what
a not-yet-implemented repair looks like. Absence of an implementation
association means only that none is supplied here: not that the repair is
impossible, rejected, abandoned, known to be unimplemented, or incorrect, and no
boolean, status, or sentinel stands for any of those.

`FaultRepairCandidateRevisionAssociation` carries exactly `candidate` and
`revision`, reusing the published `S1.P02` `GitCommitIdentity` whole and
intrinsically. It records only that the caller associated that commit with that
candidate, and asserts no repository membership, no reachability, no
pull-request head, no merge revision, no application, no deployment, no fixed
fault, no passing test, no completeness, and no exclusivity, so no
repository-membership, role, head, merge, applied, or fixed field exists.

`FaultRepairCandidateChangeSetAssociation` carries exactly `candidate` and
`change_set`, and this is the Slice that deliberately consumes the published
`S1.P05` `PullRequestChangeSet`. Consuming it changes nothing about it: the
embedded value keeps its published base and head bindings, its one to 4096
supplied changed paths in the caller's supplied order, its distinct base and head
revisions, its single hash algorithm, and its unique paths. It does not become a
complete diff or a verified repair by being associated, and the association
asserts neither that every path relevant to the repair is present, nor that every
path in the set is affected by the fault, nor that the head revision fixes
anything, nor that the pull request merged, nor that a merge was correct, nor
that the changed paths are evidence, nor that base-side blobs are known, nor that
the set is provider-complete.

The `S1.P05.S07` evidence boundary is untouched. `PullRequestChangeSet` remains
excluded from `PullRequestHistoryFactEvidenceLink` and from the `S1.P06.S04`
`FaultReportHistoryFactAssociation`, because no retained record establishes its
completeness; `S1.P06.S05` admits it under a different relation whose meaning is
a repair proposal's supplied material rather than a history fact or an evidence
association. Nothing in the module reaches the evidence layer, and no evidence
record, support, source, origin, rationale source, confidence, or review field
exists on any of the three records.

A candidate, a revision, a change set, and a pull request are four different
things and none is an identity of another. A pull request may contain one
candidate, several, unrelated changes, or no valid repair at all; a commit may
implement all, part, or none of a candidate; and a change set describes supplied
changes between one pull request's base and head rather than being the candidate
itself.

No coherence calculus over several associations exists. If a caller supplies both
a revision association and a change-set association for one candidate,
`S1.P06.S05` does not require the associated revision to equal the change set's
head revision: it may be an intermediate revision, the head, a later one, or any
other commit the caller chose. A candidate change set's pull-request repository is
likewise not required to equal the report's repository context. No value here has
the aggregate authority to say which associations form one complete candidate
record, which became `S1.P06.S08` work on bounded `FaultInstance` composition
and reference integrity.

`S1.P06.S05` adds no candidate-to-source-object relation, since `S1.P06.S04`
already publishes the weak report-to-source and report-to-history associations
and candidate provenance belongs to later evidence and composition work. A report
associated with a pull request and a candidate associated with a change set drawn
from that same pull request compose into no third claim: there is no transitivity
rule and neither association supports the other.

Multiplicity is expressed by holding several values rather than by any published
collection. One report may carry several candidates whose identities differ, and
identical repair prose does not merge them; one candidate may carry several
revision and several change-set associations; and one revision or change set may
be associated with candidates belonging to different fault reports without
merging those candidates or fault subjects. No collection, ordering, uniqueness
rule, registry, precedence, or completeness claim exists. Every model-valued
position is closed to untyped Python input and is not bypassed by
`from_attributes=True`, JSON reconstructs the declared children normally so each
record round-trips through JSON while refusing its own `model_dump` as Python
input, and the module performs no I/O.

`S1.P06.S06` adds one new production module, `faultatlas.domain.fault_test`,
whose `__all__` is exactly `FaultTestMaterialIdentity`,
`SuppliedFaultTestMaterial`, `FaultTestRunIdentity`, `ReportedFaultTestRun`,
`ReportedFaultTestOutcomeKind`, `ReportedFaultTestOutcome`,
`FaultTestRunRevisionAssociation`, and `ReportedFaultTestComparison`, in that
order, so production Python sources move from 16 to 17.
`faultatlas.domain.fault`, `faultatlas.domain.fault_repair`,
`faultatlas.domain.fault_source_relationship`, `faultatlas.domain.revision`,
`faultatlas.domain.history`, and `faultatlas.domain.evidence` are unchanged by it
and none of them imports it.

`S1.P06.S06` keeps four things apart that are easy to collapse: what test
material a caller has in mind, that a caller reports having attempted a run of
it, what disposition that attempt reportedly reached, and how one reported
outcome compares with another. Test material is not a run, so a regression test,
a reduced reproduction, a manual procedure, a test command concept, or a
property-oriented check can be described with no run and no outcome anywhere. A
run is not its outcome, so a caller may report an attempt while supplying no
outcome record at all.

Everything the Slice publishes is caller-reported knowledge. FaultAtlas executes
no analyzed repository here: it starts no process, runs no command, and observes
no verdict, so a reported run is a claim that someone says they attempted
something and a reported outcome is a claim about how that attempt reportedly
ended. Neither is a FaultAtlas observation and neither may later be read as one;
any separately authorized execution must publish a distinct value rather than
silently reuse these.

`FaultTestMaterialIdentity` and `FaultTestRunIdentity` are two further
independent named `RootModel[uuid.UUID]` values, so all seven `S1.P06`
UUID-rooted identities stay nominally distinct even when one scalar is assigned
to all seven. The caller assigns each UUID; nothing generates, derives, reserves,
looks up, deduplicates, merges, or registers one, Nil and Max are ordinary
values, and each serializes as the bare UUID string. A run identity is not an
acquisition run: the published `S1.P03` `AcquisitionRunId` describes evidence
retrieval, and `S1.P06.S06` neither imports, reuses, aliases, nor reinterprets
it. Nor is a run identity a CI workflow run, a provider-side run, or an
execution performed here, and the word "run" does not even guarantee that the
test body started.

`SuppliedFaultTestMaterial` carries exactly `material`, `report`, and
`test_statement`, consuming the published `SuppliedFaultReport` whole so the
fault subject stays reachable at `test_material.report.context.fault`. It
requires no scenario, occurrence, repair candidate, or run, and it establishes no
repository presence, no retained test bytes, no inspected locator, no execution,
no sufficiency, no reproduction, no evidence, and no regression completeness. It
is a knowledge object about a procedure rather than captured code, so no source
or evidence field exists; the fault-evidence bridge became `S1.P06.S09` work,
which associates such a record from outside rather than adding a field here,
and durable byte contracts remain `S1.P10` work.

`ReportedFaultTestRun` carries exactly `run`, `test_material`, and
`run_statement`, consuming the material whole. The statement is opaque prose
about the attempted execution context and is deliberately not parsed into
operating system, platform, architecture, environment, command, dependency
version, or runtime version fields. No outcome is attached to the run record and
no time is recorded.

`ReportedFaultTestOutcomeKind` is a bounded seven-member vocabulary for a
caller-reported execution disposition, not a claim that every testing framework
uses these states: `passed` and `failed` are the two terminal verdicts, `errored`
reports that execution began or progressed but ended in an error rather than a
verdict, `timed_out` that the attempt exceeded its time bound without one,
`skipped` that the test system's own disposition did not execute it,
`did_not_start` that environment, setup, or launch conditions prevented execution
from starting, and `cancelled` that the attempt was cancelled without reaching
`passed` or `failed`. No `unknown`, `flaky`, `regression_safe`, `fixed`, or
`verified` member exists. An unsupplied outcome is the absence of an outcome
record rather than a member of the enum, flakiness is an interpretation over
several reported runs rather than one run's terminal disposition, and regression
safety and repair correctness are not outcome kinds.

Absence is not a disposition. That no outcome record is supplied for a run means
only that none is supplied here: it reports neither failure, pass, timeout, skip,
nor a never-started run, and not that the result is unknown as a positive claim.

`ReportedFaultTestOutcome` carries exactly `run`, `outcome`, and
`outcome_statement`. It does not mean FaultAtlas witnessed the run, that the
report or the repair candidate is correct, or that evidence supports it, and it
carries no evidence, confidence, review, or correctness field. Two outcome
records may name one run and disagree; this layer neither resolves nor flags
that: composing conflicting reported knowledge became `S1.P06.S08` work, and
reviewing it remains `S1.P09` work.

`FaultTestRunRevisionAssociation` carries exactly `run` and `revision`, reusing
`GitCommitIdentity` whole and intrinsically, and claims no repository membership,
reachability, base, head, or merge role, repair candidate, before or after role,
application, deployment, or test correctness. A run may carry no revision
association at all, which is what an unavailable or simply unsupplied revision
looks like, so no `None` and no fabricated revision is required; a run may
equally carry several, and this layer has no authority to reconcile them.

`ReportedFaultTestComparison` carries exactly `before`, `after`, and
`comparison_statement`, under exactly two rules: the two outcomes must name
distinct run subjects, since one run cannot occupy both roles, and their runs
must carry the same full supplied test material value, compared as whole records
rather than identity scalars, so two runs whose material identities agree while
their content disagrees are not silently accepted. Nothing else is inferred: no
timestamp is required or read, the roles are supplied rather than derived from
chronology, and no repair candidate, run-revision association, environment
equality, independent execution, shared machine or process, causation, or
regression safety is required or implied.

Fail-to-pass is not regression safety. A comparison whose outcomes happen to be
`failed` then `passed` contains a reported fail-to-pass pattern for one test
material and nothing more, which is why no `fail_to_pass`, `repair_success`, or
`regression_safe` field is published: one failing test becoming passing
establishes neither that unrelated tests still pass, nor that no new regression
exists, nor that the repair candidate or the root cause is correct. A wider
regression claim would need its own independently reported material and outcomes.

A missing before run is not a before failure. Without a before outcome record no
comparison can be constructed, and none is synthesised, so a later passing run
never manufactures an earlier `failed`. A missing before run, a missing before
outcome, and before outcomes of `did_not_start`, `failed`, `errored`, or
`timed_out` are six distinct situations and are never flattened. For the same
reason a `did_not_start` to `passed` comparison is not a `failed` to `passed`
transition, and neither `timed_out` to `passed` nor `errored` to `passed` is that
transition either.

Distinct run identities are not an independence guarantee. The comparison
requires them because one run cannot fill both roles, not because two identities
prove independent processes, environments, evidence sources, or statistically
independent trials, and identical outcome or run prose may appear across distinct
runs without merging them. Every model-valued position, the outcome position
included, is closed to untyped Python input and is not bypassed by
`from_attributes=True`; JSON reconstructs the declared children and the enum
lexeme normally so each record round-trips through JSON while refusing its own
`model_dump` as Python input; and the module performs no I/O.

`S1.P06.S07` adds one new production module,
`faultatlas.domain.fault_interpretation`, whose `__all__` is exactly
`FaultExplanationIdentity`, `SuppliedFaultExplanation`,
`FaultHypothesisIdentity`, `SuppliedFaultHypothesis`,
`FaultExpectedPropertyIdentity`, and `SuppliedFaultExpectedProperty`, in that
order, so production Python sources move from 17 to 18.
`faultatlas.domain.fault`, `faultatlas.domain.fault_repair`,
`faultatlas.domain.fault_source_relationship`, `faultatlas.domain.fault_test`,
`faultatlas.domain.revision`, `faultatlas.domain.history`, and
`faultatlas.domain.evidence` are unchanged by it and none of them imports it.

`S1.P06.S07` publishes three independent case-local knowledge categories about
one published fault report, because they are three different epistemic acts. An
explanation is an account a caller offers of why or how the reported behavioral
deviation arises. A hypothesis is a proposition a caller explicitly retains as
tentative. An expected property is a statement of behavior a caller says ought
to hold for this report. All three anchor on one `SuppliedFaultReport` consumed
whole, so the fault subject stays reachable through the report and no fault,
repository, report identity, problem statement, or behavioral deviation is
restated.

`FaultExplanationIdentity`, `FaultHypothesisIdentity`, and
`FaultExpectedPropertyIdentity` are three further independent named
`RootModel[uuid.UUID]` values, so all ten `S1.P06` UUID-rooted identities stay
nominally distinct even when one scalar is assigned to all ten. The caller
assigns each UUID; nothing generates, derives, reserves, looks up, deduplicates,
merges, or registers one, Nil and Max are ordinary values, and each serializes
as the bare UUID string.

An explanation is a supplied explanatory claim, not a promoted fact. It may
carry a root-cause-shaped account, and doing so establishes no root cause and
records no acceptance, review, support, or verification, which is why no
`root_cause`, `accepted`, `verified`, `confidence`, or `review` field exists and
why an explanation is never more probable than a hypothesis about the same
report. A hypothesis stays explicitly tentative merely by being represented in
that position, and carries no `confirmed`, `rejected`, `supported`, `disproved`,
`probability`, `confidence`, `review`, or `evidence` field, so it cannot record
its own resolution; a hypothesis used as fixture material is a supplied
proposition there too, never a historical fact promoted by appearing in a test.

An expected property is case-local. Its carrier scopes it to exactly one
supplied fault report, so it is not a passing test, a verified invariant, a
universal program law, a cross-instance pattern, a repair acceptance criterion,
or proof that the current behavior is wrong. Cross-instance generalization into
patterns and invariants is `S1.P07` work and is not begun here. No prose is
parsed, scope-checked, or classified anywhere in the module, so breadth of
phrasing is not breadth of claim.

The three kinds do not convert into one another: there is no promotion,
lifecycle, or transition from hypothesis to explanation or back, and the same
prose may appear in two of them while the records stay distinct because they
carry different identities and different epistemic roles. One report may carry
none, one, or several of each kind independently, including explanations or
hypotheses that contradict each other, and this layer chooses no winner, so
no uniqueness, precedence, replacement, supersession, or conflict resolution
exists.
Nothing requires a reproduction, scenario, occurrence, repair candidate, test
material, reported run, or reported outcome to exist first.

Nothing is inferred from the repair or test layers. A repair candidate does not
make an explanation true, a candidate revision does not make a root cause known,
a reported `failed` to `passed` comparison neither confirms an explanation nor
verifies an expected property, a reported `passed` outcome does not satisfy an
expected property universally, a later reported success does not disprove an
earlier hypothesis, and a merge accepts nothing. The module publishes no
relation to repair candidates, test material, runs, outcomes, comparisons,
source objects, history facts, or evidence records, and co-presence manufactures
none. Bounded composition and reference integrity became `S1.P06.S08` work.

All three records are frozen, strict, extra-forbidding and always-revalidating,
close both model-valued positions to untyped Python input without being
bypassed by `from_attributes=True`, declare no input or output alias, admit no
optional or nullable field, round-trip through JSON while refusing their own
`model_dump` as Python input, and perform no I/O.

`S1.P06.S07.C01` corrects roadmap lifecycle narrative without changing any
published contract. It adds no production module, revises no `S1.P06.S01`
through `S1.P06.S07` semantics, and does not move the live gate, which stays
`S1.P06.S08`. A whole-roadmap sentence-local audit reconciled every
present-tense lifecycle and ownership statement against the current state and
found one stale claim: the `S1.P05.S01` narrative still named `S1.P05` as the
present owner of the `S1.P02` `deferred:19` default-branch observation,
although `S1.P05` is complete and `S1.P05.S08` had carried that subject forward
to `S5`. The claim had stood since `S1.P05.S08` itself, which introduced the
carry-forward statement beside it. The clause is now past tense and names the
current owner. Correct later ownership was left exactly as it stood:
confidence, review and interpretation provenance were still owned by
`S1.P09`, the fault-evidence bridge was still owned by `S1.P06.S09`, durable
byte contracts were still owned by `S1.P10`, pattern and invariant
generalization was still owned by `S1.P07`, and the repository-graph and
ingestion subjects were still owned by `S5` and `S2`. The correction also
publishes `tests/test_roadmap_lifecycle_consistency.py`, which owns this
cross-Slice narrative rule sentence-locally. Two diverged copies of that rule
are removed from the product Slice oracles, which keep their own
product-specific roadmap facts.

`S1.P06.S08` adds one new production module,
`faultatlas.domain.fault_instance`, whose `__all__` is exactly `FaultInstance`,
so production Python sources move from 18 to 19. It is the first aggregate in
the Phase, and it composes the values `S1.P06.S01` through `S1.P06.S07`
published without redefining any of them; those modules are unchanged by it and
none of them imports it.

The logical subject is the fault, not a report. One fault may be described by
more than one supplied report, so the aggregate carries a
`FaultInstanceIdentity` and one or more reports whose own
`report.context.fault` equals it, keeping logical fault identity, report
identity and repository context three separate things. Reports for one fault
may carry different repository contexts, and composing them claims no
cross-repository applicability. A minimal instance is one identity and one
substantive report; an identity alone is not a fault instance, and every
later component is optional.

An absent collection means only that this composition carries no values of that
category. It does not mean that none exists, that a search was performed, or
that anything is unavailable, unsupported, impossible or disproved, so an
omitted collection and an explicitly empty one are the same value, `None` is
refused, and no completeness, exhaustiveness or resolution field exists.

Reference integrity is by whole published record rather than by matching an
embedded identifier, because two records may carry one subject identity while
disagreeing in their supplied content and a scalar match would silently choose
one of them. A dangling reference is refused rather than repaired: nothing is
auto-inserted from the value that referenced it. Within one composition each
primary subject identity occurs at most once in its own collection, whether the
two records are identical or contradictory; that is local composition integrity
and not a global registry, it is per nominal identity type so one scalar may
still name a fault and a run at once, and collections without a subject
identity of their own carry no uniqueness rule.

Conflicts survive composition. Two outcome records may name one run and
disagree, several explanations or hypotheses may contradict each other about
one report, and several repair candidates may address one report; this layer
neither rejects the conflict, chooses a winner, marks a run flaky, nor derives
a confidence, since reviewing conflicting reported knowledge is `S1.P09` work.

Reference closure creates no semantic edge a predecessor did not publish. A
pull request associated with a report does not support a candidate carrying a
change set from it, a candidate revision equal to a run revision does not make
the run a test of the candidate, a `failed` to `passed` comparison does not
make a repair correct, and a passing outcome does not verify an expected
property. Nothing requires a candidate revision to equal a change set's head, a
run revision to equal a repair revision, or a source object's repository to
equal its report's.

Order is preserved exactly as supplied and carries no priority, confidence,
causality, chronology or ownership; nothing is sorted or canonicalised, and
canonical durable ordering remains `S1.P10` work. No evidence is consumed by
the aggregate. The
fault-evidence bridge became `S1.P06.S09` work, which publishes it as a
separate cross-domain value and adds no field here, so `FaultInstance` is
unchanged by it, and the `S1.P06.S04` associations stay weak associations
rather than becoming support. Each
collection is bounded to a fixed private maximum that limits one in-memory
composition and is neither a claim about how many records may exist nor a
durable-format limit. The aggregate is frozen, strict, extra-forbidding and
always-revalidating, closes the composed subject and every collection to
untyped Python input, and performs no I/O. The subject needs its own guard:
a `RootModel` field reconstructs from its own root type even under strict
validation, so a bare UUID would otherwise be accepted where a published
identity is meant.

`S1.P06.S09` adds one new production module,
`faultatlas.domain.fault_evidence_link`, whose `__all__` is exactly
`FaultInstanceEvidenceLink`, so production Python sources move from 19 to 20.
It publishes one frozen strict record of exactly three fields --
`fault_instance`, `subject`, `evidence_record` -- and nothing else.

The relation is weak and uniform, and it is the same association strength the
published `S1.P04` and `S1.P05` evidence links already carry: a link records
that its caller associated one record already composed inside one supplied
`FaultInstance` with one already published durable evidence-record reference.
It does not claim that FaultAtlas read the record, that the record contains,
supports, corroborates or proves the subject, that the subject was observed in
that record or derived from it, or that the subject is true, verified or
independently reproduced. It raises no confidence, confirms no hypothesis,
accepts no explanation, establishes no repair as correct, and records no
support role, strength, status, review state or verification outcome. Generic
support, confidence and review calculus remains `S1.P09` work.

The subject position admits exactly eleven substantive `S1.P06` record types
and no others: `SuppliedFaultReport`, `SuppliedFaultScenario`,
`SuppliedFaultOccurrenceContext`, `SuppliedFaultRepairCandidate`,
`SuppliedFaultTestMaterial`, `ReportedFaultTestRun`,
`ReportedFaultTestOutcome`, `ReportedFaultTestComparison`,
`SuppliedFaultExplanation`,
`SuppliedFaultHypothesis`, and `SuppliedFaultExpectedProperty`. Each is reused
whole and gains no field. The exclusions are the boundary rather than an
oversight. `FaultInstance` itself is excluded, because it is a caller's bounded
composition rather than a substantive claim and attaching a record to it would
attach evidence to the act of composing. `FaultInstanceIdentity` and every
other identity are excluded, because a name is not a record. The five
association records `S1.P06.S04` through `S1.P06.S06` publish are excluded,
because they are themselves weak caller-declared relations and evidence
attached to a relation about records rather than to the records would be a
claim about the caller's own act of associating. The published
`PullRequestHistoryFactEvidenceLink` and `RepositorySnapshotFactEvidenceLink`
are excluded and each remains the authority for its own domain, and
`PullRequestChangeSet` with the repository, snapshot and history aggregate
values are excluded because they are not `S1.P06` knowledge records.

The subject must already be an exact member of the supplied composition, and
membership is by whole published record exactly as `S1.P06.S08` decides its own
reference integrity. Two records may carry one subject identity while
disagreeing in their supplied content, so matching an embedded UUID, report
identity, run identity or subject identity would silently associate a record
the caller never supplied; a same-identity record differing anywhere else is
refused. Each admitted type is checked against the one collection that carries
it. Nothing is auto-inserted, and the supplied composition is never mutated or
reconstructed.

No association chaining exists, and that boundary is load-bearing. A report
associated with a history fact, where the same fact is elsewhere associated
with a durable record, is not thereby associated with that record. A report
associated with a pull request and a repair candidate carrying a change set
from it manufacture no evidence linkage for the candidate. Every chain stays
exactly as long as the links a caller explicitly supplied, and no link of this
type is ever derived, inferred, computed or returned; constructing one is a
separate deliberate act.

The record is referenced as one whole durable record. No evidence identifier,
strength, support role, confidence, verification state, kind, field pointer,
JSON pointer, semantic path, byte span, locator, artifact path or request
exists, and the link does not say where inside the record the subject can be
found. Each link carries one subject and one record; associating one subject
with several records is several independent links, one record may be
associated with several subjects, two identical links are equal values, and no
registry, collection, ordering, precedence, uniqueness, deduplication or
completeness semantics over multiple links exists. Absence of a link means only
that none is supplied, never that a subject is unsupported, that no evidence
exists, that a search was performed, or that anything was disproved.

`FaultInstance` is unchanged. Its exact seventeen-field surface stays published
and gains no evidence field, so one bounded knowledge composition does not
become an implicit evidence graph. All three positions are closed to untyped
Python input and `from_attributes` bypasses none of them: a strict constraint
is not applicable to a union schema, a strict union still admits a mapping
whose children are typed, and a strict model field admits one too, so each
position carries its own guard. JSON reconstructs the declared values normally
and every one of the eleven admitted types round-trips preserving its exact
type and value, which the focused tests assert over every ordered pair rather
than by sampling. One transport step is required and exactly one is performed:
because a guard standing above a value hands back an already materialized
object, and the composed collections are tuples a strict schema will not read
from parsed arrays, the composition is reconstructed in JSON input by the
published aggregate's own JSON grammar rather than rewritten here, so every
bound, uniqueness rule and reference-integrity rule the aggregate declares
still applies. The module performs no I/O.

`S1.P06.S09` demonstrates one bounded canonical vertical over the retained
pytest #4412 / #4414 case, in focused tests and here rather than in a new
persisted corpus, which stays `S1.P06.S11` work. The vertical keeps five layers
distinct and deliberately does not flatten them into one evidence-derived
fault: a retained normalized `S1.P05` observation binding a head revision of
pull request #4414; the existing `PullRequestHistoryFactEvidenceLink` from that
observation to the retained acquisition record; a caller-supplied
`SuppliedFaultReport` calibrated to the retained fault, carrying a synthetic
fault identity because the case supplies none; a caller-supplied
`FaultReportHistoryFactAssociation` joining that report to the published
observation; a bounded `FaultInstance` composing both; and one explicitly
constructed `FaultInstanceEvidenceLink` from an admitted subject to that same
retained record. FaultAtlas did not execute pytest, the retained stale-cache
hypothesis stays a supplied hypothesis rather than a fact, the Issue #4412 to
PR #4414 pairing stays a caller-supplied association rather than a provider
fact, and the last link is not inferred from the first two.

`S1.P06.S08` records that its own reference-integrity validation can become
expensive near its published bound. `S1.P06.S09` neither repairs nor reopens
that, changes no indexing, hashing, cache or bound, and states no complexity
guarantee of its own; it performs one bounded membership check per link and
leaves the cost a later optimization candidate. Deferred disposition and
readiness became `S1.P06.S10` work.

`S1.P06.S10` publishes no production module, symbol, or product semantics.
Production Python sources stay 20. It is a governance Slice: it disposes the
one subject `S1.P06` inherited, accounts for the obligations attached to it,
locks the accumulated `S1.P06` product surface, and decides whether
`S1.P06.S11` may begin. The durable record is the sealed decision under
`reference_corpus/contracts/fault-instance/decisions/`, whose Markdown
projection is derived from its JSON and never read by production code.

The effective inherited authority is not raw `S1.P05.S08` alone. It is
`S1.P05.S08` as corrected by `S1.P05.S08.C01` and consolidated by the published
`S1.P05` phase closure. Under that authority `S1.P06` receives exactly one
immediate inherited subject, `case relationship vocabulary provisional`,
carried forward under the wording `universal relationship vocabulary`, together
with two requirements and three prohibitions. The superseded owner topology,
which named six received subjects and a broader requirement, is quoted as
history and is not resurrected as effective.

That subject is `addressed`, with no `S1.P06`-owned remainder, no immediate
owner and no long-term owner, so no state is attached to it and no
`S1.P06`-owned deferred subject remains open. The word "universal" in the
carried-forward wording is the predecessor's phrasing rather than a required
capability: `S1.P05.S08.C01` narrowed the effective obligation to the bounded
domain relationship vocabulary needed by `FaultInstance`, and `S1.P06` supplied
exactly that as eight explicit typed contracts rather than one generic schema.
A report-to-source-object and a report-to-history-fact association in
`S1.P06.S04`, a candidate-to-revision and a candidate-to-change-set association
in `S1.P06.S05`, a run-to-revision association and a reported before-and-after
comparison in `S1.P06.S06`, the bounded reference-integrity relations of
`S1.P06.S08`, and the record-to-durable-evidence association of `S1.P06.S09`
each name their two endpoints by published type. No universal relationship
ontology, no generic `Relationship`, `Edge`, `Graph` or `RelationKind` type, no
relationship registry, and no provider-independent relation vocabulary was
needed and none is published. Arbitrary relationships are not representable, no
repository evolution graph semantics exist, and generic repository and
evolution graph semantics remain owned by `S5` under their own authority.

Both effective requirements are satisfied. `S1.P06` owns the bounded domain
relationship vocabulary through the eight contracts above, and it consumes the
bounded `S1.P05` history facts without redefining them: `S1.P06.S04` admits
exactly the six published history facts by type, `S1.P06.S05` consumes
`PullRequestChangeSet` under repair-candidate semantics without moving it into
the `S1.P05` evidence-fact union, `S1.P06.S08` composes the `S1.P06` records by
value, and `S1.P06.S09` keeps the `S1.P05` history and evidence authority
separate. The published `S1.P05` production bytes are unchanged.

All three effective prohibitions are preserved. No `S1.P06` module publishes
ancestry, reachability, merge-base, branch-containment or any generic Git graph
semantics. The bounded `S1.P05` surface is never read as a complete provider or
repository development history. The LEVEL-1 evidence association is not
implicitly upgraded: the `S1.P06.S04` associations stay weak caller-supplied
claims, and `S1.P06.S09` publishes no support, proof, verification, confidence
or field-level evidence locator and performs no association chaining.

For `S1.P06.S11`, the accumulated surface is locked at seven production modules
and thirty exported symbols, derived from live `__all__` values rather than
restated by hand: eight symbols in `faultatlas.domain.fault`, two in
`faultatlas.domain.fault_source_relationship`, four in
`faultatlas.domain.fault_repair`, eight in `faultatlas.domain.fault_test`, six
in `faultatlas.domain.fault_interpretation`, one in
`faultatlas.domain.fault_instance`, and one in
`faultatlas.domain.fault_evidence_link`. No alias and no package-level export
aggregator is published. On that surface, and with the inherited subject
dispositioned exactly once, `S1.P06.S11` contract-corpus readiness is
`eligible_to_begin` and `S1.P06.S11` has not begun.

One publication fact is recorded separately rather than folded into that
readiness, and it is taken from the provider's own ruleset evaluation rather
than from the merging session's account of itself. The `S1.P06.S09` pull
request was merged under an active ruleset that evaluated pass on every rule.
The merge command carried an administrator flag, but the ruleset configures no
bypass actor, no bypass was recorded, and the flag therefore changed nothing.
The only condition that ever refused the merge was one unresolved review
thread, which was resolved before the successful retry, and the pull request's
single commit was attributed, so the extra-approval condition for unattributed
changes was never triggered. `S1.P06.S09` is therefore an ordinary compliant
publication and no publication-governance exception stands against it.

That correction is itself worth recording. An earlier `S1.P06.S10` draft, and
the `S1.P06.S09` session report it drew on, described the same merge as an
administrator override that bypassed the ruleset. The description was wrong in
the direction of non-compliance. Sealing a violation that did not happen would
falsify the governance record exactly as laundering a real one would, so the
claim is corrected here rather than preserved, and the oracle now refuses both
directions.

The verdict publishes its own limits. It rests on provider records read at
publication time and cited by their stable identifiers, and those responses are
not retained in this repository, so a replay can confirm only that the artifact
records them and never that the provider reported them. Model-generated
analysis is not verified fact, and this verdict is analysis of an external
record rather than a retained observation. Retaining bounded immutable
snapshots of those responses is acquisition work outside this Slice, so
`S1.P06.S12` must re-verify the verdict rather than consume it as settled.
Whether the Phase may close remains `S1.P06.S12`'s decision and is not decided
here.

The `S1.P06.S08` membership-performance candidate is not part of canonical
`S1.P06` product state. It remains an unpublished nonblocking implementation
optimization candidate, it changes no `S1.P06.S08` semantics, and `S1.P06.S11`
readiness does not depend on it. The canonical surface is what stands on
`main`.

The `S1.P06` route is provisional beyond `S1.P06.S10`. Later exact schemas are
not authorized by appearing here, and every product Slice owns its focused
tests before the corpus Slice:

1. `S1.P06.S01` — Fault Instance Identity and Repository Context (complete)
2. `S1.P06.S02` — Supplied Fault Report and Behavioral Deviation (complete)
3. `S1.P06.S03` — Scenario and Occurrence Context (complete)
4. `S1.P06.S04` — Bounded Source and History Relationships (complete)
5. `S1.P06.S05` — Repair Candidates and Concrete Repair Associations
   (complete)
6. `S1.P06.S06` — Test Material, Reported Runs, Outcomes, and Comparability
   (complete)
7. `S1.P06.S07` — Case-Local Explanation, Hypothesis, and Expected Property
   (complete)
- `S1.P06.S07.C01` — Roadmap Lifecycle Narrative Consistency Correction
  (complete)
8. `S1.P06.S08` — Bounded `FaultInstance` Composition and Reference Integrity
   (complete)
9. `S1.P06.S09` — Fault-evidence bridge and canonical vertical (complete)
10. `S1.P06.S10` — Deferred disposition and readiness (complete)
11. `S1.P06.S11` — Accumulated contract corpus (next, not started)
12. `S1.P06.S12` — Integration and Phase closure (not started)

`S1.P06` consumes the bounded `S1.P05` history facts without redefining them
and does not read them as a complete development history. It does not own a
generic Git ancestry or reachability graph, which remains `S5` ownership, and
it does not implicitly upgrade the record-level `S1.P05.S07` evidence
association. The historical default branch remains unknown and owned by `S2`.
The published `S1.P05` contracts and the development-history v1 corpus stay
frozen. `S1.P06` receives exactly one immediate deferred subject, the universal
relationship vocabulary, and absorbs no subject owned by `S2` or `S5`. That
subject is not resolved by `S1.P06.S01`, `S1.P06.S02`, or `S1.P06.S03`.
`S1.P06.S04` implements the bounded relationship responsibility that handoff
assigns to `S1.P06`, publishing two named associations and no relationship
vocabulary, and without resolving the inherited subject formally, which
became `S1.P06.S10` work.

## Preserved later Stage 1 phases

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
unchanged by `S1.P05.S07` and neither imports the bridge.
The current live surface also adds the module `faultatlas.domain.fault`,
published by `S1.P06.S01`, whose `FaultInstanceIdentity` names one
caller-designated, possibly only suspected fault subject as a
`RootModel[uuid.UUID]`, and whose `FaultRepositoryContext` places one such
identity in one published `S1.P01` `RepositoryIdentity`. The identity
establishes no real-world fault existence and no same-defect equivalence,
allocates nothing, derives nothing from content, and converts no Issue, pull
request, run, or evidence identity. The context asserts no affected, causal,
owning, repair, or applicability repository, no commit membership, no verified
fault, no root cause, no reproduction, no repair correctness, and no evidence
support, and an identity/context pair is not yet a complete `FaultInstance`.
Both models are frozen and strict, both revalidate always, the context forbids
extra keys and guards each immediate child against untyped Python input, and
neither performs I/O.
`S1.P06.S02` extends that module in place with `FaultReportIdentity`, a
second independent `RootModel[uuid.UUID]` naming one caller-designated
supplied-report record and nominally distinct from the fault identity, and
`SuppliedFaultReport`, which binds one report identity to one published
`FaultRepositoryContext` consumed whole and to required caller-supplied
`problem_statement` and `behavioral_deviation` text of one to 4096 characters
that is neither trimmed nor normalized. The fault subject of a report is
`report.context.fault`. A report and its deviation are supplied claims, not
verification: they establish no affected repository, existing fault, executed
or observed deviation, originating Issue or pull request, known cause, repair,
run outcome, expected property, confidence, source relationship, or evidence
support, and `S1.P06.S02` published no such model. That took the module's
`__all__` from two symbols to four.
`S1.P06.S03` extends the same module again with `FaultScenarioIdentity` and
`FaultOccurrenceIdentity`, two further independent `RootModel[uuid.UUID]`
values nominally distinct from each other and from the fault and report
identities, and with `SuppliedFaultScenario`, which ties one scenario identity
to one published `SuppliedFaultReport` consumed whole and to a required
case-local `scenario_statement`, and `SuppliedFaultOccurrenceContext`, which
ties one occurrence identity to one published `SuppliedFaultScenario` consumed
whole and to a required `occurrence_context`. The fault subject of a scenario
is `scenario.report.context.fault`. A scenario states the supplied conditions
under which a report is relevant and never that the fault occurred; an
occurrence context is a supplied claim of one particular manifestation under
that scenario and is not an execution run, an independent observation, or a
reproduction. A report may stand alone, one report may carry several
scenarios, and a scenario may carry no occurrence or several, so no boolean
records whether the fault occurred and a missing occurrence record asserts
nothing. No occurrence time is recorded and the `S1.P05`
`PullRequestHistoricalOccurrenceTime` is not reused as one. `S1.P06.S03`
published no structured applicability taxonomy, run, outcome, source
relationship, evidence link, cause, repair, confidence, review, reusable
pattern, or complete `FaultInstance`; the bounded source and history
relationships came next, in `S1.P06.S04`. The `faultatlas.domain.fault`
module's current `__all__` is eight symbols and that module still performs no
I/O.
`S1.P06.S04` adds the module `faultatlas.domain.fault_source_relationship`,
whose `__all__` is exactly `FaultReportSourceObjectAssociation` and
`FaultReportHistoryFactAssociation`. Each carries exactly two fields, anchors on
a published `SuppliedFaultReport` consumed whole, and records one deliberately
weak caller-supplied association. The source-object association admits exactly
`NumberedSourceObjectIdentity` and `ProviderScopedSourceObjectIdentity`, reused
whole across all seven published object kinds, and admits no bare
`RepositoryIdentity` because repository placement already lives in
`report.context.repository`, which the associated object's repository need not
equal. The history-fact association admits exactly the six published facts the
`S1.P05.S07` evidence link admits, reused whole, and excludes
`ChangedPathStatus` as vocabulary rather than fact, `PullRequestChangeSet` as
outside that fact boundary, and `PullRequestHistoryFactEvidenceLink` as the
`S1.P05` evidence association itself. Association is not evidence support,
proof, causation, or repair correctness: approval is not confidence, a merge is
not a verified fix, a changed path is not an affected path, and a source
occurrence instant is not a fault-occurrence instant. Associating one report
with an Issue and with a pull request creates no Issue-to-pull-request
relation, and no relationship enum, triple, graph, inverse, transitive,
identifier, registry, ancestry, or completeness semantics is published. One
report may hold several associations and one source object may be associated
with reports naming different fault subjects without merging them, a missing
association encodes no known absence, and equality is ordinary model equality.
Both models are frozen, strict, extra-forbidding, always-revalidating, close
every model-valued position including both unions to untyped Python input,
round-trip through JSON while refusing their own `model_dump` as Python input,
and perform no I/O. `faultatlas.domain.fault`, `faultatlas.domain.identity`,
`faultatlas.domain.history`, and `faultatlas.domain.history_evidence_link` are
unchanged and none imports the new module.
`S1.P06.S05` adds the module `faultatlas.domain.fault_repair`, whose `__all__`
is exactly `FaultRepairCandidateIdentity`, `SuppliedFaultRepairCandidate`,
`FaultRepairCandidateRevisionAssociation`, and
`FaultRepairCandidateChangeSetAssociation`. The candidate identity is a fifth
independent `RootModel[uuid.UUID]`, nominally distinct from the fault, report,
scenario, and occurrence identities even on one shared scalar, and derived from
no pull-request number, commit digest, change-set content, report identity, or
fault identity. `SuppliedFaultRepairCandidate` ties one candidate identity to
one published `SuppliedFaultReport` consumed whole and to a supplied
`repair_statement` of one to 4096 characters under the `S1.P06.S02` text rule,
so the fault subject stays reachable at `candidate.report.context.fault`. A
candidate is a proposal, not an outcome: it establishes no known root cause, no
implementation, no merge, no passing test, no fixed fault, and no evidence
support, it requires neither a scenario nor an occurrence nor a cause, and it is
complete with no revision and no change set at all, because a not-yet-implemented
repair is exactly the case the layer must express. The revision association
reuses `GitCommitIdentity` whole and claims no repository membership,
reachability, head or merge role, application, or fix. The change-set
association deliberately consumes the `S1.P05` `PullRequestChangeSet` while
leaving its published meaning and the `S1.P05.S07` evidence boundary untouched,
so it is still excluded from `PullRequestHistoryFactEvidenceLink` and from
`FaultReportHistoryFactAssociation`, and the association asserts no complete
diff, affected path, merge, evidence, or provider completeness. Candidate,
revision, change set and pull request are four different things and none is an
identity of another; several candidates may share a report, several revisions
and change sets may share a candidate, and one revision or change set may serve
candidates of different reports without merging them. No coherence calculus
relates the associations, so an associated revision need not equal a change
set's head revision, and no status, confidence, review, evidence, or source
field exists. Both associations are frozen, strict, extra-forbidding and
always-revalidating, close every model-valued position to untyped Python input,
round-trip through JSON while refusing their own `model_dump` as Python input,
and perform no I/O.
`S1.P06.S06` adds the module `faultatlas.domain.fault_test`, whose `__all__` is
exactly `FaultTestMaterialIdentity`, `SuppliedFaultTestMaterial`,
`FaultTestRunIdentity`, `ReportedFaultTestRun`, `ReportedFaultTestOutcomeKind`,
`ReportedFaultTestOutcome`, `FaultTestRunRevisionAssociation`, and
`ReportedFaultTestComparison`. It keeps test material, a reported run, a
reported outcome, and a before-and-after comparison as four separate things:
material may exist with no run, and a run with no outcome. Everything it
publishes is caller-reported knowledge, since FaultAtlas executes no analyzed
repository here and observes no verdict, so none of these values may later be
read as a FaultAtlas-executed result. The two new `RootModel[uuid.UUID]`
identities bring the `S1.P06` UUID-rooted identities to seven, all nominally
distinct on one shared scalar, and a run identity is not the `S1.P03`
`AcquisitionRunId`, which is neither imported nor reinterpreted.
`SuppliedFaultTestMaterial` ties one material identity to one published
`SuppliedFaultReport` consumed whole and to a `test_statement`, claiming no
repository presence, retained bytes, execution, sufficiency, reproduction,
evidence, or regression completeness. `ReportedFaultTestRun` adds a
`run_statement` of opaque prose that is not parsed into environment or command
fields and carries no outcome and no time. `ReportedFaultTestOutcomeKind` is the
bounded vocabulary `passed`, `failed`, `errored`, `timed_out`, `skipped`,
`did_not_start`, and `cancelled`, with no `unknown`, `flaky`, `regression_safe`,
`fixed`, or `verified` member; an unsupplied outcome is the absence of a record
rather than any positive state, and flakiness is an interpretation over several
runs rather than one run's disposition. `ReportedFaultTestOutcome` reports one
disposition for one run and carries no evidence, confidence, review, or
correctness field, and two records may name one run and disagree without this
layer resolving them. `FaultTestRunRevisionAssociation` is optional and reuses
`GitCommitIdentity` intrinsically, inferring no repository membership, role,
candidate, or correctness. `ReportedFaultTestComparison` requires distinct run
subjects and the same full supplied test material, and infers no timestamp,
chronology, candidate, environment equality, independence, causation, or
regression safety: a `failed` to `passed` pair is a reported fail-to-pass
pattern and not a verified fix, a missing before outcome is not a before failure,
and `did_not_start`, `errored`, and `timed_out` remain distinct from `failed`.
All five records are frozen, strict, extra-forbidding and always-revalidating,
close every model-valued position and the outcome position to untyped Python
input, round-trip through JSON while refusing their own `model_dump` as Python
input, and perform no I/O.
`S1.P06.S07` adds the module `faultatlas.domain.fault_interpretation`, whose
`__all__` is exactly `FaultExplanationIdentity`, `SuppliedFaultExplanation`,
`FaultHypothesisIdentity`, `SuppliedFaultHypothesis`,
`FaultExpectedPropertyIdentity`, and `SuppliedFaultExpectedProperty`. It keeps
explanation, hypothesis, and expected property as three separate case-local
knowledge categories, each anchored on one `SuppliedFaultReport` consumed whole,
and a report may carry none, one, or several of each independently. The three
new `RootModel[uuid.UUID]` identities bring the `S1.P06` UUID-rooted identities
to ten, all nominally distinct on one shared scalar. `SuppliedFaultExplanation`
carries an `explanation_statement` that may be root-cause shaped without
establishing a root cause or recording acceptance, review, support, or
verification. `SuppliedFaultHypothesis` carries a `hypothesis_statement` that
stays explicitly tentative and cannot record its own confirmation, rejection,
probability, or supporting evidence. `SuppliedFaultExpectedProperty` carries an
`expected_property_statement` scoped to one report, which is not a passing test,
a verified invariant, a universal law, a cross-instance pattern, or a repair
acceptance criterion; generalization is `S1.P07` work. No promotion, lifecycle,
precedence, or conflict resolution relates the three, identical prose in two
kinds stays two records, and nothing is inferred from repair candidates, test
material, runs, outcomes, or comparisons, to which the module publishes no
relation at all. All three records are frozen, strict, extra-forbidding and
always-revalidating, close both model-valued positions to untyped Python input,
declare no alias and no nullable field, round-trip through JSON while refusing
their own `model_dump` as Python input, and perform no I/O.
`S1.P06.S08` adds the module `faultatlas.domain.fault_instance`, whose `__all__`
is exactly `FaultInstance`: one frozen strict aggregate of seventeen fields
composing the records `S1.P06.S01` through `S1.P06.S07` publish. It carries one
`FaultInstanceIdentity` and one or more `SuppliedFaultReport` values whose
`report.context.fault` equals it, so one logical fault may be described by
several reports in several repository contexts, and fifteen further collections
default to empty tuples. An absent collection means absent from this
composition, never known nonexistence, and `None` is refused. Reference
integrity is by whole record: a scenario's report, an association's report, a
candidate's report, a material's report and an interpretation's report must be
exact members of `reports`; an occurrence's scenario, a repair association's
candidate, a run's material, an outcome's run and a comparison's before and
after must be exact members of their own collections. Dangling references are
refused rather than auto-inserted, and each primary subject identity occurs at
most once inside one composition, per nominal identity type. Conflicting
outcomes for one run and conflicting explanations or hypotheses for one report
coexist without resolution, no semantic edge is inferred across layers, order is
preserved without meaning, no evidence, support or confidence is carried, the
composed subject and every collection are closed to untyped Python input, and
the module performs no I/O.
`S1.P06.S09` adds the module `faultatlas.domain.fault_evidence_link`, whose
`__all__` is exactly `FaultInstanceEvidenceLink`: one frozen strict record of
exactly three fields, `fault_instance`, `subject`, and `evidence_record`. It
bridges one substantive record already composed inside one `FaultInstance` to
one `DurableEvidenceRecordReference`, carrying the same weak association the
published history-fact and snapshot-fact evidence links carry and no more: no
support, proof, verification, corroboration, observation, derivation,
confidence, review or status. The subject position admits exactly the eleven
substantive `S1.P06` records and excludes the aggregate itself, every identity,
the five association records, both published evidence links, and every
repository, snapshot and history aggregate value. The subject must already be
an exact whole-record member of the collection that carries its type, a
same-identity record differing anywhere else is refused, and nothing is
auto-inserted. The record is referenced as one whole durable record with no
locator, pointer, span or field path, several links are several values with no
registry or ordering over them, and absence of a link asserts nothing. No
association chaining exists: a report to history fact and history fact to
record chain does not produce a report to record link, which must be
constructed explicitly. `FaultInstance` is unchanged and gains no evidence
field, all three positions are closed to untyped Python input, every admitted
type round-trips through JSON preserving its exact type and value, and the
module performs no I/O.
`S1.P06.S10` adds no production module and no symbol. It publishes one sealed
decision under `reference_corpus/contracts/fault-instance/decisions/`, whose
`decision.md` is a derived projection of its `decision.json` and which no
production code reads or writes. It records that `S1.P06` inherited exactly one
immediate subject under the effective `S1.P05.S08` plus `S1.P05.S08.C01` plus
`S1.P05` phase-closure authority, that the subject is `addressed` with
`self_owned_open == 0`, that both effective requirements are satisfied and all
three effective prohibitions preserved, that `S1.P06` owns seven production
modules and thirty exported symbols for `S1.P06.S11` to cover, that
`S1.P06.S11` contract-corpus readiness is `eligible_to_begin`, and that the
`S1.P06.S09` publication was compliant: its push evaluated pass on every active
rule, no bypass was configured or recorded, and the administrator flag the
merge command carried could not take effect, so no publication-governance
exception stands against it.
Production Python sources are 20.
`S1.P05` is complete: `S1.P05.S01`, `S1.P05.S02` including the
`S1.P05.S02.C01` correction, `S1.P05.S03`, `S1.P05.S04`, `S1.P05.S05`,
`S1.P05.S06`, `S1.P05.S07`, `S1.P05.S08` including the `S1.P05.S08.C01`
correction, `S1.P05.S09`, and `S1.P05.S10` are complete.
`S1.P06` is active and incomplete; `S1.P06.S01` is complete,
`S1.P06.S02` is complete, `S1.P06.S03` is complete,
`S1.P06.S04` is complete, `S1.P06.S05` is complete,
`S1.P06.S06` is complete, `S1.P06.S07` is complete including the
`S1.P06.S07.C01` correction, `S1.P06.S08` is complete,
`S1.P06.S09` is complete,
`S1.P06.S10` is complete, and `S1.P06.S11` is next and not started.
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
