# pytest #4412 Current-Contract Gap Matrix

## Scope and Authority Warning

This is the derived, case-specific S1.P00.S06 analytical view. The canonical JSON is the sole durable semantic authority. This Markdown is not a production schema, loader, migration contract, public API, or universal multi-provider model.

## Primary Artifact Lock

Canonical `gap-matrix.json` SHA-256: `55dacf5193aedc5493ac369dd0e3fb74a0f59f0c1f88bab1b625a2e4f4ff5f13`.

## Current-Contract Executive Summary

The matrix covers exactly 33 S05 entities, 53 S05 relationships, and 81 required concept rows. Current models remain provisional and internal. They represent no relationship semantics, and S07/S08 owner decisions remain unresolved.

## Support-Status Totals

| Support status | Count |
|---|---:|
| `intentionally_deferred` | 16 |
| `not_representable` | 122 |
| `partially_representable` | 17 |
| `representable` | 2 |
| `unsupported_by_current_evidence` | 10 |

## SourceLocator Capability and Limitations

Purpose: `logical_identity_for_one_supported_external_source_object`.

Known ambiguity: `object_id_does_not_distinguish_repository_scoped_issue_number_from_global_rest_id`.

It accepts only `provider=github`, a normalized repository alias, `object_kind=issue`, and one positive decimal-string `object_id`. It does not represent stable repository identity, PRs, comments, reviews, revisions, ranges, artifacts, or relationships.

## ArtifactSnapshot Capability and Limitations

Purpose: `immutable_json_text_retrieval_for_a_github_issue_locator`.

Known ambiguity: `media_type_claim_is_fixed_but_payload_text_is_not_parsed_as_json_and_limitation_reasons_are_free_text`.

It supports one Issue-bound UTF-8 `application/json` text retrieval, UTC observation time, SHA-256 of the exact UTF-8 text, and explicit limitation fields. It does not represent arbitrary diff/LICENSE bytes, request envelopes, digest scopes, transformations, provenance, or relationships.

## Highest-Impact S07 Decision Blockers

- `gap:s05-known:source-locator-byte-range-ambiguity` — SourceLocator byte-range ambiguity
- `gap:s05-known:source-locator-discussion-surface-gap` — SourceLocator discussion-surface gap

## Highest-Impact S08 Decision Blockers

- `gap:s05-known:artifact-snapshot-media-and-envelope-gap` — ArtifactSnapshot media and envelope gap
- `gap:s05-known:current-internal-models-cannot-represent-full-case` — Current internal models cannot represent full case

## S09 Deterministic Test Obligations

- `gap:s06:s09-test-only-corpus-reader-validator` — Test-only corpus reader and validator obligation
- `gap:s06:s09-exact-replay-tests` — Exact coverage, pointer, canonical, and sidecar replay tests
- `gap:s06:s09-package-exclusion-regression` — Reference-corpus package exclusion regression proof

## S10 Closure Obligations

- `gap:s05-known:sealed-candidate-nonconformance-recorded-not-erased` — Sealed-candidate nonconformance remains recorded
- `gap:s06:s10-closure-consistency` — P00 closure consistency obligation
- `gap:s06:s10-append-only-topology-closure` — Append-only evidence topology closure

## Phase-Ownership Summary

| Immediate owner | Count |
|---|---:|
| `S1.P00.S07` | 7 |
| `S1.P00.S08` | 5 |
| `S1.P00.S09` | 3 |
| `S1.P00.S10` | 3 |
| `intentionally_unowned_until_more_evidence` | 9 |
| `later_s1_phase` | 4 |

## Safe Pull-Forward Summary

- `pull:s07:identity-vocabulary`: `S1.P01` → `S1.P00.S07`; implementation excluded: `production_identity_classes_and_public_exports`.
- `pull:s07:revision-vocabulary`: `S1.P02` → `S1.P00.S07`; implementation excluded: `revision_classes_resolvers_or_graphs`.
- `pull:s08:compatibility-requirements`: `S1.P03` → `S1.P00.S08`; implementation excluded: `Evidence_Envelope_or_ArtifactSnapshot_changes`.
- `pull:s08:migration-requirements`: `S1.P10` → `S1.P00.S08`; implementation excluded: `migration_code_dispatchers_or_persistence`.
- `pull:s09:canonical-tests`: `S1.P10` → `S1.P00.S09`; implementation excluded: `production_serializer_or_loader`.
- `pull:s09:integrity-tests`: `S1.P06` → `S1.P00.S09`; implementation excluded: `generic_schema_framework`.
- `pull:s09:package-exclusion`: `S1.P10` → `S1.P00.S09`; implementation excluded: `packaging_redesign`.
- `pull:s10:closure-evidence`: `S1.P10` → `S1.P00.S10`; implementation excluded: `production_contract_implementation`.

