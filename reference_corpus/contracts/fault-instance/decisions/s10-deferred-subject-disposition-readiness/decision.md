# FaultInstance Deferred-Subject Disposition and S1.P06.S11 Readiness

## 1. Scope and Authority Warning

This internal, case-calibrated `S1.P06.S10` decision is not a production schema, class, adapter, reader, writer, migration, persistence contract, or public API. `decision.json` is the sole durable semantic authority; this Markdown is derived. The Slice is governance-only: no production Python source changed, no production module was added, and the production source count remains 20.

## 2. Exact `decision.json` SHA-256

`d3588d9dc8baf012b3751d96ab3cc6f01820abd2e8819e96ea095284828f61d5`

## 3. Result

`S1.P06` inherited exactly 1 immediate deferred subject under its effective authority. It is dispositioned exactly once, as `addressed`. 2 of 2 effective requirements are satisfied and 3 of 3 effective prohibitions are preserved.

    self_owned_open == 0

No universal relationship ontology is published, no predecessor artifact is edited, and no subject is claimed resolved that is not. `S1.P06.S11` contract-corpus readiness is `eligible_to_begin`.

## 4. Effective Inherited Authority

The effective authority is the 3 artifacts below read together. `handoff:s1-p05-s08:s1-p06` is superseded by `handoff:s1-p05-s08-c01:s1-p06`.

| Slice | Role | Path |
| --- | --- | --- |
| `S1.P05.S08` | `published_predecessor_disposition` | `reference_corpus/contracts/development-history/decisions/s08-deferred-subject-disposition/decision.json` |
| `S1.P05.S08.C01` | `published_predecessor_correction` | `reference_corpus/contracts/development-history/corrections/s08-c01-deferred-subject-owner-topology/correction.json` |
| `S1.P05.S10` | `published_predecessor_phase_closure` | `reference_corpus/contracts/development-history/closures/s1-p05-phase-closure/closure.json` |

The raw S1.P05.S08 handoff to S1.P06 is superseded and must not be read alone. It named six received subjects and the requirement own_fault_instance_consuming_relationship_and_event_semantics. The effective authority is S1.P05.S08 as corrected by S1.P05.S08.C01 and consolidated by the published S1.P05 phase closure, under which S1.P06 receives exactly one immediate subject, two requirements, and three prohibitions. The superseded owner topology is not resurrected here.

Received subjects: 1. Requirements: 2. Prohibitions: 3.

## 5. The Inherited Subject and Its Disposition

| # | Subject | Subject ID | Disposition |
| --- | --- | --- | --- |
| 1 | case relationship vocabulary provisional | `gap:s05-known:case-relationship-vocabulary-provisional` | addressed by `S1.P06.S04`, `S1.P06.S05`, `S1.P06.S06`, `S1.P06.S08`, `S1.P06.S09` |

Source: `reference_corpus/contracts/development-history/closures/s1-p05-phase-closure/closure.json` at `/p06_handoff`, SHA-256 `9f5ff594a841ccca1c9ff05d286f3cf774a87ebdd4b7da4c07facf7a62afed23`. Predecessor wording: "case relationship vocabulary provisional". Carried-forward wording: "universal relationship vocabulary". Predecessor state: `unsupported_current_scope`. Effective authority: `S1.P05.S08.C01`.

Effective scope: `own_the_bounded_domain_relationship_vocabulary_needed_by_FaultInstance`. Outcome: `satisfied_under_effective_S1.P05.S08.C01_scope`.

