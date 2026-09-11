# FaultInstance Contract Corpus

## 1. Scope and Authority Warning

This internal, source-only `S1.P06.S11` contract corpus is not a production schema, class, adapter, reader, writer, migration, persistence contract, or public API. The four canonical JSON files are the semantic authority; this Markdown is a derived projection over them: every name, digest and number it reports is one the canonical JSON carries, so a claim can only be dropped from this file, never added to it. The corpus is executed only by `tests/test_fault_instance_contract_corpus.py` and is excluded from the wheel and the sdist.

Corpus `faultatlas-fault-instance-contract-corpus` version `1`. Phase closure is owned by `S1.P06.S12` and serialization and migration by `S1.P10`.

## 2. Files and Digests

| File | Role | SHA-256 | Bytes |
| --- | --- | --- | --- |
| `contract.md` | `derived_prose` | n/a | n/a |
| `invalid-vectors.json` | `canonical_vector_file` | `9bfabd902052102b742a62878a597543a2e38da6015c5330bab16c07af40e7c0` | 172147 |
| `invalid-vectors.sha256` | `digest_sidecar` | n/a | n/a |
| `manifest.json` | `canonical_manifest` | n/a | n/a |
| `manifest.sha256` | `digest_sidecar` | n/a | n/a |
| `replay-vectors.json` | `canonical_vector_file` | `14eb01c8f6d7fd51ef4bbef01a09ed0e5f5658c4144c730e74a5511a0b4ca5a2` | 129528 |
| `replay-vectors.sha256` | `digest_sidecar` | n/a | n/a |
| `valid-vectors.json` | `canonical_vector_file` | `2407d48598ce4cb7bc53da1383686c02754a349844bf0958a352e8dcc4525915` | 287863 |
| `valid-vectors.sha256` | `digest_sidecar` | n/a | n/a |

Nine files exactly. `manifest.json` carries no digest of itself; its `manifest.sha256` sidecar does. `contract.md` has no sidecar because it is not semantic authority.

## 3. Covered Product Surface

7 owned `S1.P06` production modules and 30 owned product symbols, derived again from live `__all__` values and required to equal what the sealed `S1.P06.S10` decision recorded:

