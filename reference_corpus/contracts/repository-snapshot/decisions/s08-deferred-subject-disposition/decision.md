# Repository Snapshot Deferred-Subject Disposition

## 1. Scope and Authority Warning

This internal, case-calibrated `S1.P04.S08` decision is not a production schema, class, adapter, reader, writer, migration, persistence contract, or public API. `decision.json` is the sole durable semantic authority; this Markdown is derived. The Slice is governance-only: no production Python source changed and the production source count remains 11.

## 2. Exact `decision.json` SHA-256

`7b8c15365c52a235f3350fba884ad00dae14521a5ddd3272cf1dfa9fe044c5f4`

## 3. Result

`S1.P04` inherited 7 deferred subjects from `S1.P00`, `S1.P01`, `S1.P02`, and `S1.P03`. Each is dispositioned exactly once. 3 are addressed by published `S1.P04` Slices, 1 is split into an addressed portion and a carried-forward remainder, and the remainder plus 3 further subjects are carried forward to valid later owners.

    self_owned_open == 0

Nothing unsupported is claimed as implemented, no predecessor artifact is edited, no historical unknown is replaced by a current observation, and no placeholder production model is created.

## 4. Inherited Subjects and Dispositions

| # | Subject | Source | Pointer | Disposition |
| --- | --- | --- | --- | --- |
| 1 | repository snapshot aggregation (`deferred:p01:p04-repository-snapshot-aggregation`) | S1.P01_phase_closure | `/deferred_register/items/17` | addressed by `S1.P04.S04` |
| 2 | repository snapshot aggregation (`deferred:17`) | S1.P02_phase_closure | `/deferred_register/items/16` | addressed by `S1.P04.S04` |
| 3 | snapshot completeness (`deferred:18`) | S1.P02_phase_closure | `/deferred_register/items/17` | split: addressed by `S1.P04.S05`, `S1.P04.S06`; remainder `evidence_insufficient` to `S2` / `S5` |
| 4 | default-branch observation (`deferred:19`) | S1.P02_phase_closure | `/deferred_register/items/18` | `unsupported_current_scope` to `S1.P05` |
| 5 | repository membership aggregation (`deferred:20`) | S1.P02_phase_closure | `/deferred_register/items/19` | `evidence_insufficient` to `S2` / `S5` |
| 6 | repository snapshot model (`deferred:01`) | S1.P03_phase_closure | `/deferred_register/entries/0` | addressed by `S1.P04.S01`, `S1.P04.S02`, `S1.P04.S03`, `S1.P04.S04`, `S1.P04.S05`, `S1.P04.S06`, `S1.P04.S07` |
| 7 | historical default branch unknown (`gap:s05-known:historical-default-branch-unknown`) | S1.P00_phase_closure | `/deferred_register/items/5` | `unknown_pending_additional_evidence` to `S2` |

## 5. Per-Subject Rationale

### 5.1 repository snapshot aggregation — `deferred:p01:p04-repository-snapshot-aggregation`

Source: `reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json` at `/deferred_register/items/17`, SHA-256 `2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642`. Predecessor wording: "P04 repository snapshot aggregation is outside S1.P01 and remains owned by S1.P04.". Predecessor state: `provisional_design`. Predecessor immediate owner: `S1.P04`.

S1.P04.S04 published RepositorySnapshotPathBindingCollection, the bounded ordered aggregate of supplied path bindings over one snapshot subject, which is the aggregation subject this item reserved. Aggregation is not membership, completeness, or reachability, and this disposition claims none of them.

### 5.2 repository snapshot aggregation — `deferred:17`

Source: `reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json` at `/deferred_register/items/16`, SHA-256 `daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67`. Predecessor wording: "repository snapshot aggregation". Predecessor state: `provisional_design`. Predecessor immediate owner: `S1.P04`.

The same aggregation subject restated at S1.P02 closure. S1.P04.S04 published the bounded ordered collection; supplied order is preserved and carries no repository structural meaning.

### 5.3 snapshot completeness — `deferred:18`