The carried-forward wording is "universal relationship vocabulary", and "universal" there names the predecessor's phrasing rather than a required capability. S1.P05.S08.C01 narrowed the effective obligation to the bounded domain relationship vocabulary needed by FaultInstance, and the S1.P05 phase closure carries that narrowed obligation forward as the single immediate subject S1.P06 receives. S1.P06 has supplied that bounded vocabulary as eight explicit typed contracts rather than one generic relation schema: a report to source-object association and a report to bounded history-fact association in S1.P06.S04; a repair candidate to immutable revision association and a repair candidate to supplied change-set association in S1.P06.S05; a reported run to revision association and a reported before-and-after comparison in S1.P06.S06; the bounded reference-integrity relations of the composition in S1.P06.S08; and the substantive record to durable evidence-record association in S1.P06.S09. Each names its two endpoints by published type, so no Relationship, Edge, Graph, RelationKind, registry, or provider-independent relationship ontology was needed and none was published. The obligation is therefore fulfilled under its effective scope, with no P06-owned remainder and no later owner.

An addressed subject carries no remainder, so no state and no owner is attached: `addressed_count` is 1, `carried_forward_count` is 0, `split_count` is 0, and `self_owned_open` is 0.

## 6. Requirement Accounting

### 6.1 `own_the_bounded_domain_relationship_vocabulary_needed_by_FaultInstance`

Status: `satisfied`. Identifier: `requirement:s1-p05-s08-c01:s1-p06:01`.

| Slice | Module | Symbol | Endpoints |
| --- | --- | --- | --- |
| `S1.P06.S04` | `faultatlas.domain.fault_source_relationship` | `FaultReportSourceObjectAssociation` | supplied report to bounded source object |
| `S1.P06.S04` | `faultatlas.domain.fault_source_relationship` | `FaultReportHistoryFactAssociation` | supplied report to one bounded S1.P05 history fact |
| `S1.P06.S05` | `faultatlas.domain.fault_repair` | `FaultRepairCandidateRevisionAssociation` | supplied repair candidate to one immutable revision |
| `S1.P06.S05` | `faultatlas.domain.fault_repair` | `FaultRepairCandidateChangeSetAssociation` | supplied repair candidate to one supplied pull-request change set |
| `S1.P06.S06` | `faultatlas.domain.fault_test` | `FaultTestRunRevisionAssociation` | reported test run to one immutable revision |
| `S1.P06.S06` | `faultatlas.domain.fault_test` | `ReportedFaultTestComparison` | reported before outcome to reported after outcome |
| `S1.P06.S08` | `faultatlas.domain.fault_instance` | `FaultInstance` | bounded composition reference integrity across fifteen declared edges |
| `S1.P06.S09` | `faultatlas.domain.fault_evidence_link` | `FaultInstanceEvidenceLink` | substantive composed record to one durable evidence-record reference |

A generic relation schema was published: `false`.

### 6.2 `consume_the_bounded_S1_P05_history_facts_without_redefining_them`

Status: `satisfied`. Identifier: `requirement:s1-p05-s08-c01:s1-p06:02`.

- S1.P06.S04 admits exactly the six published S1.P05 history facts by type and redefines none of them
- S1.P06.S05 consumes PullRequestChangeSet under repair-candidate semantics and does not move it into the S1.P05 evidence-fact union
- S1.P06.S08 composes the S1.P06 records by value and adds no field to any of them
- S1.P06.S09 keeps the S1.P05 history and evidence authority separate and adds no transitive inference

Admitted `S1.P05` history facts: `PullRequestChangedPath`, `PullRequestHeadRefDeletion`, `PullRequestHistoricalOccurrenceTime`, `PullRequestMergeRevisionOutcome`, `PullRequestReviewRevisionApproval`, `PullRequestRevisionRoleBinding`.

Predecessor production bytes redefined: `false`. Predecessor modules unchanged by `S1.P06`: `faultatlas.domain.history`, `faultatlas.domain.history_evidence_link`.

## 7. Prohibition Accounting

### 7.1 `own_a_generic_git_ancestry_or_reachability_graph`

State: `preserved`. Identifier: `prohibition:s1-p05-s08-c01:s1-p06:01`.

- no S1.P06 module publishes an ancestry, reachability, merge-base, or branch-containment relation
- S1.P06.S05 associates a repair candidate with one immutable revision and with one supplied change set, and requires no relation between them
- S1.P06.S06 associates a reported run with one revision and compares two reported outcomes, and derives no ordering over revisions
- S1.P06.S08 refuses a dangling reference and requires no candidate revision to equal a change set head

