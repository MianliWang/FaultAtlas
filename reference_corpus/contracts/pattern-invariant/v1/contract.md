# P07 Pattern/Invariant Contract Corpus v1

Source-only synthetic constructor examples; JSON is authoritative. No retained-real replay or empirical generality is established.

## Fixed target snapshot

| Target | Owner |
| --- | --- |
| `FaultInvariantExpectedPropertyAssociation` | `faultatlas.domain.invariant_relationship` |
| `FaultInvariantIdentity` | `faultatlas.domain.invariant` |
| `FaultPatternComposition` | `faultatlas.domain.pattern_composition` |
| `FaultPatternExemplarAssociation` | `faultatlas.domain.pattern_exemplar` |
| `FaultPatternIdentity` | `faultatlas.domain.pattern` |
| `FaultPatternInvariantAssociation` | `faultatlas.domain.invariant_relationship` |
| `SuppliedFaultInvariant` | `faultatlas.domain.invariant` |
| `SuppliedFaultPattern` | `faultatlas.domain.pattern` |

## Executable vectors

| ID | Target | Operation / mode / recipe | Obligation |
| --- | --- | --- | --- |
| `valid.pattern_identity.python` | `FaultPatternIdentity` | validate / python / typed | pattern_identity |
| `valid.pattern_identity.json` | `FaultPatternIdentity` | validate / json / literal | pattern_identity |
| `valid.pattern.python` | `SuppliedFaultPattern` | validate / python / typed | pattern |
| `valid.pattern.json` | `SuppliedFaultPattern` | validate / json / literal | pattern |
| `valid.exemplar.python` | `FaultPatternExemplarAssociation` | validate / python / typed | exemplar |
| `valid.exemplar.json` | `FaultPatternExemplarAssociation` | validate / json / literal | exemplar |
| `valid.invariant_identity.python` | `FaultInvariantIdentity` | validate / python / typed | invariant_identity |
| `valid.invariant_identity.json` | `FaultInvariantIdentity` | validate / json / literal | invariant_identity |
| `valid.invariant.python` | `SuppliedFaultInvariant` | validate / python / typed | invariant |
| `valid.invariant.json` | `SuppliedFaultInvariant` | validate / json / literal | invariant |
| `valid.pattern_invariant.python` | `FaultPatternInvariantAssociation` | validate / python / typed | pattern_invariant |
| `valid.pattern_invariant.json` | `FaultPatternInvariantAssociation` | validate / json / literal | pattern_invariant |
| `valid.invariant_expected.python` | `FaultInvariantExpectedPropertyAssociation` | validate / python / typed | invariant_expected |
| `valid.invariant_expected.json` | `FaultInvariantExpectedPropertyAssociation` | validate / json / literal | invariant_expected |
| `valid.composition.python` | `FaultPatternComposition` | validate / python / typed | composition |
| `valid.composition.json` | `FaultPatternComposition` | validate / json / literal | composition |
| `invalid.pattern_identity.strict-root` | `FaultPatternIdentity` | reject / python / typed | pattern_identity |
| `invalid.pattern_identity.invalid-uuid` | `FaultPatternIdentity` | reject / json / literal | pattern_identity |
| `invalid.invariant_identity.strict-root` | `FaultInvariantIdentity` | reject / python / typed | invariant_identity |
| `invalid.invariant_identity.invalid-uuid` | `FaultInvariantIdentity` | reject / json / literal | invariant_identity |
| `invalid.pattern.typed-identity` | `SuppliedFaultPattern` | reject / python / typed | pattern |
| `invalid.pattern.padded-text` | `SuppliedFaultPattern` | reject / json / literal | pattern |
| `invalid.invariant.typed-identity` | `SuppliedFaultInvariant` | reject / python / typed | invariant |
| `invalid.invariant.padded-text` | `SuppliedFaultInvariant` | reject / json / literal | invariant |
| `invalid.exemplar.typed-pattern` | `FaultPatternExemplarAssociation` | reject / python / typed | exemplar |
| `invalid.exemplar.no-support-field` | `FaultPatternExemplarAssociation` | reject / json / literal | exemplar |
| `invalid.pattern_invariant.typed-pattern` | `FaultPatternInvariantAssociation` | reject / python / typed | pattern_invariant |
| `invalid.pattern_invariant.no-support-field` | `FaultPatternInvariantAssociation` | reject / json / literal | pattern_invariant |
| `invalid.invariant_expected.changed-property` | `FaultInvariantExpectedPropertyAssociation` | reject / python / typed | invariant_expected |
| `invalid.invariant_expected.other-case` | `FaultInvariantExpectedPropertyAssociation` | reject / json / literal | invariant_expected |
| `invalid.composition.strict-tuple` | `FaultPatternComposition` | reject / python / typed | composition |
| `invalid.composition.explicit-null` | `FaultPatternComposition` | reject / json / literal | composition |
| `invalid.composition.duplicate-invariant` | `FaultPatternComposition` | reject / python / typed | composition |
| `invalid.composition.orphan-invariant` | `FaultPatternComposition` | reject / json / literal | composition |
| `invalid.composition.changed-pattern` | `FaultPatternComposition` | reject / json / literal | composition |
| `invalid.composition.changed-invariant` | `FaultPatternComposition` | reject / python / typed | composition |
| `invalid.composition.changed-property` | `FaultPatternComposition` | reject / python / typed | composition |
| `invalid.composition.nested-owner` | `FaultPatternComposition` | reject / python / typed | owner_revalidation |
| `invalid.pattern.lone-surrogate-wire` | `SuppliedFaultPattern` | reject / json_wire / wire | pattern |
| `composition.full-native` | `FaultPatternComposition` | validate / json / literal | two_cases |
| `composition.explicit-independence` | `FaultPatternComposition` | validate / python / typed | relation_independence |
| `composition.repeated-order` | `FaultPatternComposition` | validate / python / typed | order_repetition |
| `composition.separate-roots` | `FaultPatternComposition` | compare / python / separate | separate_roots |
| `composition.order-value-inequality` | `FaultPatternComposition` | compare / python / separate | order_repetition |
| `composition.competing-claims` | `FaultPatternComposition` | validate / python / typed | competing_claims |
| `composition.no-global-case-registry` | `FaultPatternComposition` | validate / python / typed | no_global_registry |
| `composition.evidence-separate` | `FaultPatternComposition` | compare / python / evidence | evidence_separation |
| `composition.nominal-identities` | `FaultPatternIdentity` | compare / python / nominal | nominal_identity |

