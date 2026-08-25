# Development History Deferred-Subject Disposition

## 1. Scope and Authority Warning

This internal, case-calibrated `S1.P05.S08` decision is not a production schema, class, adapter, reader, writer, migration, persistence contract, or public API. `decision.json` is the sole durable semantic authority; this Markdown is derived. The Slice is governance-only: no production Python source changed and the production source count remains 13.

## 2. Exact `decision.json` SHA-256

`8df7a989ef33fb5d6e70c8815d1b74748c8c2f98cfb7e581414548a403d65cfe`

## 3. Result

`S1.P05` inherited 12 deferred subjects from `S1.P00`, `S1.P01`, `S1.P02`, `S1.P03`, and `S1.P04`, and introduced 0 of its own. Each is dispositioned exactly once. 4 are split into an addressed portion and a carried-forward remainder, and 8 are carried forward whole to valid later owners.

    self_owned_open == 0

Nothing unsupported is claimed as implemented, no predecessor artifact is edited, no historical unknown is replaced by a current observation, and no placeholder production model is created.

## 4. Inherited Subjects and Dispositions

| # | Subject | Source | Pointer | Disposition |
| --- | --- | --- | --- | --- |
| 1 | discussion edit and deletion history unknown (`gap:s05-known:discussion-edit-and-deletion-history-unknown`) | S1.P00_phase_closure | `/deferred_register/items/4` | `unknown_pending_additional_evidence` to `S2` / `S2` |
| 2 | case relationship vocabulary provisional (`gap:s05-known:case-relationship-vocabulary-provisional`) | S1.P00_phase_closure | `/deferred_register/items/18` | `unsupported_current_scope` to `S1.P06` / `S1.P06` |
| 3 | development history event model (`deferred:p01:p05-development-history-event-model`) | S1.P01_phase_closure | `/deferred_register/items/18` | split: addressed by `S1.P05.S03`, `S1.P05.S04`, `S1.P05.S05`, `S1.P05.S06`; remainder `unsupported_current_scope` to `S1.P06` / `S1.P06` |
| 4 | development history relationship model (`deferred:p01:p05-development-history-relationship-model`) | S1.P01_phase_closure | `/deferred_register/items/19` | `unsupported_current_scope` to `S1.P06` / `S1.P06` |
| 5 | evidence original head repository (`deferred:p01:evidence-original-head-repository`) | S1.P01_phase_closure | `/deferred_register/items/33` | `evidence_insufficient` to `S2` / `S5` |
| 6 | evidence historical source completeness (`deferred:p01:evidence-historical-source-completeness`) | S1.P01_phase_closure | `/deferred_register/items/34` | `evidence_insufficient` to `S2` / `S5` |
| 7 | revision ref and path event history (`deferred:21`) | S1.P02_phase_closure | `/deferred_register/items/20` | split: addressed by `S1.P05.S05`, `S1.P05.S06`; remainder `evidence_insufficient` to `S2` / `S5` |
| 8 | ancestry and reachability (`deferred:22`) | S1.P02_phase_closure | `/deferred_register/items/21` | `unsupported_current_scope` to `S1.P06` / `S1.P06` |
| 9 | path rename and copy history (`deferred:23`) | S1.P02_phase_closure | `/deferred_register/items/22` | `evidence_insufficient` to `S2` / `S5` |
| 10 | complete discussion and history relationships (`deferred:24`) | S1.P02_phase_closure | `/deferred_register/items/23` | split: addressed by `S1.P05.S03`; remainder `unsupported_current_scope` to `S1.P06` / `S1.P06` |
| 11 | development_history_model (`deferred:02`) | S1.P03_phase_closure | `/deferred_register/entries/1` | split: addressed by `S1.P05.S01`, `S1.P05.S02`, `S1.P05.S03`, `S1.P05.S04`, `S1.P05.S05`, `S1.P05.S06`, `S1.P05.S07`; remainder `unsupported_current_scope` to `S1.P06` / `S1.P06` |
| 12 | default-branch observation (`deferred:p04:04`) | S1.P04_phase_closure | `/deferred_register/items/3` | `unsupported_current_scope` to `S5` / `S5` |

## 5. Per-Subject Rationale

### 5.1 discussion edit and deletion history unknown — `gap:s05-known:discussion-edit-and-deletion-history-unknown`