### 7.2 `read_the_bounded_S1_P05_surface_as_a_complete_development_history`

State: `preserved`. Identifier: `prohibition:s1-p05-s08-c01:s1-p06:02`.

- S1.P06.S04 admits exactly six published S1.P05 history facts and treats them as bounded records
- no S1.P06 module claims the S1.P05 surface enumerates a provider or repository development history
- S1.P06.S08 states that an absent collection means absent from this composition and never known nonexistence

### 7.3 `upgrade_the_LEVEL_1_evidence_association_implicitly`

State: `preserved`. Identifier: `prohibition:s1-p05-s08-c01:s1-p06:03`.

- S1.P06.S04 associations remain weak caller-supplied claims and carry no support, strength, or confidence field
- S1.P06.S09 publishes the same LEVEL 1 association strength as the S1.P04 and S1.P05 evidence links
- S1.P06.S09 publishes no support, proof, verification, confidence, or field-level evidence locator
- S1.P06.S09 performs no association chaining: a report to history-fact association plus a history-fact to record association does not produce a report to record association

## 8. `S1.P06` Product Inventory for `S1.P06.S11`

The accumulated s1.p06 product surface s1.p06.s11 must cover.

| Module | Publishing Slices | Exported Symbols |
| --- | --- | --- |
| `faultatlas.domain.fault` | `S1.P06.S01`, `S1.P06.S02`, `S1.P06.S03` | 8 |
| `faultatlas.domain.fault_source_relationship` | `S1.P06.S04` | 2 |
| `faultatlas.domain.fault_repair` | `S1.P06.S05` | 4 |
| `faultatlas.domain.fault_test` | `S1.P06.S06` | 8 |
| `faultatlas.domain.fault_interpretation` | `S1.P06.S07` | 6 |
| `faultatlas.domain.fault_instance` | `S1.P06.S08` | 1 |
| `faultatlas.domain.fault_evidence_link` | `S1.P06.S09` | 1 |

Owned modules: 7. Owned symbols: 30. Duplicate symbols: 0. Alias symbols published: `false`. Package-level aggregator published: `false`. Inventory derived from `live_module_dunder_all`.

| Slice | Module | Symbol |
| --- | --- | --- |
| `S1.P06.S01` | `faultatlas.domain.fault` | `FaultInstanceIdentity` |
| `S1.P06.S01` | `faultatlas.domain.fault` | `FaultRepositoryContext` |
| `S1.P06.S02` | `faultatlas.domain.fault` | `FaultReportIdentity` |
| `S1.P06.S02` | `faultatlas.domain.fault` | `SuppliedFaultReport` |
| `S1.P06.S03` | `faultatlas.domain.fault` | `FaultScenarioIdentity` |
| `S1.P06.S03` | `faultatlas.domain.fault` | `FaultOccurrenceIdentity` |
| `S1.P06.S03` | `faultatlas.domain.fault` | `SuppliedFaultScenario` |
| `S1.P06.S03` | `faultatlas.domain.fault` | `SuppliedFaultOccurrenceContext` |
| `S1.P06.S04` | `faultatlas.domain.fault_source_relationship` | `FaultReportSourceObjectAssociation` |
| `S1.P06.S04` | `faultatlas.domain.fault_source_relationship` | `FaultReportHistoryFactAssociation` |
| `S1.P06.S05` | `faultatlas.domain.fault_repair` | `FaultRepairCandidateIdentity` |
| `S1.P06.S05` | `faultatlas.domain.fault_repair` | `SuppliedFaultRepairCandidate` |
| `S1.P06.S05` | `faultatlas.domain.fault_repair` | `FaultRepairCandidateRevisionAssociation` |
| `S1.P06.S05` | `faultatlas.domain.fault_repair` | `FaultRepairCandidateChangeSetAssociation` |
| `S1.P06.S06` | `faultatlas.domain.fault_test` | `FaultTestMaterialIdentity` |
| `S1.P06.S06` | `faultatlas.domain.fault_test` | `SuppliedFaultTestMaterial` |
| `S1.P06.S06` | `faultatlas.domain.fault_test` | `FaultTestRunIdentity` |
| `S1.P06.S06` | `faultatlas.domain.fault_test` | `ReportedFaultTestRun` |
| `S1.P06.S06` | `faultatlas.domain.fault_test` | `ReportedFaultTestOutcomeKind` |
| `S1.P06.S06` | `faultatlas.domain.fault_test` | `ReportedFaultTestOutcome` |
| `S1.P06.S06` | `faultatlas.domain.fault_test` | `FaultTestRunRevisionAssociation` |
| `S1.P06.S06` | `faultatlas.domain.fault_test` | `ReportedFaultTestComparison` |
| `S1.P06.S07` | `faultatlas.domain.fault_interpretation` | `FaultExplanationIdentity` |
| `S1.P06.S07` | `faultatlas.domain.fault_interpretation` | `SuppliedFaultExplanation` |
| `S1.P06.S07` | `faultatlas.domain.fault_interpretation` | `FaultHypothesisIdentity` |
| `S1.P06.S07` | `faultatlas.domain.fault_interpretation` | `SuppliedFaultHypothesis` |
| `S1.P06.S07` | `faultatlas.domain.fault_interpretation` | `FaultExpectedPropertyIdentity` |
| `S1.P06.S07` | `faultatlas.domain.fault_interpretation` | `SuppliedFaultExpectedProperty` |
| `S1.P06.S08` | `faultatlas.domain.fault_instance` | `FaultInstance` |
| `S1.P06.S09` | `faultatlas.domain.fault_evidence_link` | `FaultInstanceEvidenceLink` |