Source: `reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json` at `/deferred_register/items/17`, SHA-256 `daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67`. Predecessor wording: "snapshot completeness". Predecessor state: `provisional_design`. Predecessor immediate owner: `S1.P04`.

The inherited subject is broader than what S1.P04 established. A bounded declared-scope portion is addressed; the whole-repository remainder is not, and is carried forward with a valid later owner rather than claimed.

**Addressed portion** — declared exact-path scope and scope-relative positive structural coverage of supplied bindings. S1.P04.S05 published RepositorySnapshotDeclaredPathScope, a caller-supplied exact-path denominator, and S1.P04.S06 published RepositorySnapshotDeclaredPathScopeCoverage, a positive-only witness that every exact declared path also appears as the exact path of a supplied binding. Both range only over caller-supplied values.

**Carried-forward remainder** — whole-repository snapshot completeness: `evidence_insufficient`, immediate owner `S2`, preserved long-term owner `S5`. Whole-repository snapshot completeness requires an authoritative enumeration of repository content, and the retained canonical acquisition records six non-recursive traversals carrying only logical_path, non_recursive, request_ordinal, requested_tree_sha, and truncated, and retains no tree-entry list for any of them. Acquiring and retaining recursive tree-entry manifests is source ingestion and normalization work owned by S2; the completeness semantics over that evidence are repository-graph semantics owned by S5. S1.P04.S05 and S1.P04.S06 did not implement this remainder and must not be read as having done so.

### 5.4 default-branch observation — `deferred:19`

Source: `reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json` at `/deferred_register/items/18`, SHA-256 `daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67`. Predecessor wording: "default-branch observation". Predecessor state: `provisional_design`. Predecessor immediate owner: `S1.P04`.

A default-branch designation is a mutable-ref fact that changes over time. S1.P04 snapshot identity is a stable RepositoryIdentity plus an immutable GitCommitIdentity, and mutable refs are explicitly not snapshot identity, so S1.P04.S01 through S1.P04.S07 required no default-branch designation and published none. Ref designation over time is development-history semantics owned by S1.P05, which S1.P02 already assigned the adjacent revision ref and path event history subject.

### 5.5 repository membership aggregation — `deferred:20`

Source: `reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json` at `/deferred_register/items/19`, SHA-256 `daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67`. Predecessor wording: "repository membership aggregation". Predecessor state: `provisional_design`. Predecessor immediate owner: `S1.P04`.

No repository membership claim exists in S1.P04. A supplied path binding, a bounded aggregate, a declared scope, a coverage witness, and an evidence association each explicitly disclaim membership, existence, and reachability. Membership requires an authoritative tree-entry enumeration and verified reachability from the S1.P04.S02 root tree, and the retained canonical acquisition records six non-recursive traversals carrying only logical_path, non_recursive, request_ordinal, requested_tree_sha, and truncated, and retains no tree-entry list for any of them. Acquisition and retention of that evidence is owned by S2; reachability and repository-graph semantics over it are owned by S5.

### 5.6 repository snapshot model — `deferred:01`

Source: `reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure/closure.json` at `/deferred_register/entries/0`, SHA-256 `21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b`. Predecessor wording: "repository_snapshot_model". Predecessor state: `not_implemented`. Predecessor immediate owner: `S1.P04`.

S1.P04.S01 through S1.P04.S07 published the repository snapshot model: immutable snapshot subject identity, root-tree binding, path-object binding, bounded binding collection, declared path scope, declared-scope coverage witness, and the snapshot-fact-to-evidence-record association bridge. The model this item reserved now exists, boundedly.

**Boundedness** — The published model is bounded. It performs no Git or filesystem I/O and claims no repository membership, path existence, root-tree reachability, snapshot or whole-repository completeness, known absence, prefix or tree-topology consistency, Git mode, symbolic-link or gitlink semantics, fact-level evidence location, confidence, review, or persistence. Evidence association is LEVEL 1 only.

### 5.7 historical default branch unknown — `gap:s05-known:historical-default-branch-unknown`

