# Development History Contract Corpus

## 1. Scope and Authority Warning

This internal, source-only `S1.P05.S09` contract corpus is not a production schema, class, adapter, reader, writer, migration, persistence contract, or public API. The four canonical JSON files are the semantic authority; this Markdown is derived. The corpus is executed only by `tests/test_development_history_contract_corpus.py` and is excluded from the wheel and the sdist.

## 2. Covered Product Surface

Two `S1.P05` production modules and nine published product symbols:

| Symbol | Module | Slice | Target class |
| --- | --- | --- | --- |
| `PullRequestRevisionRoleBinding` | `faultatlas.domain.history` | `S1.P05.S01` | `record_model_target` |
| `ChangedPathStatus` | `faultatlas.domain.history` | `S1.P05.S02` | `vocabulary_enum_target` |
| `PullRequestChangedPath` | `faultatlas.domain.history` | `S1.P05.S02` | `record_model_target` |
| `PullRequestChangeSet` | `faultatlas.domain.history` | `S1.P05.S02` | `record_model_target` |
| `PullRequestReviewRevisionApproval` | `faultatlas.domain.history` | `S1.P05.S03` | `record_model_target` |
| `PullRequestMergeRevisionOutcome` | `faultatlas.domain.history` | `S1.P05.S04` | `record_model_target` |
| `PullRequestHeadRefDeletion` | `faultatlas.domain.history` | `S1.P05.S05` | `record_model_target` |
| `PullRequestHistoricalOccurrenceTime` | `faultatlas.domain.history` | `S1.P05.S06` | `record_model_target` |
| `PullRequestHistoryFactEvidenceLink` | `faultatlas.domain.history_evidence_link` | `S1.P05.S07` | `record_model_target` |

Supporting authorities are consumed but not owned: `faultatlas.domain.evidence`, `faultatlas.domain.identity`, `faultatlas.domain.revision`. `faultatlas.domain.snapshot` and `faultatlas.domain.snapshot_evidence_link` are outside this corpus: no `S1.P05` value consumes them.

## 3. Vector Inventory

| Family | valid | invalid | replay |
| --- | --- | --- | --- |
| `change-set` | 5 | 17 | 0 |
| `changed-path` | 4 | 10 | 3 |
| `changed-path-status` | 3 | 4 | 0 |
| `evidence-association` | 0 | 0 | 12 |
| `evidence-link` | 15 | 29 | 0 |
| `head-ref-deletion` | 3 | 8 | 1 |
| `merge-outcome` | 3 | 8 | 1 |
| `occurrence-time` | 7 | 12 | 3 |
| `review-approval` | 3 | 10 | 1 |
| `revision-role-binding` | 0 | 0 | 2 |
| `role-binding` | 5 | 11 | 0 |
| `supplied-change-set` | 0 | 0 | 1 |
| **total** | **48** | **109** | **24** |

181 vectors over 19 declared fixtures. Every vector occupies a distinct semantic partition.

## 4. Replay and Provenance

The canonical replay does not flatten its layers into evidence-derived history. Three classifications are used and a fourth is deliberately absent:

- `caller_supplied_association` — S07 history-fact evidence links
- `caller_supplied_composition` — the S02 supplied change set
- `retained_normalized_observation` — S01 bindings, S02 changed paths, S03 approval, S04 merge outcome, S05 deletion, and S06 occurrence instants

`deterministic_derivation` is not present: `S1.P05` publishes no deterministic derivation, and the ahead, behind, and merge-base values the retained comparison carries remain deferred with `S1.P02` `deferred:22`.

Eleven history facts are individually linkable. `PullRequestChangeSet` is a published product fact and is replayed as a caller-supplied composition, but `S1.P05.S07` does not admit it as an evidence-link fact, and the replay preserves that asymmetry.

Every retained `role` is derived from the source position its revision digest was read from rather than trusted from the vector, so a swapped role fails even when every digest is re-sealed:

- `/observations/comparison/base_sha` implies `base`
- `/observations/comparison/head_sha` implies `head`
- `/observations/pr/attempts/0/bracket_a/head/sha` implies `head`

A caller-supplied composition or association cites no retained location of its own; each embedded fact is instead bound to the retained vector it reuses, so its nested values inherit that provenance.