## 9. `S1.P06.S11` Entry Readiness

| # | Prerequisite | Status |
| --- | --- | --- |
| 01 | `S1.P06.S01_through_S1.P06.S09_present_on_canonical_main` | `satisfied` |
| 02 | `all_seven_P06_product_modules_present` | `satisfied` |
| 03 | `all_thirty_P06_product_symbols_present` | `satisfied` |
| 04 | `inherited_deferred_subject_dispositioned_exactly_once` | `satisfied` |
| 05 | `self_owned_open_is_zero` | `satisfied` |
| 06 | `both_effective_P05_to_P06_requirements_satisfied` | `satisfied` |
| 07 | `all_effective_prohibitions_preserved` | `satisfied` |
| 08 | `S1.P06.S09_canonical_vertical_exists` | `satisfied` |
| 09 | `S11_can_replay_P06_semantics_without_executing_external_repositories` | `satisfied` |
| 10 | `no_S11_contract_corpus_exists_yet` | `satisfied` |
| 11 | `S11_has_not_begun_during_S10` | `satisfied` |
| 12 | `package_remains_twenty_production_modules` | `satisfied` |

Unsatisfied prerequisites: 0. `S1.P06.S11` contract corpus: `eligible_to_begin`. Implementation state: `not_started`.

Governance readiness is recorded separately from semantic readiness. `S1.P06.S09` publication state: `compliant`. Publication-governance exception: `absent`. Blocks `S1.P06.S11` semantic corpus construction: `false`. Must be preserved for `S1.P06.S12` closure: `true`.

## 10. Publication Governance

### 10.1 `S1.P06.S09` — compliant publication

The S1.P06.S09 pull request was merged under an active ruleset that evaluated pass on every rule. The merge command carried an administrator flag, but the ruleset configures no bypass actor, no bypass was recorded, and the flag therefore changed nothing. The only condition that ever refused the merge was an unresolved review thread, which was resolved before the successful retry.