Counts: `{"accepted": 25, "files": {"composition-vectors": 9, "invalid-vectors": 23, "valid-vectors": 16}, "rejected": 23, "vectors": 48}`. Counts describe declared rows; execution results live in external validation receipts.

Input builders consume explicit declarations; expected primitives are separately authored, including defaults and tuple order. Actual model dumps are compared to those expectations, never used to generate them.
Every rejection validates a legal base first. Native JSON enters model_validate_json; escaped product wire preserves the lone-surrogate case without corrupting artifact UTF-8. Unknown dispatch metadata fails before model calls.

## Integrity

Each sha256sum-style sidecar locks its own JSON. The manifest locks the three vector JSON files; the focused test independently pins all four. This view has no self-digest or hash cycle.

- `composition-vectors.json`: `ed737148c3b182a1e27b4a35186ca525be557a05c132c29a13be3ed0c73e6b4d`, 100145 bytes.
- `invalid-vectors.json`: `d102e7ee656f2c2934eea630982d745d96c764c9594268ee40d1c71c99c8b2fa`, 9943 bytes.
- `valid-vectors.json`: `1063f1af440bcd1f569025153a3205d260e2ef98473a22e3cc9d0ec2ee13492c`, 24689 bytes.

## Preserved S07 authority

`reference_corpus/contracts/pattern-invariant/decisions/s07-deferred-subject-disposition-readiness/decision.json`: `8937e1a896d8d4a78f01ce82878d478318b853532f90d9b93192f22d976ae237`, 22947 bytes.
- `/subjects/0`: `deferred:04`, `bounded_model_implemented`; origin `reference_corpus/contracts/evidence-envelope/closures/s1-p03-phase-closure/closure.json#/deferred_register/entries/3`.
- `/subjects/1`: `gap:s05-known:cross-repository-pattern-and-transfer-not-established`, `unknown_carried_forward`; origin `reference_corpus/pytest-4412/closures/s1-p00-phase-closure/closure.json#/deferred_register/items/23`.
  `unknown_pending_additional_evidence`; owner `S1.P08`; revisit `before_S1.P08_makes_transfer_or_applicability_claims_and_only_after_additional_cross_repository_cases`. additional reviewed cross-repository cases
