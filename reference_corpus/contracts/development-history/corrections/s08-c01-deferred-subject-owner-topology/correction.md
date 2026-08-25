# Development History Deferred-Subject Owner-Topology Correction

## 1. Scope and Authority Warning

This internal, case-calibrated `S1.P05.S08.C01` correction is not a production schema, class, adapter, reader, writer, migration, persistence contract, or public API. `correction.json` is the sole durable semantic authority for this correction; this Markdown is derived. The Slice is governance-only: no production Python source changed and the production source count remains 13.

## 2. Exact `correction.json` SHA-256

`46e60fe7193532fad71a428fa752e8b931ba4f1f9fe157500da4572a5bdd838e`

## 3. Append-Only Relationship to `S1.P05.S08`

The correction cites each superseded disposition by exact path, json pointer, and sha-256 of the sealed s1.p05.s08 decision and restates its ownership under s1.p05.s08.c01 correction identifiers; no predecessor byte is edited and the predecessor digest is unchanged.

The published `S1.P05.S08` decision remains immutable historical provenance. Its bytes are unmodified, its digest is unchanged, and it is not regenerated. This correction supersedes selected disposition records by citation.

## 4. Result

6 of the twelve published disposition records are superseded and 1 earlier proposed change is deliberately not adopted. The effective projection keeps all 12 inherited subjects dispositioned exactly once with no self-introduced subject.

    self_owned_open == 0

Effective authority: `S1.P05.S08` for 6 subjects and `S1.P05.S08.C01` for 6.

## 5. Superseded Disposition Records

| # | Subject | Published | Corrected | Reason in brief |
| --- | --- | --- | --- | --- |
| 1 | discussion edit and deletion history unknown (`gap:s05-known:discussion-edit-and-deletion-history-unknown`) | `carried_forward` S2 / S2 | `carried_forward` S2 / S5 | The published record kept S2 as both immediate and preserved long-term owner. |
| 2 | development history event model (`deferred:p01:p05-development-history-event-model`) | `split` S1.P06 / S1.P06 | `split` S5 / S5 | The published record routed the generic event framework to S1.P06. |
| 3 | development history relationship model (`deferred:p01:p05-development-history-relationship-model`) | `carried_forward` S1.P06 / S1.P06 | `split` S5 / S5 | The published record carried the whole subject forward to S1.P06 and recorded no addressed portion. |
| 4 | ancestry and reachability (`deferred:22`) | `carried_forward` S1.P06 / S1.P06 | `carried_forward` S5 / S5 | The published record routed ancestry and reachability to S1.P06. |
| 5 | complete discussion and history relationships (`deferred:24`) | `split` S1.P06 / S1.P06 · unsupported_current_scope | `split` S2 / S5 · evidence_insufficient | The published record recorded the remainder as unsupported_current_scope owned by S1.P06. |
| 6 | development_history_model (`deferred:02`) | `split` S1.P06 / S1.P06 | `split` S5 / S5 | The published record routed the complete provider development-history graph to S1.P06. |

## 6. Per-Record Rationale

### 6.1 discussion edit and deletion history unknown — `gap:s05-known:discussion-edit-and-deletion-history-unknown`

Superseded record: `disposition:s1-p05-s08:01` in `reference_corpus/contracts/development-history/decisions/s08-deferred-subject-disposition/decision.json` at `/inherited_subject_register/items/0`, SHA-256 `8df7a989ef33fb5d6e70c8815d1b74748c8c2f98cfb7e581414548a403d65cfe`.

The published record kept S2 as both immediate and preserved long-term owner. Acquisition of discussion edit and deletion evidence is S2 work, but the semantics over that evidence once acquired are development-history evolution semantics owned by S5, matching every other evidence-gated remainder in this register. The immediate owner is unchanged; only the preserved long-term owner is corrected.

### 6.2 development history event model — `deferred:p01:p05-development-history-event-model`

Superseded record: `disposition:s1-p05-s08:03` in `reference_corpus/contracts/development-history/decisions/s08-deferred-subject-disposition/decision.json` at `/inherited_subject_register/items/2`, SHA-256 `8df7a989ef33fb5d6e70c8815d1b74748c8c2f98cfb7e581414548a403d65cfe`.

The published record routed the generic event framework to S1.P06. A generic development or repository event graph is repository and evolution graph semantics, which S5 owns; S1.P06 consumes bounded facts for FaultInstance modelling and does not own a generic event framework. The addressed portion is unchanged: S1.P05.S03 through S1.P05.S06 publish bounded typed historical occurrences and their source occurrence times without any generic framework.

### 6.3 development history relationship model — `deferred:p01:p05-development-history-relationship-model`

Superseded record: `disposition:s1-p05-s08:04` in `reference_corpus/contracts/development-history/decisions/s08-deferred-subject-disposition/decision.json` at `/inherited_subject_register/items/3`, SHA-256 `8df7a989ef33fb5d6e70c8815d1b74748c8c2f98cfb7e581414548a403d65cfe`.