Source: `reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json` at `/deferred_register/items/4`, SHA-256 `8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e`. Predecessor wording: "Discussion edit and deletion history unknown". Predecessor state: `unknown_pending_additional_evidence`. Predecessor immediate owner: `S1.P05`.

**Carried forward** — discussion edit and deletion history, state `unknown_pending_additional_evidence`, immediate owner `S2`, preserved long-term owner `S2`. The retained acquisition carries no edit or deletion field for any discussion surface: it records no edited, edited_at, or deleted_at member on any comment, review, or timeline item. Absence of retained edit evidence is not evidence that no edit occurred, and S1.P05 published nothing that asserts either. Establishing whether discussion content was edited or deleted requires separately authorized historical acquisition owned by S2, exactly as the source item states.

### 5.2 case relationship vocabulary provisional — `gap:s05-known:case-relationship-vocabulary-provisional`

Source: `reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json` at `/deferred_register/items/18`, SHA-256 `8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e`. Predecessor wording: "Case relationship vocabulary provisional". Predecessor state: `provisional_pending_later_phase_design`. Predecessor immediate owner: `S1.P05`.

**Carried forward** — universal relationship vocabulary, state `unsupported_current_scope`, immediate owner `S1.P06`, preserved long-term owner `S1.P06`. The retained case vocabulary names cross-referenced, mentioned, and subscribed timeline relations and one reviewed-derived Issue-to-Pull-Request pairing. S1.P05 published no relationship vocabulary and deliberately did not schedule the Issue pairing as a product relation. A universal relationship schema requires additional cases and explicit claim design, which the source item states directly; the consuming semantics belong to the FaultInstance layer in S1.P06 rather than to the bounded history-fact layer.

### 5.3 development history event model — `deferred:p01:p05-development-history-event-model`

Source: `reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json` at `/deferred_register/items/18`, SHA-256 `2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642`. Predecessor wording: "P05 development history event model is outside S1.P01 and remains owned by S1.P05.". Predecessor state: `provisional_design`. Predecessor immediate owner: `S1.P05`.

The inherited subject is broader than what S1.P05 established. The three occurrence families the retained material supplies are addressed; a generic event framework is not, and is carried forward with a valid later owner rather than claimed.

**Addressed** — bounded pull-request occurrence facts and their source occurrence times. S1.P05.S03, S1.P05.S04, and S1.P05.S05 published the review revision approval, the merge revision outcome, and the head-ref deletion, and S1.P05.S06 published PullRequestHistoricalOccurrenceTime, which names the source instant at which exactly one of those three already published facts occurred. The subject position carries the meaning, so the embedded relation is the event kind. These are exactly the occurrence kinds the retained chronology supplies.

**Carried forward** — generic development-history event framework, state `unsupported_current_scope`, immediate owner `S1.P06`, preserved long-term owner `S1.P06`. A generic DevelopmentEvent, EventKind, Timeline, or Chronology type is deliberately absent. The retained timeline carries eleven items across nine event lexemes, of which only three correspond to a published S1.P05 relation; inventing a generic event framework would publish a vocabulary the retained material does not calibrate. No product consumer exists below S1.P06, so the generic remainder is carried forward rather than fabricated.

### 5.4 development history relationship model — `deferred:p01:p05-development-history-relationship-model`

Source: `reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json` at `/deferred_register/items/19`, SHA-256 `2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642`. Predecessor wording: "P05 development history relationship model is outside S1.P01 and remains owned by S1.P05.". Predecessor state: `provisional_design`. Predecessor immediate owner: `S1.P05`.

**Carried forward** — generic development-history relationship model, state `unsupported_current_scope`, immediate owner `S1.P06`, preserved long-term owner `S1.P06`. S1.P05 published relations between a pull request and revisions, paths, reviews, merges, and ref deletions, each a bounded two-position fact. It published no relationship model over development-history entities themselves, and no generic relation type. The retained cross-reference, mention, and subscription relations have no published S1.P05 product type and no consumer below the FaultInstance layer, so a generic relationship model would be invented rather than evidenced.

### 5.5 evidence original head repository — `deferred:p01:evidence-original-head-repository`

Source: `reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json` at `/deferred_register/items/33`, SHA-256 `2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642`. Predecessor wording: "Evidence for evidence original head repository is insufficient in the current single-case calibration.". Predecessor state: `evidence_insufficient`. Predecessor immediate owner: `S1.P05`.