| Fact | Value |
| --- | --- |
| pull request | #83 |
| merge method | `squash_under_an_active_ruleset` |
| rule suite | `4016672138` |
| ruleset result | `pass` |
| ruleset condition satisfied | `true` |
| administrator flag passed | `true` |
| bypass exercised | `false` |
| bypass actors configured | 0 |
| bypass records in period | 0 |
| refused earlier attempt | `4016654651` |
| squash commit | `8fcc1fbda571d7bc0447e1a298f51d810915d287` |
| reviewed tree == squash tree | `2bc107981e3573fefb132af366a09d05045d0506` |
| must be preserved for `S1.P06.S12` | `true` |

Evidence:

- rule suite 4016672138 evaluated the push that created the squash commit and returned result pass
- all five active rules passed: pull_request, required_status_checks, required_linear_history, non_fast_forward, deletion
- the ruleset configures no bypass actor and reports that the repository owner can never bypass it, so the administrator flag the merge command carried could not take effect
- no bypass record exists for the repository in the surrounding period
- the pull request's single commit is attributed to a recognised account, so the extra-approval condition for unattributed changes was never triggered
- the earlier attempt, rule suite 4016654651, was refused by the same active pull_request rule because one review thread was unresolved; the thread was resolved and the retry evaluated pass

This record explicitly does not say:

- an administrator bypass occurred
- the ruleset was overridden
- a required condition was skipped

Unresolved exceptions: 0.

### 10.2 Evidential status

This verdict is not offline-replayable. The provider responses it rests on are cited by their stable identifiers but are not retained in this repository, so a replay can confirm only that this artifact records them, never that the provider reported them. Model-generated analysis is not verified fact, and this verdict is analysis of an external record rather than a retained observation. Retaining bounded immutable snapshots of those responses is acquisition work outside this Slice's write closure and is not performed here.

| Fact | Value |
| --- | --- |
| basis | `provider_ruleset_evaluation_read_at_publication_time` |
| observed at | `2026-09-10T09:40:00Z` |
| cited by | `stable_provider_rule_suite_identifiers` |
| provider records retained | `false` |
| replayable offline | `false` |
| `S1.P06.S12` must re-verify | `true` |

Recorded from the provider's own ruleset evaluation rather than from the merging session's account of itself. An earlier S1.P06.S10 draft, and the S1.P06.S09 session report it drew on, described this merge as an administrator override that bypassed the ruleset. That description was wrong in the direction of non-compliance, and it is corrected here rather than sealed. S1.P06.S12 may read this as an ordinary compliant publication. S1.P06.S10 does not decide whether S1.P06.S12 may close the Phase; S1.P06.S12 owns that decision.

## 11. Non-Generalizations

- FaultAtlas publishes no universal relationship ontology
- no generic Relationship, Edge, Graph, or RelationKind type exists
- no relationship registry or provider-independent relation vocabulary exists
- arbitrary relationships between arbitrary subjects are not representable
- no repository evolution graph semantics exist
- no ancestry, reachability, merge-base, or branch-containment semantics exist
- no cross-case relationship generalization exists
- generic repository and evolution graph semantics remain owned by S5 under their own authority
- S1.P06.S10 adds no production module, symbol, or product semantics

Intentional deferral is not implementation failure: `true`.

## 12. Source Locks

| Lock | Path | Bytes | SHA-256 |
| --- | --- | --- | --- |
| `authority:s1-p05-s08` | `reference_corpus/contracts/development-history/decisions/s08-deferred-subject-disposition/decision.json` | 36563 | `8df7a989ef33fb5d6e70c8815d1b74748c8c2f98cfb7e581414548a403d65cfe` |
| `authority:s1-p05-s08-c01` | `reference_corpus/contracts/development-history/corrections/s08-c01-deferred-subject-owner-topology/correction.json` | 29366 | `1ca0459edcc44951639c7b465f47eca43221d892a1621030267cb72fbcdd3bc3` |
| `authority:s1-p05-s10` | `reference_corpus/contracts/development-history/closures/s1-p05-phase-closure/closure.json` | 67457 | `9f5ff594a841ccca1c9ff05d286f3cf774a87ebdd4b7da4c07facf7a62afed23` |

Cited artifacts: 3. Immutable: `true`. Sealed at `2026-09-10T09:40:00Z`.