The published record carried the whole subject forward to S1.P06 and recorded no addressed portion. That understated what S1.P05 published and misrouted the remainder. S1.P05.S01, S1.P05.S03, S1.P05.S04, and S1.P05.S05 publish bounded typed relations between a pull request and revisions, reviews, merges, and ref deletions, so an addressed portion exists and is now recorded. The generic development-history relationship and evolution graph that remains is repository-graph semantics owned by S5 rather than FaultInstance-consuming semantics owned by S1.P06.

**Addressed portion recorded** — bounded typed pull-request history relations, by `S1.P05.S01`, `S1.P05.S03`, `S1.P05.S04`, `S1.P05.S05`. S1.P05.S01 publishes the pull-request-to-revision role binding, S1.P05.S03 the review-to-revision approval, S1.P05.S04 the pull-request-to-merge-revision outcome, and S1.P05.S05 the head binding to head-ref deletion. Each is a bounded two-position typed relation over already published values.

### 6.4 ancestry and reachability — `deferred:22`

Superseded record: `disposition:s1-p05-s08:08` in `reference_corpus/contracts/development-history/decisions/s08-deferred-subject-disposition/decision.json` at `/inherited_subject_register/items/7`, SHA-256 `8df7a989ef33fb5d6e70c8815d1b74748c8c2f98cfb7e581414548a403d65cfe`.

The published record routed ancestry and reachability to S1.P06. Ancestry, descendance, reachability, branch containment, merge-base, and integration path are generic Git graph semantics over repository evidence, which S5 owns. S1.P06 may consume future ancestry facts but does not own a generic Git graph, so routing the subject there would have assigned an owner the published architecture does not support. Nothing about the non-claim changes: no published S1.P05 value expresses any of these relations, and none may be inferred from timestamps, comparison ordering, parent count, ahead or behind values, or merge-base equality.

### 6.5 complete discussion and history relationships — `deferred:24`

Superseded record: `disposition:s1-p05-s08:10` in `reference_corpus/contracts/development-history/decisions/s08-deferred-subject-disposition/decision.json` at `/inherited_subject_register/items/9`, SHA-256 `8df7a989ef33fb5d6e70c8815d1b74748c8c2f98cfb7e581414548a403d65cfe`.

The published record recorded the remainder as unsupported_current_scope owned by S1.P06. The blocking condition is evidence rather than scope: the retained material supplies only a selected set of discussion events for one pull request, and a complete discussion and history relationship record requires acquisition owned by S2 with the evolution-graph semantics over it owned by S5. The state is corrected to evidence_insufficient accordingly. The addressed portion is unchanged.

### 6.6 development_history_model — `deferred:02`

Superseded record: `disposition:s1-p05-s08:11` in `reference_corpus/contracts/development-history/decisions/s08-deferred-subject-disposition/decision.json` at `/inherited_subject_register/items/10`, SHA-256 `8df7a989ef33fb5d6e70c8815d1b74748c8c2f98cfb7e581414548a403d65cfe`.

The published record routed the complete provider development-history graph to S1.P06. A complete repository or provider development-history graph is repository-graph semantics owned by S5. The addressed portion is unchanged: S1.P05.S01 through S1.P05.S07 publish the bounded history model with LEVEL-1 evidence association, which is what the next canonical-contract Phase needs.

## 7. Deliberate Non-Correction

### 7.1 default-branch observation — `deferred:p04:04`

Retained unchanged at `carried_forward`, `unsupported_current_scope`, immediate owner `S5`, preserved long-term owner `S5`.

An earlier orientation table proposed S2 immediate and S5 long-term for this subject. That proposal is not adopted and the published S5/S5 disposition is retained deliberately. The subject is the default-branch designation model, and the retained repository observation already supplies a current designation, recording the value main observed at 2026-07-24, so the subject is not blocked on acquisition and an acquisition immediate owner would misstate why it is unresolved. What is missing is a semantic owner for designation over retained mutable-ref observations, which is repository-graph semantics owned by S5. The separate historical default-branch unknown remains owned by S2 through its own inherited subject and is neither merged here nor re-dispositioned.

## 8. Effective Disposition Projection