| Symbol | Module | Slice | Target class |
| --- | --- | --- | --- |
| `FaultInstanceIdentity` | `faultatlas.domain.fault` | `S1.P06.S01` | `identity_target` |
| `FaultRepositoryContext` | `faultatlas.domain.fault` | `S1.P06.S01` | `record_target` |
| `FaultReportIdentity` | `faultatlas.domain.fault` | `S1.P06.S02` | `identity_target` |
| `SuppliedFaultReport` | `faultatlas.domain.fault` | `S1.P06.S02` | `record_target` |
| `FaultScenarioIdentity` | `faultatlas.domain.fault` | `S1.P06.S03` | `identity_target` |
| `FaultOccurrenceIdentity` | `faultatlas.domain.fault` | `S1.P06.S03` | `identity_target` |
| `SuppliedFaultScenario` | `faultatlas.domain.fault` | `S1.P06.S03` | `record_target` |
| `SuppliedFaultOccurrenceContext` | `faultatlas.domain.fault` | `S1.P06.S03` | `record_target` |
| `FaultReportSourceObjectAssociation` | `faultatlas.domain.fault_source_relationship` | `S1.P06.S04` | `record_target` |
| `FaultReportHistoryFactAssociation` | `faultatlas.domain.fault_source_relationship` | `S1.P06.S04` | `record_target` |
| `FaultRepairCandidateIdentity` | `faultatlas.domain.fault_repair` | `S1.P06.S05` | `identity_target` |
| `SuppliedFaultRepairCandidate` | `faultatlas.domain.fault_repair` | `S1.P06.S05` | `record_target` |
| `FaultRepairCandidateRevisionAssociation` | `faultatlas.domain.fault_repair` | `S1.P06.S05` | `record_target` |
| `FaultRepairCandidateChangeSetAssociation` | `faultatlas.domain.fault_repair` | `S1.P06.S05` | `record_target` |
| `FaultTestMaterialIdentity` | `faultatlas.domain.fault_test` | `S1.P06.S06` | `identity_target` |
| `SuppliedFaultTestMaterial` | `faultatlas.domain.fault_test` | `S1.P06.S06` | `record_target` |
| `FaultTestRunIdentity` | `faultatlas.domain.fault_test` | `S1.P06.S06` | `identity_target` |
| `ReportedFaultTestRun` | `faultatlas.domain.fault_test` | `S1.P06.S06` | `record_target` |
| `ReportedFaultTestOutcomeKind` | `faultatlas.domain.fault_test` | `S1.P06.S06` | `vocabulary_target` |
| `ReportedFaultTestOutcome` | `faultatlas.domain.fault_test` | `S1.P06.S06` | `record_target` |
| `FaultTestRunRevisionAssociation` | `faultatlas.domain.fault_test` | `S1.P06.S06` | `record_target` |
| `ReportedFaultTestComparison` | `faultatlas.domain.fault_test` | `S1.P06.S06` | `record_target` |
| `FaultExplanationIdentity` | `faultatlas.domain.fault_interpretation` | `S1.P06.S07` | `identity_target` |
| `SuppliedFaultExplanation` | `faultatlas.domain.fault_interpretation` | `S1.P06.S07` | `record_target` |
| `FaultHypothesisIdentity` | `faultatlas.domain.fault_interpretation` | `S1.P06.S07` | `identity_target` |
| `SuppliedFaultHypothesis` | `faultatlas.domain.fault_interpretation` | `S1.P06.S07` | `record_target` |
| `FaultExpectedPropertyIdentity` | `faultatlas.domain.fault_interpretation` | `S1.P06.S07` | `identity_target` |
| `SuppliedFaultExpectedProperty` | `faultatlas.domain.fault_interpretation` | `S1.P06.S07` | `record_target` |
| `FaultInstance` | `faultatlas.domain.fault_instance` | `S1.P06.S08` | `record_target` |
| `FaultInstanceEvidenceLink` | `faultatlas.domain.fault_evidence_link` | `S1.P06.S09` | `record_target` |

16 supporting targets from 6 earlier-phase modules are consumed and not owned: `faultatlas.domain.evidence`, `faultatlas.domain.history`, `faultatlas.domain.history_evidence_link`, `faultatlas.domain.identity`, `faultatlas.domain.revision`, `faultatlas.domain.snapshot_evidence_link`. None counts toward owned coverage and none gains new semantics.

## 4. Vector Inventory

| Family | valid | invalid | replay |
| --- | --- | --- | --- |
| `composition` | 10 | 16 | 1 |
| `evidence-link` | 14 | 26 | 1 |
| `expected-property` | 2 | 4 | 1 |
| `explanation` | 3 | 4 | 1 |
| `history-fact-association` | 8 | 6 | 1 |
| `hypothesis` | 3 | 4 | 1 |
| `identity` | 17 | 0 | 11 |
| `occurrence` | 2 | 3 | 1 |
| `repair-candidate` | 2 | 2 | 1 |
| `repair-change-set-association` | 1 | 2 | 1 |
| `repair-revision-association` | 3 | 2 | 1 |
| `report` | 6 | 12 | 1 |
| `repository-context` | 3 | 6 | 1 |
| `retained-observation` | 0 | 0 | 9 |
| `scenario` | 2 | 3 | 1 |
| `source-object-association` | 4 | 4 | 1 |
| `test-comparison` | 3 | 5 | 1 |
| `test-material` | 2 | 1 | 1 |
| `test-outcome` | 5 | 3 | 2 |
| `test-outcome-kind` | 8 | 5 | 0 |
| `test-run` | 3 | 1 | 2 |
| `test-run-revision-association` | 2 | 1 | 1 |
| **total** | **103** | **110** | **41** |

254 vectors over 29 declared fixtures. Every vector occupies a distinct semantic partition and every one of the thirty owned symbols is executably covered.

## 5. Execution and Rejection

