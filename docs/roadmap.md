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
- **S1** is active through the preparatory `S1.P00` Phase.
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
`S1.P00.S04` is active with a local immutable-evidence capture implementation
pending Gate 3 publication and push CI. `S1.P00.S05` has not begun.

Non-goals include source ingestion, persistence, retrieval implementation,
repository graphs, RAG, model routing, artifact synthesis, services, UI, and
declaring provisional models to be public or complete contracts.

The current `S1.P00` Slice sequence is:

1. `S1.P00.S01` — Roadmap and Terminology Reconciliation (complete)
2. `S1.P00.S02` — Reference-Case Selection and Capture Policy (complete)
3. `S1.P00.S03` — Acquisition Procedure and Capture Manifest Plan (complete)
4. `S1.P00.S04` — Immutable Reference Evidence Capture (active; local
   implementation pending Gate 3 publication and push CI)
5. `S1.P00.S05` — Case Manifest and Relationship Lock (not begun)
6. `S1.P00.S06` — Current-Contract Gap Matrix
7. `S1.P00.S07` — Identity, Revision, and Provenance Decision
8. `S1.P00.S08` — Snapshot Boundary and Compatibility Decision
9. `S1.P00.S09` — Deterministic Corpus Tests
10. `S1.P00.S10` — Integration and Phase Closure

## Preserved Stage 1 phases

- **S1.P01 — Identity Primitives**
- **S1.P02 — Revision-qualified Locators**
- **S1.P03 — Evidence Envelope**
- **S1.P04 — Repository Snapshot Model**
- **S1.P05 — Development History Model**
- **S1.P06 — Fault Instance Model**
- **S1.P07 — Pattern & Invariant Model**
- **S1.P08 — Transfer & Applicability Model**
- **S1.P09 — Provenance, Confidence & Review**
- **S1.P10 — Persistence, Serialization & Contract Corpus**

## Current-code mapping

The existing internal `SourceLocator` and `ArtifactSnapshot` models are
provisional, pre-roadmap S1 seeds. They are not declared completed
implementations of `S1.P01`, `S1.P02`, or `S1.P03`.

The minimal CLI and governed Python foundation belong to the S0 operational
baseline. Environment-only commits remain a development-maintenance track and
are not product Phases.

## Rolling planning

Slices in the current Phase may be detailed as evidence and decisions become
available. Later-Phase implementation details remain provisional until their
own gates. In particular, no advanced RAG approach is locked before retrieval
benchmarks justify it.