| Subject | Disposition | State | Immediate | Long-term | Authority |
| --- | --- | --- | --- | --- | --- |
| discussion edit and deletion history unknown (`gap:s05-known:discussion-edit-and-deletion-history-unknown`) | `carried_forward` | `unknown_pending_additional_evidence` | `S2` | `S5` | `S1.P05.S08.C01` |
| case relationship vocabulary provisional (`gap:s05-known:case-relationship-vocabulary-provisional`) | `carried_forward` | `unsupported_current_scope` | `S1.P06` | `S1.P06` | `S1.P05.S08` |
| development history event model (`deferred:p01:p05-development-history-event-model`) | `split` | `unsupported_current_scope` | `S5` | `S5` | `S1.P05.S08.C01` |
| development history relationship model (`deferred:p01:p05-development-history-relationship-model`) | `split` | `unsupported_current_scope` | `S5` | `S5` | `S1.P05.S08.C01` |
| evidence original head repository (`deferred:p01:evidence-original-head-repository`) | `carried_forward` | `evidence_insufficient` | `S2` | `S5` | `S1.P05.S08` |
| evidence historical source completeness (`deferred:p01:evidence-historical-source-completeness`) | `carried_forward` | `evidence_insufficient` | `S2` | `S5` | `S1.P05.S08` |
| revision ref and path event history (`deferred:21`) | `split` | `evidence_insufficient` | `S2` | `S5` | `S1.P05.S08` |
| ancestry and reachability (`deferred:22`) | `carried_forward` | `unsupported_current_scope` | `S5` | `S5` | `S1.P05.S08.C01` |
| path rename and copy history (`deferred:23`) | `carried_forward` | `evidence_insufficient` | `S2` | `S5` | `S1.P05.S08` |
| complete discussion and history relationships (`deferred:24`) | `split` | `evidence_insufficient` | `S2` | `S5` | `S1.P05.S08.C01` |
| development_history_model (`deferred:02`) | `split` | `unsupported_current_scope` | `S5` | `S5` | `S1.P05.S08.C01` |
| default-branch observation (`deferred:p04:04`) | `carried_forward` | `unsupported_current_scope` | `S5` | `S5` | `S1.P05.S08` |

Dispositions {"carried_forward": 7, "split": 5}; immediate owners {"S1.P06": 1, "S2": 6, "S5": 5}; long-term owners {"S1.P06": 1, "S5": 11}; states {"evidence_insufficient": 5, "unknown_pending_additional_evidence": 1, "unsupported_current_scope": 6}.

## 9. Downstream Handoffs

### 9.1 `S2` — `handoff:s1-p05-s08-c01:s2`

Received subjects: complete discussion and history relationships, discussion edit and deletion history unknown, evidence historical source completeness, evidence original head repository, path rename and copy history, revision ref and path event history.

Requirements: `acquire_and_retain_ref_path_rename_and_discussion_evidence_under_a_separately_authorized_evidence_gate`.

Prohibited: `substitute_a_current_observation_for_a_historical_unknown`, `treat_absence_of_retained_edit_evidence_as_absence_of_edits`, `treat_this_correction_as_a_production_schema`.

### 9.2 `S5` — `handoff:s1-p05-s08-c01:s5`

Received subjects: ancestry and reachability, complete discussion and history relationships, default-branch observation, development history event model, development history relationship model, development_history_model, discussion edit and deletion history unknown, evidence historical source completeness, evidence original head repository, path rename and copy history, revision ref and path event history.

Requirements: `own_repository_and_evolution_graph_semantics_including_generic_event_relationship_and_ancestry_models`, `own_default_branch_designation_semantics_over_retained_mutable_ref_observations`.

Prohibited: `derive_completeness_or_reachability_from_caller_supplied_S1_P05_values`, `infer_ancestry_from_timestamps_ordering_parent_count_or_comparison_values`, `merge_the_separately_owned_historical_default_branch_unknown_into_the_designation_subject`.

### 9.3 `S1.P06` — `handoff:s1-p05-s08-c01:s1-p06`

Received subjects: case relationship vocabulary provisional.

Requirements: `own_the_bounded_domain_relationship_vocabulary_needed_by_FaultInstance`.

Prohibited: `own_a_generic_git_ancestry_or_reachability_graph`, `read_the_bounded_S1_P05_surface_as_a_complete_development_history`, `upgrade_the_LEVEL_1_evidence_association_implicitly`.

## 10. Preserved Non-Generalizations

- no S1.P05 product semantics are added or removed by this correction
- S1.P06 does not own a generic Git ancestry or reachability graph
- S5 ownership of a generic event, relationship, or ancestry model is an owner assignment and not an implementation
- no historical default-branch substitution from a current observation
- the default-branch designation subject and the historical default-branch unknown remain separate subjects with separate owners
- the S1.P05.S08 decision bytes remain valid historical provenance and are not regenerated
- S1.P05.S07 evidence association remains LEVEL 1 record-level only
- intentional evidence-gated deferral is not implementation failure

## 11. Locked Source Artifacts

| Lock | Path | Bytes | SHA-256 |
| --- | --- | --- | --- |
| `decision:s1-p05-s08` | `reference_corpus/contracts/development-history/decisions/s08-deferred-subject-disposition/decision.json` | 36563 | `8df7a989ef33fb5d6e70c8815d1b74748c8c2f98cfb7e581414548a403d65cfe` |
| `closure:s1-p04` | `reference_corpus/contracts/repository-snapshot/closures/s1-p04-phase-closure/closure.json` | 51268 | `8605fdd7972f18c0e9c85f26cb0c366e71362630f25ea87a4cd6c22cc85aee74` |
| `acquisition:pytest-4412-run-0001` | `reference_corpus/pytest-4412/acquisitions/run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json` | 61283 | `1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318` |