- `/subjects/2`: `deferred:p01:p07-pattern-generality`, `unknown_retained_with_original_owner`; origin `reference_corpus/contracts/identity/closures/s1-p01-phase-closure/closure.json#/deferred_register/items/37`.
  `evidence_insufficient`; owner `S1.P07`; revisit `before_S1_P07_operational_completion`. Evidence for p07 pattern generality is insufficient in the current single-case calibration.

## Reused focused owners

Collected baseline references, not execution-success claims or permanent test-source byte locks; matching run evidence is external.
- `V1`: `tests/test_fault_pattern_vertical.py::test_two_repository_composition_matches_authored_payload`
- `V2`: `tests/test_fault_pattern_vertical.py::test_exemplars_and_expectation_chains_are_explicit`
- `V3`: `tests/test_fault_pattern_vertical.py::test_wrong_case_property_fails_at_membership_owner[case_b_property]`
- `V4`: `tests/test_fault_pattern_vertical.py::test_repetition_order_and_separate_roots_remain_local`
- `V5`: `tests/test_fault_pattern_vertical.py::test_competing_claims_survive_composition`
- `V6`: `tests/test_fault_pattern_vertical.py::test_case_evidence_link_does_not_propagate`
- `V7`: `tests/test_fault_pattern_vertical.py::test_invalid_nested_child_revalidates_at_its_owner`
- `attachment`: `tests/test_fault_pattern_composition.py::test_root_attachment_and_repeated_explicit_relations[json]`
- `bounds`: `tests/test_fault_pattern_composition.py::test_collection_maximum[json-invariant_expected_property_associations]`
- `full_member`: `tests/test_fault_invariant_relationship.py::test_full_record_equal_member_qualifies_without_object_identity`
- `invariant_identity`: `tests/test_fault_invariant.py::test_uuid_policy_and_bare_json_round_trip[scalar0]`
- `invariant_text`: `tests/test_fault_invariant.py::test_invalid_text_is_refused_during_python_and_json_validation[ \t\n-value_error]`
- `invariant_uniqueness`: `tests/test_fault_pattern_composition.py::test_duplicate_invariant_identity_refused[False-json]`
- `json`: `tests/test_fault_pattern_composition.py::test_full_authored_wire_and_reentry[json]`
- `order`: `tests/test_fault_pattern_composition.py::test_order_is_preserved_and_changes_value_equality[exemplar_associations]`
- `package`: `tests/test_package.py::test_offline_build_excludes_reference_corpus_and_historical_license`
- `pattern_text`: `tests/test_fault_pattern.py::test_the_character_limit_is_inclusive_and_one_more_is_refused`
- `python_children`: `tests/test_fault_pattern_composition.py::test_python_children_are_typed[foreign-False-exemplar_associations]`
- `wheel`: `tests/test_fault_pattern_composition.py::test_installed_wheel_provenance_and_authored_json`

## Limits

- Supplied pattern/invariant claims are not truth, recurrence, applicability, confidence or repair correctness.
- Repeated associations and synthetic repositories are not independent observations.
- S08 does not resolve either empirical remainder, close P07, grant P08 eligibility or complete a whole-Phase planning audit.
- P01 deferred:p01:p07-pattern-generality remains for review before P07 operational completion.
- Canonical artifact bytes are a test convention, not P10 durable product interchange or a database schema.
- Only the fixed local recipes execute; retained source, scripts and fixture-supplied commands are never executed.

Publication: `{"completion_evidence": "external_Git_GitHub_and_task_receipt", "condition": "protected_squash_and_successful_natural_main_verification", "state": "sealed_publication_candidate"}`.
