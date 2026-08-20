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
  active and incomplete; `S1.P04.S01` is complete, `S1.P04.S02` is complete,
  and `S1.P04.S03` is complete. `S1.P04.S04` is next and not started.
  `S1.P05` through `S1.P10` remain not started.
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
are complete. `S1.P04` is active and incomplete; `S1.P04.S01` is complete,
`S1.P04.S02` is complete, and `S1.P04.S03` is complete. `S1.P04.S04` is next
and not started. `S1.P05` through `S1.P10` remain not started, and `S2-S9`
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

`S1.P04` is active and incomplete. `S1.P04.S01` is complete, `S1.P04.S02` is
complete, `S1.P04.S03` is complete, and `S1.P04.S04` is next and not started.
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

Repository membership collections; entry kind, mode, symlink, and gitlink
semantics; ordering; duplicate-path and prefix collision rules; completeness;
absence; evidence linkage; Git or filesystem I/O; and persistence or durable
serialization remain deferred. `S1.P05` through `S1.P10` remain not started;
S01, S02, and S03 do not make S1.P05 eligible to begin.

The remaining `S1.P04` sequence below is PROVISIONAL planning only. It is not
a commitment, and the slice count is fixed retrospectively at Phase closure:

1. `S1.P04.S04` — bounded path-binding collection
2. `S1.P04.S05` — snapshot scope and completeness
3. `S1.P04.S06` — entry kind and Git mode semantics, evidence-gated
4. `S1.P04.S07` — evidence-linked offline snapshot vertical
5. `S1.P04.S08` — repository snapshot contract corpus
6. `S1.P04.S09` — integration and Phase closure

S06 is gated on evidence that does not yet exist in this repository. The
retained canonical path-resolution evidence records no Git file mode for any
leaf or traversal, so S06 is not guaranteed to implement mode.

## Preserved later Stage 1 phases

- **S1.P05 — Development History Model**
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
`RepositorySnapshotRootTreeBinding` and `RepositorySnapshotPathBinding` values
in `faultatlas.domain.snapshot`; `S1.P04` is active and incomplete,
`S1.P04.S01`, `S1.P04.S02`, and `S1.P04.S03` are complete, and `S1.P04.S04` is
next and not started. The path binding performs no Git or filesystem I/O and
claims no repository membership, completeness, or evidence linkage.

The minimal CLI and governed Python foundation belong to the S0 operational
baseline. Environment-only commits remain a development-maintenance track and
are not product Phases.

## Rolling planning

Slices in the current Phase may be detailed as evidence and decisions become
available. Later-Phase implementation details remain provisional until their
own gates. In particular, no advanced RAG approach is locked before retrieval
benchmarks justify it.