## 5. Objective and Descriptive Declarations

Every manifest declaration is exactly one of two kinds. An **objective** declaration is compared with something outside the manifest -- the live `__all__`, the filesystem, the sealed vector files, the locked source documents, or the executor's own registries -- and the focused oracle fails if any objective leaf has no such consumer. A **descriptive** declaration has no independent source of truth; the exact leaf paths are enumerated in `descriptive_metadata.paths` (83 of them) and are never counted as verified assurance.

Fixture values are inlined in the vectors rather than referenced by marker. The manifest records that mechanism as `inlined_values_with_test_only_explicit_semantic_bindings`: the corpus carries the values, and the oracle resolves each of the 19 declared fixtures to an exact vector, side, and JSON pointer rather than searching for an equal value.

## 6. Rejection Contract

Invalid vectors lock `failure_category`, `error_location`, `error_location_mode`, `error_type`. Prose messages, Pydantic internal union branch labels, and validator function names are deliberately not locked. The `prefix` location mode is used only where a discriminatorless union reports per-branch locations: the `S1.P05.S06` occurrence union and the `S1.P05.S07` fact union.

The eleven `S1.P05.S07` forbidden extras protect eleven DIFFERENT published non-claims. Further spellings of one boundary earn no partition: `field_path`, `semantic_path`, and `evidence_locator` restate the localization non-claim `json_pointer` already carries.

| Extra key | Published non-claim |
| --- | --- |
| `artifact` | no direct artifact or envelope carrier coupling |
| `confidence` | no confidence or review-status semantics |
| `evidence_records` | no evidence aggregation |
| `json_pointer` | no field-level or semantic evidence localization |
| `primary_evidence` | no primary-evidence designation or ranking |
| `request_id` | no acquisition-request provenance coupling |
| `schema_version` | no top-level history-evidence-link schema version |
| `strength` | no support-strength semantics |
| `superseded` | no automatic correction or supersession traversal |
| `support_role` | no support-role semantics |
| `verification` | no verification or proof semantics |

## 7. Effective Governance

`S1.P05.S08` and its append-only `S1.P05.S08.C01` correction are consumed as source authorities and are never vectorized as product behaviour. The executor recomputes the effective projection from both artifacts rather than trusting a stored table:

    inherited 12 · exactly once 12 · self-introduced 0 · self_owned_open 0
    split 5 · carried_forward 7
    immediate S1.P06 1 · S2 6 · S5 5
    long-term S1.P06 1 · S5 11
    authority S1.P05.S08 6 · S1.P05.S08.C01 6

## 8. Non-Generalizations

- no complete development-history graph
- no generic DevelopmentEvent
- no generic relationship graph
- no ancestry or reachability semantics
- no merge-base semantics
- no ahead or behind semantics
- no branch containment
- no historical default-branch substitution
- current default branch is not historical truth
- no rename or copy semantics
- no complete mutable-ref history
- no complete discussion history
- no edit or deletion absence claim
- no complete historical review state
- no timestamp-implied causality
- approval does not cause merge
- merge does not cause ref deletion
- no CI or test correctness
- no repair correctness
- no FaultInstance semantics
- no root cause
- no violated invariant
- no S1.P09 confidence or review interpretation
- no field-level evidence locator
- no verification or support strength
- no persistence
- no production serializer or registry
- no production corpus reader
- no source ingestion
- no Git or GitHub I/O
- no retrieval or RAG
- generic repository or evolution graph is S5-owned, not S1.P06-owned

## 9. Locked Source Authorities

| Authority | Role | SHA-256 |
| --- | --- | --- |
| `decision:s1-p05-s08:disposition` | `governance_disposition_not_vectorized` | `8df7a989ef33fb5d6e70c8815d1b74748c8c2f98cfb7e581414548a403d65cfe` |
| `correction:s1-p05-s08-c01:owner-topology` | `append_only_owner_topology_correction` | `1ca0459edcc44951639c7b465f47eca43221d892a1621030267cb72fbcdd3bc3` |
| `closure:s1-p03:evidence-envelope` | `originating_development_history_model_reservation` | `21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b` |
| `acquisition:run-0001` | `retained_replay_evidence` | `1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318` |
| `correction:s04-c01-acquisition-closure` | `retained_additive_correction_evidence` | `44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2` |
