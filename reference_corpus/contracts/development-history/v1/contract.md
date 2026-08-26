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
| `change-set` | 5 | 11 | 0 |
| `changed-path` | 4 | 9 | 3 |
| `changed-path-status` | 3 | 4 | 0 |
| `evidence-association` | 0 | 0 | 12 |
| `evidence-link` | 15 | 28 | 0 |
| `head-ref-deletion` | 3 | 7 | 1 |
| `merge-outcome` | 3 | 6 | 1 |
| `occurrence-time` | 7 | 11 | 3 |
| `review-approval` | 3 | 8 | 1 |
| `revision-role-binding` | 0 | 0 | 2 |
| `role-binding` | 5 | 11 | 0 |
| `supplied-change-set` | 0 | 0 | 1 |
| **total** | **48** | **95** | **24** |

167 vectors over 19 declared fixtures. Every vector occupies a distinct semantic partition.

## 4. Replay and Provenance

The canonical replay does not flatten its layers into evidence-derived history. Three classifications are used and a fourth is deliberately absent:

- `caller_supplied_association` — S07 history-fact evidence links
- `caller_supplied_composition` — the S02 supplied change set
- `retained_normalized_observation` — S01 bindings, S02 changed paths, S03 approval, S04 merge outcome, S05 deletion, and S06 occurrence instants

`deterministic_derivation` is not present: `S1.P05` publishes no deterministic derivation, and the ahead, behind, and merge-base values the retained comparison carries remain deferred with `S1.P02` `deferred:22`.

Eleven history facts are individually linkable. `PullRequestChangeSet` is a published product fact and is replayed as a caller-supplied composition, but `S1.P05.S07` does not admit it as an evidence-link fact, and the replay preserves that asymmetry.

## 5. Rejection Contract

Invalid vectors lock `failure_category`, `error_location`, `error_location_mode`, `error_type`. Prose messages, Pydantic internal union branch labels, and validator function names are deliberately not locked. The `prefix` location mode is used only where a discriminatorless union reports per-branch locations: the `S1.P05.S06` occurrence union and the `S1.P05.S07` fact union.

## 6. Effective Governance

`S1.P05.S08` and its append-only `S1.P05.S08.C01` correction are consumed as source authorities and are never vectorized as product behaviour. The executor recomputes the effective projection from both artifacts rather than trusting a stored table:

    inherited 12 · exactly once 12 · self-introduced 0 · self_owned_open 0
    split 5 · carried_forward 7
    immediate S1.P06 1 · S2 6 · S5 5
    long-term S1.P06 1 · S5 11

## 7. Non-Generalizations

- no complete development-history graph
- no generic development event model
- no generic development-history relationship graph
- no ancestry, descendance, reachability, or branch containment
- no merge-base, ahead, or behind semantics
- no historical default-branch substitution from a current observation
- no rename or copy semantics
- no complete mutable-ref history
- no discussion completeness
- no edit or deletion absence claim
- no complete historical review state
- no causal order derived from timestamps
- no merge caused by approval
- no ref deletion caused by merge
- no CI, test, or repair correctness claim
- no FaultInstance or root-cause semantics
- no confidence, review state, or claim interpretation
- no field-level evidence locator
- no verification or support strength
- no evidence aggregation or supersession following
- no persistence, serialization registry, or production corpus reader
- no source ingestion, Git or GitHub I/O, or retrieval
- no generic repository or evolution graph owned by S1.P06

## 8. Locked Source Authorities

| Authority | Role | SHA-256 |
| --- | --- | --- |
| `decision:s1-p05-s08:disposition` | `governance_disposition_not_vectorized` | `8df7a989ef33fb5d6e70c8815d1b74748c8c2f98cfb7e581414548a403d65cfe` |
| `correction:s1-p05-s08-c01:owner-topology` | `append_only_owner_topology_correction` | `1ca0459edcc44951639c7b465f47eca43221d892a1621030267cb72fbcdd3bc3` |
| `closure:s1-p03:evidence-envelope` | `originating_development_history_model_reservation` | `21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b` |
| `acquisition:run-0001` | `retained_replay_evidence` | `1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318` |
| `correction:s04-c01-acquisition-closure` | `retained_additive_correction_evidence` | `44491ee512d2c2022110b83967fb6fa86d13045bc8404ea490d7a08b7aef24a2` |