**Carried forward** — original head repository identity, state `evidence_insufficient`, immediate owner `S2`, preserved long-term owner `S5`. The retained acquisition records original_head_repository_identity as unknown and head_repository_state as unavailable. The head repository was already gone at acquisition time, so the identity cannot be recovered from this case at all. Acquiring head-repository evidence where it still exists is source ingestion owned by S2, and the repository-graph semantics over such evidence are owned by S5. S1.P05.S05 published the head-ref deletion without ever naming a head repository, and must not be read as having established one.

### 5.6 evidence historical source completeness — `deferred:p01:evidence-historical-source-completeness`

Source: `reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json` at `/deferred_register/items/34`, SHA-256 `2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642`. Predecessor wording: "Evidence for evidence historical source completeness is insufficient in the current single-case calibration.". Predecessor state: `evidence_insufficient`. Predecessor immediate owner: `S1.P05`.

**Carried forward** — historical source completeness, state `evidence_insufficient`, immediate owner `S2`, preserved long-term owner `S5`. Each retained collection declares pagination_complete for the surface it selected, which establishes completeness of the retained selection and not of provider history. One case cannot calibrate historical source completeness, and no S1.P05 value expresses completeness of any kind. Acquiring broader historical evidence is owned by S2 and the completeness semantics over that evidence are owned by S5, matching the disposition S1.P04.S08 already applied to whole-repository completeness.

### 5.7 revision ref and path event history — `deferred:21`

Source: `reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json` at `/deferred_register/items/20`, SHA-256 `daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67`. Predecessor wording: "revision ref and path event history". Predecessor state: `provisional_design`. Predecessor immediate owner: `S1.P05`.

The inherited subject spans ref history and path history. One historical ref occurrence is addressed; complete mutable-ref history, ref reuse, and all path event history are not, and are carried forward with valid later owners rather than claimed.

**Addressed** — one historical head-ref deletion occurrence for one pull request. S1.P05.S05 published PullRequestHeadRefDeletion, which carries the recorded head binding and the head-ref lexeme and states that the ref was deleted, and S1.P05.S06 bound that occurrence to its retained source instant. This is exactly one historical ref occurrence for one pull request, which the retained lifecycle event supplies.

**Carried forward** — complete mutable-ref history and all path event history, state `evidence_insufficient`, immediate owner `S2`, preserved long-term owner `S5`. The published deletion names a ref lexeme and one occurrence; it establishes no underlying Git ref identity, no creation, no rename, no recreation, and no reuse, and it says nothing about any other ref. No path event history exists at all: the retained traversals carry only logical_path, non_recursive, request_ordinal, requested_tree_sha, and truncated, and retain no path lifecycle. Acquiring ref and path event history is source ingestion owned by S2, and the semantics over that evidence are repository-graph semantics owned by S5.

### 5.8 ancestry and reachability — `deferred:22`

Source: `reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json` at `/deferred_register/items/21`, SHA-256 `daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67`. Predecessor wording: "ancestry and reachability". Predecessor state: `provisional_design`. Predecessor immediate owner: `S1.P05`.

**Carried forward** — ancestry and reachability, state `unsupported_current_scope`, immediate owner `S1.P06`, preserved long-term owner `S1.P06`. No published S1.P05 value expresses ancestry, descendance, reachability, branch containment, merge-base, or integration path, and every such term appears in faultatlas.domain.history only as an explicit non-claim. The retained comparison does carry ahead_by, behind_by, merge_base_sha, and a status lexeme, and the retained merge resolution carries ordered merge parents, but S1.P05 deliberately published none of them, and S1.P05.S02 routed the deterministic ahead, behind, and merge-base derivations to this very subject. Ancestry must not be inferred from commit ordering, parent counts, timestamps, or a comparison result, so the subject is carried forward whole for the layer that consumes such relations.

### 5.9 path rename and copy history — `deferred:23`

Source: `reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json` at `/deferred_register/items/22`, SHA-256 `daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67`. Predecessor wording: "path rename and copy history". Predecessor state: `provisional_design`. Predecessor immediate owner: `S1.P05`.