Three input modes: `json`, `python`, `replay`. Two operations: `construct`, `reject`. Four test-only input markers: `enum_value`, `indexed_value`, `tuple_value`, `typed_value`. An unknown target, operation, or marker fails closed. No marker reaches production validation.

Accepted vectors declare an explicitly authored semantic dump, except the one declared cardinality probe, which declares its member count instead of a four-thousand-member dump; a production dump is never used as its own oracle in either shape. Rejected vectors declare a failure category, an error type and an error location. Prefix locations are used only at the three discriminatorless union positions `FaultReportHistoryFactAssociation.history_fact`, `FaultReportSourceObjectAssociation.source_object`, `FaultInstanceEvidenceLink.subject`, where branch-internal labels are not a stable contract. No Pydantic message prose is locked.

## 6. Replay and Provenance

The canonical vertical does not flatten its layers into an evidence-derived fault instance. Five classifications are used:

- `caller_supplied_association` — the S04, S05, S06 and S09 supplied associations
- `caller_supplied_composition` — the S08 composition and the supplied change set
- `caller_supplied_identity` — the eleven synthetic S1.P06 identity replays
- `caller_supplied_record` — the S01, S02, S03, S05, S06 and S07 supplied records
- `retained_normalized_observation` — the six retained S1.P05 history facts and the retained acquisition record

`S1.P06` has 0 historical UUID identities, so every `S1.P06` identifier replayed here is fixed, synthetic and caller-supplied. Replay targets 29 of the thirty owned symbols; `ReportedFaultTestOutcomeKind` participates in the vertical as the declared disposition inside the two reported outcomes rather than as a replay target of its own.

The retained case keeps every boundary it already had:

- the Issue #4412 and PR #4414 pairing is not promoted to a provider fact
- stale-cache causation remains a caller-supplied hypothesis
- no historical S1.P06 UUID identity exists, so every one here is synthetic
- FaultAtlas did not execute pytest
- a reported run or outcome is not an independent execution
- a reported failed-then-passed pair is not repair correctness
- an expected property is not an S1.P07 invariant
- the S1.P06.S09 evidence association is explicitly supplied, never inferred
- the whole evidence record is referenced with no field-level locator

17 manifest leaves are declared human-oriented prose and are never counted as verified assurance. Every other leaf is refused when falsified.

## 7. Package Boundary

Production Python modules stay at 20. `S1.P06.S11` adds no production file, symbol, or product semantic. The wheel and the sdist exclude `reference_corpus/`, `tests/` and `docs/`, so installing `faultatlas` never makes this corpus available and no production API can locate or read it.

The seven owned production modules are sealed inputs, locked by SHA-256 and byte length and verified against live bytes before the corpus runs.

## 8. Non-Goals

- no universal relationship ontology
- no generic relationship graph
- no generic Git ancestry or reachability graph
- no merge-base, ahead, behind, or branch-containment semantics
- no complete development-history claim
- no support, confidence, or review calculus
- no field-level evidence locator
- no automatic evidence transitivity
- no repair correctness
- no independent test execution
- no reusable Pattern or Invariant
- no transfer or applicability semantics
- no persistence or production serializer
- no production corpus reader
- no source ingestion
- no retrieval or RAG
- no repository execution
- no root cause and no violated invariant
- no timestamp-implied causality and no fault-occurrence time
- no allocator and no identity resolution, deduplication, or merging
- no same-defect or different-defect equivalence judgement
- no canonical ordering of a composed collection
- corpus validity does not prove factual truth of caller-supplied records
- replayability does not promote a supplied claim into retained observation

## 9. Handoff

`S1.P06.S12` is next: integration and `S1.P06` Phase closure. The entry authority for this Slice is the sealed `S1.P06.S10` decision at `reference_corpus/contracts/fault-instance/decisions/s10-deferred-subject-disposition-readiness/decision.json`, SHA-256 `57e9fdf8befdb4844459857f26dc5e69e91388f2d8a7a27994825882815d4fac`. It is authority for readiness and scope and is never vectorized as product behavior.