Source: `reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json` at `/deferred_register/items/5`, SHA-256 `8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e`. Predecessor wording: "Historical default branch unknown". Predecessor state: `unknown_pending_additional_evidence`. Predecessor immediate owner: `intentionally_unowned_until_more_evidence`.

The state is preserved exactly: the historical default branch remains unknown and is not fabricated. Only ownership moves. S1.P00 routed this item to S1.P04 conditionally, at the latest decision point before S1.P04 relies on historical default-branch identity and only after new evidence. S1.P04.S01 through S1.P04.S07 never relied on it: no production source references a default branch and no domain module exports a branch or default designation, so the condition never triggered. the retained canonical acquisition observes only the current default branch value at its own observation time and retains no historical default-branch evidence, and current provider retrieval could only re-observe current state. Acquiring separately authorized historical ref evidence, if it is ever obtainable, is source ingestion work owned by S2.

**Prohibited resolution** — The historical unknown must never be replaced with the repository's current default branch, and no current provider observation may be presented as historical fact.

## 6. Downstream Handoffs

- `S2` (`handoff:s1-p04-s08:s2`, `not_started`) receives: whole-repository snapshot completeness; repository membership aggregation; historical default branch unknown.
- `S5` (`handoff:s1-p04-s08:s5`, `not_started`) receives: whole-repository snapshot completeness; repository membership aggregation.
- `S1.P05` (`handoff:s1-p04-s08:s1-p05`, `not_started`) receives: default-branch observation.

## 7. Preserved Non-Generalizations

- no whole-repository snapshot completeness
- no verified repository membership
- no historical default-branch substitution
- no default-branch designation model in S1.P04
- no known absence
- no prefix, ancestry, or tree-topology semantics
- no Git mode, symbolic-link, or gitlink semantics
- S1.P04.S07 evidence association remains LEVEL 1 record-level only
- no fact-level evidence locator
- no persistence or durable serialization
- intentional evidence-gated deferral is not implementation failure

Intentional evidence-gated deferral is not implementation failure. `S1.P04.S09` will turn the appropriate product non-generalizations into contract vectors; `S1.P04.S10` will lock the final closure register.

## 8. Predecessor Integrity

This is redisposition, not correction. The `S1.P00`, `S1.P01`, `S1.P02`, and `S1.P03` closures were correct at publication and remain byte-identical; their original ownership and state statements remain historically true. This decision cites each inherited item by exact path, JSON pointer, and SHA-256 and restates its ownership under `S1.P04` disposition identifiers without editing a single predecessor byte.

## 9. Locked Source Artifacts

| Path | SHA-256 |
| --- | --- |
| `reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json` | `8c02d79c4a5a1d52b9fc2a3718e1b47888da6195588e62ab927388dbe972189e` |
| `reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json` | `2c1bfb9d3d596711066796ef83999d49b6846e65315a301eead7fa8fb5ac4642` |
| `reference_corpus/contracts/revision-locator/closures/s1-p02-phase-closure/closure.json` | `daf3a89ef22bf20652d91cc96f476f1f31584ec90d860e57d1641c3ec6ab5a67` |
| `reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure/closure.json` | `21a24e7ab572456f22d3aca572e10e76be69529770b96a131f3d4f624d0b481b` |
| `reference_corpus/pytest-4412/case/case.json` | `fc1439a8f9766bdf55b95e9d63f3bf19db44da1724dfb7cd2e889771384b9efa` |
| `reference_corpus/pytest-4412/analysis/s06-current-contract-gap-matrix/gap-matrix.json` | `55dacf5193aedc5493ac369dd0e3fb74a0f59f0c1f88bab1b625a2e4f4ff5f13` |
| `reference_corpus/pytest-4412/decisions/s07-identity-revision-provenance/decision.json` | `60ecb66565525cb21a924508794635072ae50e935d4791d9d91da5b6399ce866` |
| `reference_corpus/pytest-4412/acquisitions/run-0001-s04-v1-base-4c9cde74-head-690a63b9/acquisition.json` | `1c29093bf1537e9b824a18df1848b71a8da014f544bc9f385707eb0e000a1318` |