**Carried forward** — path rename and copy history, state `evidence_insufficient`, immediate owner `S2`, preserved long-term owner `S5`. The retained change evidence supplies no rename or copy semantics whatsoever: neither retained changed-path surface carries a rename, copy, previous_filename, or similarity member, and the retained status vocabulary is exactly added and modified. S1.P05.S02 published ChangedPathStatus with exactly those two members, which is evidence-faithful rather than an omission. Rename must not be inferred from content similarity or from a path disappearing and another appearing, so acquiring rename evidence is owned by S2 and the semantics over it by S5.

### 5.10 complete discussion and history relationships — `deferred:24`

Source: `reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json` at `/deferred_register/items/23`, SHA-256 `daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67`. Predecessor wording: "complete discussion and history relationships". Predecessor state: `provisional_design`. Predecessor immediate owner: `S1.P05`.

The inherited subject asks for complete discussion and history relationships. One reviewed relation is addressed; the complete discussion graph is not, and is carried forward with a valid later owner rather than claimed.

**Addressed** — one published review-to-revision approval relation. S1.P05.S03 published PullRequestReviewRevisionApproval, binding one published review identity to the immutable revision it approved. That is one discussion-originated relation carried as a product fact, and the retained material supplies exactly one such review.

**Carried forward** — complete discussion and history relationship graph, state `unsupported_current_scope`, immediate owner `S1.P06`, preserved long-term owner `S1.P06`. The retained material carries cross-referenced, mentioned, and subscribed relations, three top-level comments, a separate issue surface, and one Issue-to-Pull-Request pairing classified as a reviewed derived interpretation rather than a provider fact. None has a published S1.P05 product type, and the pairing is deliberately not scheduled as one. A complete discussion and history relationship graph is FaultInstance-consuming semantics owned by S1.P06, and completeness of a discussion graph must not be inferred from the retained selected events.

### 5.11 development_history_model — `deferred:02`

Source: `reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure/closure.json` at `/deferred_register/entries/1`, SHA-256 `21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b`. Predecessor wording: "development_history_model". Predecessor state: `not_implemented`. Predecessor immediate owner: `S1.P05`.

The inherited subject reserved a development_history_model. A bounded history-fact layer is addressed; a complete provider development-history graph is not, and is carried forward with a valid later owner rather than claimed.

**Addressed** — bounded pull-request development-history fact model with LEVEL-1 evidence association. S1.P05 published a bounded development-history surface: eight history values in faultatlas.domain.history covering revision role bindings, changed paths and their supplied change set, review revision approval, merge revision outcome, head-ref deletion, and historical occurrence time, together with one cross-domain bridge value in faultatlas.domain.history_evidence_link associating those facts with durable evidence records at LEVEL 1. That is the bounded history-fact model this item reserved, and it is sufficient for the canonical vertical.

**Carried forward** — complete provider development-history graph, state `unsupported_current_scope`, immediate owner `S1.P06`, preserved long-term owner `S1.P06`. The published surface is bounded pull-request history facts, not a complete repository or provider development-history graph. It carries no event framework, no relationship model, no chronology, no completeness claim, and no non-pull-request development subject. Calling the current surface a complete development history would overstate what the authority supports, so the remainder is carried forward.

### 5.12 default-branch observation — `deferred:p04:04`

Source: `reference_corpus/contracts/repository-snapshot/closures/s1-p04-phase-closure/closure.json` at `/deferred_register/items/3`, SHA-256 `8605fdd7972f18c0e9c85f26cb0c366e71362630f25ea87a4cd6c22cc85aee74`. Predecessor wording: "P02 deferred:19 default-branch observation". Predecessor state: `unsupported_current_scope`. Predecessor immediate owner: `S1.P05`.

**Carried forward** — default-branch designation semantics, state `unsupported_current_scope`, immediate owner `S5`, preserved long-term owner `S5`. This subject is the default-branch designation model, and it is not the historical default branch. The two are separate inherited subjects and are kept separate here. The retained repository observation already supplies a current designation, recording the value main observed at 2026-07-24, so this subject is not blocked on acquisition and is not routed to an acquisition owner; what is missing is a semantic owner for designation over retained mutable-ref observations, which is repository-graph semantics owned by S5. S1.P05 published no such model and must not be read as having published one. The pull request under analysis targeted a base ref named master in 2018, which disagrees with the current observation and is in any case a base-ref lexeme rather than a designation, so neither may be substituted for the other. The historical default branch at the canonical occurrence time has no retained evidence at all and remains the separately owned subject gap:s05-known:historical-default-branch-unknown, dispositioned to S2 by S1.P04.S08 at /inherited_subject_register/items/6 and recorded at /deferred_register/items/6 of the S1.P04 phase closure; it is deliberately not merged into this subject and not re-dispositioned here.

