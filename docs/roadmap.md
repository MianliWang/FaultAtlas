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
  `S1.P02.S06` is complete. `S1.P02.S07` is complete. `S1.P03` is next,
  eligible, and not started. `S1.P04` through `S1.P10` remain not started.
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
`S1.P02.S07` is complete. `S1.P03` is next, eligible, and not started.
`S1.P04` through `S1.P10` and `S2-S9` remain unimplemented.

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
reader, resolver, or persistence contract. Retrieval provenance, conflict
resolution, lifecycle transition history, evidence envelopes, and migration
remain unimplemented.

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
publishes the internal, case-calibrated Phase closure. `S1.P03` is next,
eligible, and not started. No production corpus reader, locator resolver,
Evidence Envelope, or persistence contract exists.

## Preserved later Stage 1 phases

- **S1.P03 — Evidence Envelope**
- **S1.P04 — Repository Snapshot Model**
- **S1.P05 — Development History Model**
- **S1.P06 — Fault Instance Model**
- **S1.P07 — Pattern & Invariant Model**
- **S1.P08 — Transfer & Applicability Model**
- **S1.P09 — Provenance, Confidence & Review**
- **S1.P10 — Persistence, Serialization & Contract Corpus**

## Current-code mapping

The existing internal `SourceLocator` and `ArtifactSnapshot` models remain
pre-roadmap S1 seeds. They are not revision-qualified Git locator (`S1.P02`)
or Evidence Envelope (`S1.P03`) implementations, and they are not public
contracts.

The minimal CLI and governed Python foundation belong to the S0 operational
baseline. Environment-only commits remain a development-maintenance track and
are not product Phases.

## Rolling planning

Slices in the current Phase may be detailed as evidence and decisions become
available. Later-Phase implementation details remain provisional until their
own gates. In particular, no advanced RAG approach is locked before retrieval
benchmarks justify it.
