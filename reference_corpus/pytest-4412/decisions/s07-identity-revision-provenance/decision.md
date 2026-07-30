# pytest #4412 Identity, Revision, and Provenance Decision

## 1. Scope and Authority Warning

This is the internal, case-calibrated S1.P00.S07 decision view. Canonical `decision.json` is the sole durable semantic authority, and `decision.md` is derived. It is not a production schema, class, wire format, loader, migration, persistence contract, or public API.

## 2. Exact Primary JSON SHA-256

Canonical `decision.json` SHA-256: `60ecb66565525cb21a924508794635072ae50e935d4791d9d91da5b6399ce866`.

## 3. Executive Decision Summary

S07 locks eleven case-calibrated product decisions, covers five S06-routed owner decisions, and records dispositions for seven immediate-S07 gaps while leaving production implementation to later owners.

## 4. Provider and Authority Model

- Provider key: `github`.
- Navigation authority: `github.com`.
- Retrieval authority: `api.github.com`.
- Separation rule: `provider_key_navigation_authority_retrieval_authority_api_version_media_and_HTTP_controls_are_distinct`.
- Canonical navigation references are authority-derived and are not direct provider fields.

## 5. Stable Repository Identity and Alias Rules

Stable case identity is provider `github` plus repository ID `37489525`. `pytest-dev/pytest` is a mutable alias observed under `api.github.com` at `2026-07-24T11:03:15.996744Z`.

The original deleted head repository remains `unknown`; it is not inferred from head label, ref, login, target repository, reachability, or current alias.

## 6. Typed Source-Object Identity Rules

| Kind | Identity components | Parent linkage |
|---|---|---|
| `repository` | `provider`, `provider_stable_repository_ID` | `none` |
| `issue` | `provider`, `stable_repository_identity`, `object_kind_issue`, `repository_scoped_number` | `stable_repository_identity` |
| `pull_request` | `provider`, `stable_repository_identity`, `object_kind_pull_request`, `repository_scoped_number` | `stable_repository_identity` |
| `issue_comment` | `provider`, `object_kind_issue_comment`, `provider_global_stable_ID` | `stable_repository_and_parent_issue_identity` |
| `pull_request_comment` | `provider`, `object_kind_pull_request_comment`, `provider_global_stable_ID` | `stable_repository_and_parent_pull_request_identity` |
| `pull_request_review` | `provider`, `object_kind_pull_request_review`, `provider_global_stable_ID` | `stable_repository_parent_pull_request_and_reviewed_revision` |
| `timeline_event` | `provider`, `object_kind_timeline_event`, `provider_assigned_stable_event_ID_when_present` | `stable_repository_and_parent_source_object` |
| `actor_or_reviewer_attribution` | `provider`, `provider_user_ID_when_observed`, `explicit_field_state` | `attributed_source_object_or_event` |

Repository-scoped numbers, REST global IDs, and GraphQL node IDs remain distinct typed roles. Source indexes and mutable logins are not stable object identity.

## 7. Git Objects, Revision Roles, and Ref Observations

Git identity requires object kind, hash algorithm, and full digest. Commits, trees, and blobs remain distinct; base, head, merge-first-parent, and merge are roles over commit identities.

Merge parent order is preserved. A mutable ref is an observation rather than revision identity, and deleting a ref does not invalidate its immutable target commit.

## 8. Locator Boundary

A revision-qualified path contains:

- `stable_repository_identity`
- `immutable_revision_identity`
- `exact_repository_relative_path`
- `path_representation_rules`

Line, byte, and diff-hunk coordinates belong to a separate S1.P02 contract. They require explicit conventions, parent binding, encoding/line-ending assumptions, diff-side separation, and reviewed applicability.

## 9. Field-State Vocabulary

| State | Meaning | Canonical-case witness |
|---|---|---|
| `present` | The inspected representation contains a usable value. | direct: The retained Issue observation contains a usable GraphQL node ID. |
| `observed_null` | The inspected representation explicitly contains null. | direct: Issue timeline source index 17 explicitly reports a null actor field in the supplemental observation. |
| `missing` | The inspected representation does not contain the field. | direct: The pre-merge PR representation omits merge_commit_sha and records that field as missing. |
| `unavailable` | The object or representation is known, but no representation was obtained. | direct: The deleted PR-head repository is known as a subject, but no repository representation was obtained. |
| `inaccessible` | Access was denied or required authorization that was unavailable. | not observed; bounded negative example: No access denial was observed; private and permission-hidden records remain unknown and must not be relabeled inaccessible. |
| `deleted` | Explicit provider evidence reports deletion or a tombstone. | direct: The provider timeline contains an explicit PR-head-ref deletion lifecycle event. |
| `unknown` | Available evidence cannot establish the value or state. | direct: The original repository identity behind the deleted PR head ref cannot be established. |
| `unsupported` | The current contract or provider surface intentionally cannot represent or support the concept. | direct: The single case does not support a universal transfer conclusion. |
| `conflict` | Two or more evidence-bearing observations disagree and no accepted resolution exists. | not observed; bounded negative example: No unresolved conflict is present: recorded base and merge first parent differ because they have distinct roles and were reconciled explicitly. |

