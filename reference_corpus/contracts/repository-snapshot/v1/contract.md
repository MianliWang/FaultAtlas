# Repository Snapshot Contract Corpus

## 1. Scope and Authority Warning

This internal, source-repository-only `S1.P04.S09` corpus is not a production schema, reader, writer, validator, migration, persistence contract, or public API. The JSON files are the durable authorities; this Markdown is derived and is never an independent semantic authority. The Slice adds no product semantics and changes no production Python source.

## 2. Corpus Digests

| File | SHA-256 |
| --- | --- |
| `manifest.json` | `60381766870b84db296f1c1f224a0938a66f69fba2e35b7eeeaac862eb1a3827` |
| `valid-vectors.json` | `f26cc45cf2b5a13ee099dbda8f890743fe233ca7db3c855a4547784a405ea56f` |
| `invalid-vectors.json` | `e5179a1a424057a62a04e3321f6f4330cc8cb2f46f32609863579e5fcab624f0` |
| `replay-vectors.json` | `a1bf07b1be323b18ce0d16c0aba2963331eab4ba4c4659e38275cf5951146095` |

`contract.md` carries no sidecar, matching the published identity, revision-locator, and evidence-envelope corpora.

## 3. Owned Production Modules

- `faultatlas.domain.snapshot`
- `faultatlas.domain.snapshot_evidence_link`

Dependency authorities used as inputs but **not** owned by `S1.P04`:

- `faultatlas.domain.evidence`
- `faultatlas.domain.identity`
- `faultatlas.domain.revision`

`DurableEvidenceRecordReference`, `RepositoryIdentity`, `GitCommitIdentity`, `GitTreeIdentity`, `GitBlobIdentity`, and `GitRepositoryPath` are support targets. They are never `S1.P04` product symbols.

## 4. The Seven Owned Model Contracts

| Slice | Symbol | Fields | Contract |
| --- | --- | --- | --- |
| `S01` | `RepositorySnapshotIdentity` | `repository`, `revision` | Stable repository plus one immutable commit. Mutable refs are not identity. |
| `S02` | `RepositorySnapshotRootTreeBinding` | `snapshot`, `root_tree` | Supplied root tree whose algorithm must match the revision algorithm. Evidence-neutral. |
| `S03` | `RepositorySnapshotPathBinding` | `snapshot`, `path`, `git_object` | One exact path bound to one blob or tree, discriminated on `kind`. Commit-at-path fails closed. |
| `S04` | `RepositorySnapshotPathBindingCollection` | `snapshot`, `bindings` | Bounded ordered aggregate, at most 4096, shared subject, no repeated path. Empty is valid. |
| `S05` | `RepositorySnapshotDeclaredPathScope` | `snapshot`, `declared_paths` | Bounded ordered exact-path denominator, at most 4096, no repeated path. Empty is valid. |
| `S06` | `RepositorySnapshotDeclaredPathScopeCoverage` | `scope`, `collection` | Positive-only witness over a non-empty scope; validity is order-insensitive. |
| `S07` | `RepositorySnapshotFactEvidenceLink` | `fact`, `evidence_record` | LEVEL-1 association of one S02 or S03 fact with one durable record. |

All seven share `frozen`, `extra=forbid`, `strict`, `revalidate_instances=always`, and `validate_default`.

## 5. Vector Inventory

- valid: **50**
- invalid: **68**
- replay: **26**
- total: **144**
- fixtures: **16**

Every vector declares a `semantic_partition`, and the partitions are unique across the corpus, so no vector is a re-parameterization of another.

## 6. Replay Provenance

Replay is chained rather than flattened. Each vector declares the provenance of its own layer, and the corpus never claims an evidence-derived repository snapshot:

| Classification | Layers |
| --- | --- |
| `caller_supplied_association` | S07 evidence associations |
| `caller_supplied_selection` | S04 aggregates and S05 declared scopes |
| `deterministic_derivation` | S06 coverage witnesses |
| `retained_normalized_observation` | S01 subject and S02/S03 facts |

The retained canonical acquisition holds 4 normalized leaves and 6 non-recursive traversals, and no tree-entry manifest. Replay therefore reconstructs the published supplied values only. It asserts no whole-repository enumeration, no verified membership, and no root-tree reachability. These classifications are corpus and test metadata; they create no production vocabulary.

## 7. Error-Oracle Policy

Rejection vectors lock `failure_category`, `error_location`, `error_location_mode`, and `error_type`. Full error prose is never locked. Where a discriminatorless union reports one error per branch, the location is matched as a stable prefix, so pydantic-internal branch labels are not frozen as contract.

## 8. Non-Generalizations

- `a_supplied_path_binding_is_not_repository_membership`
- `a_binding_collection_is_not_repository_membership`
- `a_declared_path_scope_is_not_path_existence`
- `a_coverage_witness_is_not_snapshot_completeness`
- `a_coverage_witness_is_not_whole_repository_completeness`
- `an_uncovered_declared_path_is_not_absent_missing_unknown_or_unavailable`
- `an_undeclared_path_is_not_absent`
- `no_whole_repository_enumeration_or_completeness`
- `no_verified_repository_membership`
- `no_root_tree_reachability_verification`
- `no_known_absence`
- `no_prefix_ancestry_or_tree_topology_semantics`
- `no_git_mode_executable_symlink_or_gitlink_semantics`
- `no_default_branch_designation`
- `no_historical_default_branch_substitution`
- `S07_evidence_association_is_LEVEL_1_record_level_only`
- `no_fact_level_evidence_locator_or_json_pointer`
- `no_support_role_strength_verification_confidence_or_review`
- `no_persistence_serialization_readers_writers_or_migration`
- `no_production_corpus_reader_or_capability`
- `corpus_replay_classifications_are_test_metadata_not_production_vocabulary`

## 9. Governance Authority

`S1.P04.S08` is governance authority and is referenced through `source_decisions`; it is never vectorized as product behavior. It supplies the disposition of all seven inherited subjects, the preservation of the historical default branch as unknown, the absence of any default-branch designation in `S1.P04`, and the transfer of whole-repository completeness and repository membership.

| Authority | SHA-256 |
| --- | --- |
| `reference_corpus/contracts/repository-snapshot/decisions/s08-deferred-subject-disposition/decision.json` | `7361582b749eeb986319b0cce87155671b3b25904346be06e6004fb0e53ac1da` |
| `reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure/closure.json` | `21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b` |
| `reference_corpus/pytest-4412/acquisitions/run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json` | `1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318` |

## 10. Package Exclusion

The corpus is source-repository-only and is excluded from both the wheel and the sdist. It provides no production reader, writer, validator, or other runtime capability, and its executor is the tracked test module `tests/test_repository_snapshot_contract_corpus.py`.