## 6. Downstream Handoffs

### 6.1 `S2` — `handoff:s1-p05-s08:s2`

Received subjects: discussion edit and deletion history, original head repository identity, historical source completeness, complete mutable-ref history and all path event history, path rename and copy history.

Requirements: `acquire_and_retain_ref_and_path_event_history_under_a_separately_authorized_evidence_gate`, `acquire_and_retain_rename_and_copy_evidence_rather_than_inferring_it`, `preserve_the_historical_default_branch_as_unknown_until_genuine_historical_evidence_exists`.

Prohibited: `substitute_a_current_observation_for_a_historical_unknown`, `treat_absence_of_retained_edit_evidence_as_absence_of_edits`, `treat_this_decision_as_a_production_schema`.

Status: `not_started`.

### 6.2 `S5` — `handoff:s1-p05-s08:s5`

Received subjects: original head repository identity, historical source completeness, complete mutable-ref history and all path event history, path rename and copy history, default-branch designation semantics.

Requirements: `own_repository_graph_semantics_over_retained_ref_and_path_evidence`, `own_historical_source_completeness_semantics`, `own_default_branch_designation_semantics_over_retained_mutable_ref_observations`.

Prohibited: `derive_completeness_or_reachability_from_caller_supplied_S1_P05_values`, `merge_the_separately_owned_historical_default_branch_unknown_into_the_designation_subject`, `substitute_a_current_observation_for_a_historical_unknown`.

Status: `not_started`.

### 6.3 `S1.P06` — `handoff:s1-p05-s08:s1-p06`

Received subjects: universal relationship vocabulary, generic development-history event framework, generic development-history relationship model, ancestry and reachability, complete discussion and history relationship graph, complete provider development-history graph.

Requirements: `own_fault_instance_consuming_relationship_and_event_semantics`, `consume_the_bounded_S1_P05_history_facts_without_redefining_them`.

Prohibited: `read_the_bounded_S1_P05_surface_as_a_complete_development_history`, `upgrade_the_LEVEL_1_evidence_association_implicitly`.

Status: `not_started`.

## 7. Preserved Non-Generalizations

- no historical default-branch substitution from a current observation
- the default-branch designation subject and the historical default-branch unknown remain separate subjects with separate owners
- no default-branch designation model in S1.P05
- no ancestry, descendance, reachability, containment, merge-base, or integration-path semantics
- no rename or copy inference from path similarity or from disappearance and addition
- no complete mutable-ref history and no path event history
- no generic development event, event-kind, timeline, or chronology framework
- no generic development-history relationship model
- no complete discussion or history relationship graph
- no historical source completeness and no provider-history exhaustiveness
- absence of retained edit or deletion evidence is not absence of edits or deletions
- S1.P05.S07 evidence association remains LEVEL 1 record-level only with no fact-level locator
- intentional evidence-gated deferral is not implementation failure

## 8. Predecessor Integrity

A successor decision cites each predecessor item by exact path, json pointer, and sha-256 and restates its ownership under s1.p05 disposition identifiers; no predecessor byte is edited. Predecessor statements remain historically correct and the register is append-only.

## 9. Locked Source Artifacts

| Lock | Path | Bytes | SHA-256 |
| --- | --- | --- | --- |
| `closure:s1-p00` | `reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json` | 102190 | `8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e` |
| `closure:s1-p01` | `reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json` | 112606 | `2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642` |
| `closure:s1-p02` | `reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json` | 100669 | `daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67` |
| `closure:s1-p03` | `reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure/closure.json` | 127921 | `21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b` |
| `closure:s1-p04` | `reference_corpus/contracts/repository-snapshot/closures/s1-p04-phase-closure/closure.json` | 51268 | `8605fdd7972f18c0e9c85f26cb0c366e71362630f25ea87a4cd6c22cc85aee74` |
| `acquisition:pytest-4412-run-0001` | `reference_corpus/pytest-4412/acquisitions/run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json` | 61283 | `1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318` |