## 10. Provenance-Layer Separation

| Ordinal | Layer | Subject | Downstream owner(s) |
|---:|---|---|---|
| 1 | `provenance-layer:01-source-authority` | Source provider and named navigation or retrieval authorities | `S1.P01` |
| 2 | `provenance-layer:02-repository-identity` | Stable repository identity | `S1.P01` |
| 3 | `provenance-layer:03-source-object-identity` | Repository, Issue, PR, comment, review, timeline, and attribution objects | `S1.P01` |
| 4 | `provenance-layer:04-immutable-revision-or-artifact` | Git object or immutable exact artifact identity | `S1.P02`, `S1.P03` |
| 5 | `provenance-layer:05-mutable-ref-or-alias-observation` | Repository alias or mutable Git ref at one observation | `S1.P01`, `S1.P02` |
| 6 | `provenance-layer:06-retrieval-request` | One bounded request attempt | `S1.P03` |
| 7 | `provenance-layer:07-response-representation-observation` | Response metadata and the observed representation | `S1.P03` |
| 8 | `provenance-layer:08-acquisition-run` | Governed acquisition run | `S1.P03` |
| 9 | `provenance-layer:09-retained-artifact` | Exact bytes retained by FaultAtlas | `S1.P03` |
| 10 | `provenance-layer:10-transformation` | Derivation from one representation or artifact to another | `S1.P03` |
| 11 | `provenance-layer:11-correction-or-supersession` | Semantic correction or supersession of a specific durable record | `S1.P03`, `S1.P10` |
| 12 | `provenance-layer:12-case-manifest-relationship` | Case entity and relationship assertions over locked evidence | `S1.P05`, `S1.P10` |
| 13 | `provenance-layer:13-reviewed-interpretation` | Reviewed selection, technical role, invariant, or other interpretation | `S1.P09` |
| 14 | `provenance-layer:14-faultatlas-publication` | Publication of a FaultAtlas artifact | `S1.P10` |

The layers never overwrite one another. Acquisition time is not provider event time; supplemental observations are not backdated; normalized data is not raw; corrections and interpretations preserve their inputs.

## 11. Legacy `SourceLocator` Disposition

`SourceLocator` remains internal, provisional, unchanged, legacy, and GitHub-Issue-only. Its `repository` is a mutable alias and its `object_id` remains `unresolved_legacy_ambiguity_between_repository_scoped_number_and_global_provider_ID`.

No new consumer may depend on the ambiguous `object_id`; future work must map it explicitly or preserve the legacy seed beside typed contracts.

## 12. S08 Boundary

`ArtifactSnapshot` is not a stable source-identity carrier. Snapshot identity differs from source identity, and exact diff/LICENSE bytes do not fit its current Issue-bound UTF-8 JSON-text behavior. S08 retains all preserve, evolve, and replace/adapter options; none is selected here.

## 13. Locked, Provisional, and Unknown Summary

- Locked decision items: `11`.
- Provisional items: `23`.
- Unknown items: `4`.
- Later owner decisions still required: `6`.

## 14. S1.P01-S1.P03 Handoff

- `S1.P01`: provider authority abstraction; stable repository identity; typed source object identity; time qualified alias observations; explicit identity state carriers; legacy SourceLocator compatibility mapping.
- `S1.P02`: algorithm qualified Git object identity; revision roles; ordered merge parents; mutable ref observations; revision qualified paths; line byte and diff hunk locators.
- `S1.P03`: request response observation and acquisition provenance; representation and retained artifact split; transformation and correction records; omission and completeness boundary; publication provenance.

## 15. No Production Model Change

No production model, export, CLI, dependency, lockfile, CI configuration, or public API changed. No S08 or S1.P01-S1.P03 implementation began.

## 16. Not a Universal Schema

This record is calibrated only to GitHub, Git, pytest #4412, and current FaultAtlas requirements. It does not claim validated private GitHub, GitHub Enterprise, non-Git VCS, other-provider, alternate-ID-system, or arbitrary-history support.