## Product-Owner Decision Summary

- `decision:s07:canonical-identity-tuple` — How should provider, stable repository identity, timed aliases, object kind, repository-scoped numbers, global REST IDs, and GraphQL node IDs compose without ambiguity? Recommended default: `typed_separate_identity_components`; state: `owner_decision_required`.
- `decision:s07:actor-reviewer-missing-states` — How should actor and reviewer identities distinguish observed values, observed null, omitted, unavailable, inaccessible, and unknown? Recommended default: `typed_attribution_with_explicit_field_state`; state: `owner_decision_required`.
- `decision:s07:revision-identity` — How should commits, trees, blobs, comparison endpoints, and their hash algorithms be explicitly identified? Recommended default: `kind_specific_revision_identifiers_with_explicit_algorithm`; state: `owner_decision_required`.
- `decision:s07:topology-ref-and-locator` — How should ordered parents, distinct base and first-parent roles, mutable or deleted refs, revision-qualified paths, and line, byte, and hunk ranges compose? Recommended default: `composable_typed_topology_ref_and_locator_components`; state: `owner_decision_required`.
- `decision:s07:provenance-authority-chain` — How should navigation authority, retrieval API authority, request provenance, URL construction provenance, observation time, and publication provenance compose? Recommended default: `typed_authority_and_provenance_records`; state: `owner_decision_required`.
- `decision:s08:artifact-snapshot-boundary` — Should ArtifactSnapshot v1 remain unchanged behind an outer evidence envelope, evolve through an explicit version, or be replaced with an adapter? Recommended default: `retain_v1_and_add_outer_envelope`; state: `owner_decision_required`.
- `decision:s08:representation-media-and-digest` — How should semantic normalized values, exact source bytes, requested and observed media, transformations, and algorithm-qualified digest scope be separated? Recommended default: `outer_evidence_envelope_with_explicit_representation_records`; state: `owner_decision_required`.
- `decision:s08:completeness-and-omission-carrier` — How should pagination, intentional omission, unavailable, deleted, inaccessible, observed null, current-visible limits, and unknown history be preserved? Recommended default: `versioned_envelope_level_limitation_and_omission_records`; state: `owner_decision_required`.
- `decision:s08:reader-writer-migration-compatibility` — What semantic reader, canonical writer, version dispatch, migration, backward-compatibility, supersession, and append-only correction policy applies? Recommended default: `freeze_v1_and_add_explicit_outer_adapters`; state: `owner_decision_required`.
- `decision:s09:test-verifier-scope` — Which corpus checks belong in a bounded test-only verifier, and which production reader, loader, or migration behaviors remain explicitly out of scope? Recommended default: `test_only_literal_corpus_verifier`; state: `owner_decision_required`.
- `decision:s10:p00-closure-criteria` — What exact evidence proves P00 closure across decisions, deterministic tests, source locks, append-only topology, package exclusion, docs, publication, and clean synchronization? Recommended default: `bounded_static_audit_with_exact_locked_inputs`; state: `owner_decision_required`.

## Explicit Boundaries

- `prohibited:modify-current-models` — modify SourceLocator or ArtifactSnapshot.
- `prohibited:add-identity-types` — add production identity or revision classes in S07 preparation.
- `prohibited:evidence-envelope` — implement an Evidence Envelope in S08 preparation.
- `prohibited:universal-schema` — turn the case or matrix format into a universal production schema.
- `prohibited:persistence-vendor` — choose database persistence graph vector or model vendor.
- `prohibited:ingestion-retrieval` — add ingestion retrieval embeddings synthesis or RAG.
- `prohibited:provider-acquisition` — reacquire pytest provider evidence.
- `prohibited:s07-start` — begin S1.P00.S07 implementation.
- `prohibited:tracked-broad-tests` — add comprehensive corpus tests during S06.

No current production model, package export, CLI behavior, dependency, CI configuration, or public API was changed. S07 implementation was not started. This matrix is not a universal production schema.
