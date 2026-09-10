from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tarfile
import uuid
import zipfile
from pathlib import Path
from typing import Any, Literal

import pytest
from pydantic import BaseModel, ConfigDict, RootModel, ValidationError

import faultatlas.domain.fault as fault_module
from faultatlas.domain.fault import FaultInstanceIdentity, FaultRepositoryContext
from faultatlas.domain.identity import (
    NumberedSourceObjectIdentity,
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
    RepositoryScopedNumber,
    SourceObjectKind,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FAULT_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/fault.py"
CHECKOUT_SOURCE_ROOT = REPOSITORY_ROOT / "src"

# The retained pytest #4412 case supplies a repository identity and no fault
# instance identifier at all, so every UUID below is a fixed synthetic value
# supplied by this oracle. Pairing one with the retained repository is a
# supplied demonstration, never an observed Issue-to-Fault mapping.
RETAINED_PROVIDER = "github"
RETAINED_REPOSITORY_ID = "37489525"
OTHER_REPOSITORY_ID = "37489526"
RETAINED_PULL_REQUEST_NUMBER = "4414"

SUPPLIED_FAULT_TEXT = "12345678-1234-4234-8234-123456789abc"
SUPPLIED_FAULT = uuid.UUID(SUPPLIED_FAULT_TEXT)
SECOND_FAULT_TEXT = "abcdef01-2345-4678-89ab-cdef01234567"
SECOND_FAULT = uuid.UUID(SECOND_FAULT_TEXT)
NIL_FAULT = uuid.UUID("00000000-0000-0000-0000-000000000000")
MAX_FAULT = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

# Fixed lexemes covering several UUID generation versions plus the two special
# values. None is generated during the test run and none carries an ordering,
# time, or generation-version promise in this contract.
ADMITTED_UUID_TEXT: tuple[tuple[str, int | None], ...] = (
    ("c232ab00-9414-11ec-b3c8-9e6bdeced846", 1),
    ("6fa459ea-ee8a-3ca4-894e-db77e160355e", 3),
    (SUPPLIED_FAULT_TEXT, 4),
    ("886313e1-3b8a-5372-9b90-0c9aee199e5d", 5),
    ("018f2c9e-1a2b-7c3d-8e4f-5a6b7c8d9e0f", 7),
    ("00000000-0000-8000-8000-00000000002a", 8),
    ("00000000-0000-0000-0000-000000000000", None),
    ("ffffffff-ffff-ffff-ffff-ffffffffffff", None),
)

# The module's CURRENT surface. S01 published the first two; S02 extended the
# same module in place with the next two, and S03 with the last four. Per-model
# S01 tests are unchanged.
EXPECTED_EXPORTS = [
    "FaultInstanceIdentity",
    "FaultRepositoryContext",
    "FaultReportIdentity",
    "SuppliedFaultReport",
    "FaultScenarioIdentity",
    "FaultOccurrenceIdentity",
    "SuppliedFaultScenario",
    "SuppliedFaultOccurrenceContext",
]

FORBIDDEN_IMPORTS = frozenset(
    {
        "datetime",
        "hashlib",
        "http",
        "io",
        "json",
        "os",
        "pathlib",
        "random",
        "re",
        "requests",
        "secrets",
        "socket",
        "subprocess",
        "sys",
        "time",
        "urllib",
    }
)
FORBIDDEN_UUID_CALLS = frozenset(
    {"getnode", "uuid1", "uuid3", "uuid4", "uuid5", "uuid6", "uuid7", "uuid8"}
)


# --- helpers -----------------------------------------------------------------


def _repository(
    repository_id: str = RETAINED_REPOSITORY_ID,
) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=ProviderKey(RETAINED_PROVIDER),
        provider_repository_id=ProviderRepositoryId(repository_id),
    )


def _repository_payload(
    repository_id: str = RETAINED_REPOSITORY_ID,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "provider": RETAINED_PROVIDER,
        "provider_repository_id": repository_id,
    }


def _identity(value: uuid.UUID = SUPPLIED_FAULT) -> FaultInstanceIdentity:
    return FaultInstanceIdentity(value)


def _context(
    fault: uuid.UUID = SUPPLIED_FAULT,
    repository_id: str = RETAINED_REPOSITORY_ID,
) -> FaultRepositoryContext:
    return FaultRepositoryContext(
        fault=_identity(fault),
        repository=_repository(repository_id),
    )


def _context_payload(
    fault_text: str = SUPPLIED_FAULT_TEXT,
    repository_id: str = RETAINED_REPOSITORY_ID,
) -> dict[str, Any]:
    return {"fault": fault_text, "repository": _repository_payload(repository_id)}


def _failures(error: ValidationError) -> tuple[tuple[tuple[int | str, ...], str], ...]:
    return tuple((detail["loc"], detail["type"]) for detail in error.errors())


def _distinct_value_count(*values: object) -> int:
    return len(set(values))


def _fault_source_tree() -> ast.Module:
    return ast.parse(FAULT_SOURCE.read_bytes(), filename=FAULT_SOURCE.name)


# --- foreign and lookalike carriers ------------------------------------------


class ForeignUuidRoot(RootModel[uuid.UUID]):
    """A different published-shaped model over the same scalar content."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class ForeignRepositoryIdentity(BaseModel):
    """A structurally identical model that is not the predecessor type."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    schema_version: Literal[1] = 1
    provider: ProviderKey
    provider_repository_id: ProviderRepositoryId


class FaultIdentityLookalike:
    """An attribute-backed carrier of a fault identity's only field."""

    def __init__(self, root: uuid.UUID) -> None:
        self.root = root


class RepositoryIdentityLookalike:
    """An attribute-backed carrier of the predecessor's fields."""

    def __init__(self, provider: ProviderKey, identifier: ProviderRepositoryId) -> None:
        self.schema_version = 1
        self.provider = provider
        self.provider_repository_id = identifier


class UnextendedFaultInstanceIdentity(FaultInstanceIdentity):
    """An ordinary subclass that adds no field."""


class UnextendedRepositoryIdentity(RepositoryIdentity):
    """An ordinary predecessor subclass that adds no field."""


class ExtendedRepositoryIdentity(RepositoryIdentity):
    """A predecessor subclass that adds a field the base schema forbids."""

    note: str = "supplied"


# --- scalar identity construction and the declared strict profile ------------


def test_identity_accepts_a_supplied_uuid_through_every_normal_entry_path() -> None:
    positional = FaultInstanceIdentity(SUPPLIED_FAULT)
    keyword = FaultInstanceIdentity(root=SUPPLIED_FAULT)
    validated = FaultInstanceIdentity.model_validate(SUPPLIED_FAULT)
    from_json = FaultInstanceIdentity.model_validate_json(
        json.dumps(SUPPLIED_FAULT_TEXT)
    )

    assert positional.root == SUPPLIED_FAULT
    assert positional == keyword == validated == from_json


def test_identity_revalidates_an_existing_identity_through_model_validate() -> None:
    supplied = _identity()

    revalidated = FaultInstanceIdentity.model_validate(supplied)

    assert revalidated == supplied
    assert revalidated.root == SUPPLIED_FAULT


def test_the_identity_constructor_is_not_an_instance_copy_api() -> None:
    supplied = _identity()

    with pytest.raises(ValidationError) as positional:
        FaultInstanceIdentity(supplied)  # pyright: ignore[reportArgumentType]
    with pytest.raises(ValidationError) as keyword:
        FaultInstanceIdentity(root=supplied)  # pyright: ignore[reportArgumentType]

    assert _failures(positional.value) == (((), "is_instance_of"),)
    assert _failures(keyword.value) == (((), "is_instance_of"),)


@pytest.mark.parametrize(
    "supplied",
    (
        SUPPLIED_FAULT_TEXT,
        SUPPLIED_FAULT_TEXT.upper(),
        f"urn:uuid:{SUPPLIED_FAULT_TEXT}",
        SUPPLIED_FAULT.hex,
    ),
)
def test_python_validation_of_uuid_text_is_refused_under_the_strict_profile(
    supplied: str,
) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultInstanceIdentity.model_validate(supplied)

    assert _failures(failure.value) == (((), "is_instance_of"),)


@pytest.mark.parametrize(
    "supplied",
    (
        SUPPLIED_FAULT.bytes,
        SUPPLIED_FAULT.int,
        SUPPLIED_FAULT.fields,
        None,
    ),
)
def test_python_validation_refuses_non_uuid_scalar_carriers(supplied: object) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultInstanceIdentity.model_validate(supplied)

    assert _failures(failure.value) == (((), "is_instance_of"),)


def test_identity_has_no_default_and_no_root_factory() -> None:
    with pytest.raises(ValidationError) as failure:
        FaultInstanceIdentity()  # pyright: ignore[reportCallIssue]

    assert _failures(failure.value) == (((), "is_instance_of"),)
    assert FaultInstanceIdentity.model_fields["root"].is_required()
    assert FaultInstanceIdentity.model_fields["root"].default_factory is None


# --- JSON shape, admission breadth, and the semantic round trip --------------


@pytest.mark.parametrize(("text", "version"), ADMITTED_UUID_TEXT)
def test_every_admitted_uuid_survives_the_semantic_json_round_trip(
    text: str,
    version: int | None,
) -> None:
    supplied = uuid.UUID(text)
    assert supplied.version == version

    value = FaultInstanceIdentity(supplied)
    restored = FaultInstanceIdentity.model_validate_json(value.model_dump_json())

    assert restored == value
    assert restored.root == supplied
    assert value.model_dump_json() == json.dumps(str(supplied))


def test_json_output_is_a_lowercase_hyphenated_scalar_string() -> None:
    dumped = json.loads(_identity().model_dump_json())

    assert isinstance(dumped, str)
    assert dumped == SUPPLIED_FAULT_TEXT
    assert dumped == dumped.lower()
    assert dumped.count("-") == 4


@pytest.mark.parametrize(
    "spelling",
    (
        SUPPLIED_FAULT_TEXT.upper(),
        f"urn:uuid:{SUPPLIED_FAULT_TEXT}",
        SUPPLIED_FAULT.hex,
    ),
)
def test_json_admission_uses_the_locked_uuid_grammar_without_preserving_spelling(
    spelling: str,
) -> None:
    restored = FaultInstanceIdentity.model_validate_json(json.dumps(spelling))

    assert restored == _identity()
    assert restored.model_dump_json() == json.dumps(SUPPLIED_FAULT_TEXT)


def test_the_nil_and_max_uuids_are_ordinary_admitted_subjects() -> None:
    nil = FaultInstanceIdentity(NIL_FAULT)
    maximum = FaultInstanceIdentity(MAX_FAULT)

    assert nil != maximum
    assert nil != _identity()
    assert maximum != _identity()
    assert nil == FaultInstanceIdentity(NIL_FAULT)
    assert FaultInstanceIdentity.model_validate_json(nil.model_dump_json()) == nil
    assert (
        FaultInstanceIdentity.model_validate_json(maximum.model_dump_json()) == maximum
    )


@pytest.mark.parametrize("special", (NIL_FAULT, MAX_FAULT))
def test_the_special_uuids_are_ordinary_subjects_inside_a_context(
    special: uuid.UUID,
) -> None:
    placed = _context(fault=special)

    restored = FaultRepositoryContext.model_validate_json(placed.model_dump_json())

    assert restored == placed
    assert restored != _context()
    assert json.loads(placed.model_dump_json()) == _context_payload(str(special))


@pytest.mark.parametrize(
    ("document", "expected"),
    (
        ('"not-a-uuid"', "uuid_parsing"),
        ('""', "uuid_parsing"),
        (f'"{SUPPLIED_FAULT_TEXT}-extra"', "uuid_parsing"),
        ("null", "uuid_type"),
        ("5", "uuid_type"),
        ("true", "uuid_type"),
        (f'["{SUPPLIED_FAULT_TEXT}"]', "uuid_type"),
    ),
)
def test_json_identity_refuses_malformed_and_mistyped_documents(
    document: str,
    expected: str,
) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultInstanceIdentity.model_validate_json(document)

    assert _failures(failure.value) == (((), expected),)


@pytest.mark.parametrize("wrapper", ("root", "fault_id", "value", "uuid"))
def test_earlier_object_shaped_identity_proposals_have_no_json_form(
    wrapper: str,
) -> None:
    document = json.dumps({wrapper: SUPPLIED_FAULT_TEXT})

    with pytest.raises(ValidationError) as failure:
        FaultInstanceIdentity.model_validate_json(document)

    # A root-level object is refused because the schema is a UUID scalar, not
    # because a RootModel forbids extra keys: RootModel has no such setting.
    assert _failures(failure.value) == (((), "uuid_type"),)
    assert "extra" not in FaultInstanceIdentity.model_config


@pytest.mark.parametrize("wrapper", ("root", "fault_id"))
def test_the_retired_wrappers_have_no_nested_json_form_either(wrapper: str) -> None:
    payload = _context_payload()
    payload["fault"] = {wrapper: SUPPLIED_FAULT_TEXT}

    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate_json(json.dumps(payload))

    assert _failures(failure.value) == ((("fault",), "uuid_type"),)


def test_python_mapping_input_is_not_an_identity_construction_form() -> None:
    with pytest.raises(ValidationError) as failure:
        FaultInstanceIdentity.model_validate({"root": SUPPLIED_FAULT})

    assert _failures(failure.value) == (((), "is_instance_of"),)


# --- equality, substitution, and hashing -------------------------------------


def test_equal_uuids_are_equal_identities_and_substitute_for_one_another() -> None:
    first = _identity()
    second = FaultInstanceIdentity(uuid.UUID(SUPPLIED_FAULT_TEXT))

    assert first == second
    assert hash(first) == hash(second)
    assert _context() == FaultRepositoryContext(fault=second, repository=_repository())
    assert _distinct_value_count(first, second) == 1


def test_different_uuids_are_different_identities() -> None:
    first = _identity()
    second = _identity(SECOND_FAULT)

    assert first != second
    assert _distinct_value_count(first, second) == 2


@pytest.mark.parametrize(
    "other",
    (
        SUPPLIED_FAULT,
        SUPPLIED_FAULT_TEXT,
        ForeignUuidRoot(SUPPLIED_FAULT),
        # An unrelated published identifier whose scalar content is the fault's
        # own text. Content equality must not become value equality.
        ProviderRepositoryId(SUPPLIED_FAULT_TEXT),
    ),
)
def test_an_identity_is_not_equal_to_a_carrier_that_merely_matches(
    other: object,
) -> None:
    assert _identity() != other
    assert other != _identity()


def test_identities_are_unordered_and_carry_no_sequence_meaning() -> None:
    earlier = FaultInstanceIdentity(uuid.UUID("018f2c9e-1a2b-7c3d-8e4f-5a6b7c8d9e0f"))
    later = FaultInstanceIdentity(uuid.UUID("018f2c9e-1a2b-7c3d-8e4f-5a6b7c8d9e10"))

    unordered: list[Any] = [earlier, later]
    with pytest.raises(TypeError):
        sorted(unordered)


def test_context_equality_uses_both_complete_canonical_children() -> None:
    supplied = _context()
    other_provider = FaultRepositoryContext(
        fault=_identity(),
        repository=RepositoryIdentity(
            provider=ProviderKey("gitlab"),
            provider_repository_id=ProviderRepositoryId(RETAINED_REPOSITORY_ID),
        ),
    )

    assert supplied == _context()
    assert supplied != _context(repository_id=OTHER_REPOSITORY_ID)
    assert supplied != _context(fault=SECOND_FAULT)
    # Every field of the embedded predecessor participates, not just the one
    # the other cases happen to vary.
    assert supplied != other_provider
    assert hash(supplied) == hash(_context())
    # Unequal values are permitted to hash-collide, so distinctness is witnessed
    # as two set members rather than as unequal hashes.
    assert _distinct_value_count(supplied, other_provider) == 2


def test_one_fault_may_be_placed_in_two_repositories() -> None:
    first = _context()
    second = _context(repository_id=OTHER_REPOSITORY_ID)

    assert first.fault == second.fault
    assert first.repository != second.repository
    assert first != second
    assert _distinct_value_count(first, second) == 2


def test_two_faults_may_share_one_repository() -> None:
    first = _context()
    second = _context(fault=SECOND_FAULT)

    assert first.repository == second.repository
    assert first.fault != second.fault
    assert first != second
    assert _distinct_value_count(first, second) == 2


# --- context construction, JSON shape, and the two round trips ---------------


def test_context_accepts_the_constructor_and_a_typed_python_mapping() -> None:
    constructed = _context()
    mapped = FaultRepositoryContext.model_validate(
        {"fault": _identity(), "repository": _repository()}
    )

    assert constructed == mapped
    assert tuple(FaultRepositoryContext.model_fields) == ("fault", "repository")


def test_context_revalidates_an_existing_context() -> None:
    supplied = _context()

    revalidated = FaultRepositoryContext.model_validate(supplied)

    assert revalidated == supplied


def test_context_json_carries_exactly_two_keys_and_the_predecessor_fields() -> None:
    document: dict[str, Any] = json.loads(_context().model_dump_json())

    assert document == _context_payload()
    assert sorted(document) == ["fault", "repository"]
    assert document["fault"] == SUPPLIED_FAULT_TEXT
    assert sorted(document["repository"]) == [
        "provider",
        "provider_repository_id",
        "schema_version",
    ]
    assert document["repository"]["schema_version"] == 1


def test_context_reconstructs_typed_children_from_json() -> None:
    supplied = _context()

    restored = FaultRepositoryContext.model_validate_json(supplied.model_dump_json())

    assert restored == supplied
    assert isinstance(restored.fault, FaultInstanceIdentity)
    assert isinstance(restored.repository, RepositoryIdentity)


def test_python_dump_reentry_is_a_different_input_language_and_is_refused() -> None:
    supplied = _context()

    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate(supplied.model_dump())

    assert _failures(failure.value) == (
        (("fault",), "value_error"),
        (("repository",), "value_error"),
    )


def test_decoded_json_validated_in_python_mode_is_not_json_mode_validation() -> None:
    supplied = _context()

    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate(json.loads(supplied.model_dump_json()))

    assert _failures(failure.value) == (
        (("fault",), "value_error"),
        (("repository",), "value_error"),
    )


def test_the_context_carries_no_schema_version_or_role_of_its_own() -> None:
    document: dict[str, Any] = json.loads(_context().model_dump_json())

    assert "schema_version" not in document
    assert set(FaultRepositoryContext.model_fields) == {"fault", "repository"}


# --- immediate child boundary guards -----------------------------------------


@pytest.mark.parametrize(
    "supplied",
    (
        SUPPLIED_FAULT,
        SUPPLIED_FAULT_TEXT,
        ForeignUuidRoot(SUPPLIED_FAULT),
        FaultIdentityLookalike(SUPPLIED_FAULT),
        {"root": SUPPLIED_FAULT},
    ),
    ids=("raw-uuid", "uuid-text", "foreign-model", "attribute-lookalike", "mapping"),
)
def test_the_fault_position_refuses_untyped_python_input(supplied: object) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate(
            {"fault": supplied, "repository": _repository()}
        )

    assert _failures(failure.value) == ((("fault",), "value_error"),)


@pytest.mark.parametrize(
    "supplied",
    (
        RETAINED_REPOSITORY_ID,
        ForeignRepositoryIdentity(
            provider=ProviderKey(RETAINED_PROVIDER),
            provider_repository_id=ProviderRepositoryId(RETAINED_REPOSITORY_ID),
        ),
        RepositoryIdentityLookalike(
            ProviderKey(RETAINED_PROVIDER),
            ProviderRepositoryId(RETAINED_REPOSITORY_ID),
        ),
    ),
    ids=("raw-text", "foreign-model", "attribute-lookalike"),
)
def test_the_repository_position_refuses_untyped_python_input(
    supplied: object,
) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate(
            {"fault": _identity(), "repository": supplied}
        )

    assert _failures(failure.value) == ((("repository",), "value_error"),)


def test_the_repository_position_refuses_a_python_mapping() -> None:
    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate(
            {"fault": _identity(), "repository": _repository_payload()}
        )

    assert _failures(failure.value) == ((("repository",), "value_error"),)


def test_the_constructor_guards_both_children_like_the_mapping_path() -> None:
    with pytest.raises(ValidationError) as fault_failure:
        FaultRepositoryContext(
            fault=SUPPLIED_FAULT,  # pyright: ignore[reportArgumentType]
            repository=_repository(),
        )
    with pytest.raises(ValidationError) as repository_failure:
        FaultRepositoryContext(
            fault=_identity(),
            repository=RETAINED_REPOSITORY_ID,  # pyright: ignore[reportArgumentType]
        )

    assert _failures(fault_failure.value) == ((("fault",), "value_error"),)
    assert _failures(repository_failure.value) == ((("repository",), "value_error"),)


@pytest.mark.parametrize(
    "supplied",
    (
        SUPPLIED_FAULT,
        ForeignUuidRoot(SUPPLIED_FAULT),
        FaultIdentityLookalike(SUPPLIED_FAULT),
    ),
    ids=("raw-uuid", "foreign-model", "attribute-lookalike"),
)
def test_a_top_level_mapping_with_from_attributes_still_guards_the_fault_child(
    supplied: object,
) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate(
            {"fault": supplied, "repository": _repository()},
            from_attributes=True,
        )

    assert _failures(failure.value) == ((("fault",), "value_error"),)


@pytest.mark.parametrize(
    "supplied",
    (
        RETAINED_REPOSITORY_ID,
        ForeignRepositoryIdentity(
            provider=ProviderKey(RETAINED_PROVIDER),
            provider_repository_id=ProviderRepositoryId(RETAINED_REPOSITORY_ID),
        ),
        RepositoryIdentityLookalike(
            ProviderKey(RETAINED_PROVIDER),
            ProviderRepositoryId(RETAINED_REPOSITORY_ID),
        ),
    ),
    ids=("raw-text", "foreign-model", "attribute-lookalike"),
)
def test_a_top_level_mapping_with_from_attributes_still_guards_the_repository_child(
    supplied: object,
) -> None:
    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate(
            {"fault": _identity(), "repository": supplied},
            from_attributes=True,
        )

    assert _failures(failure.value) == ((("repository",), "value_error"),)


def test_each_child_position_refuses_the_other_declared_child_type() -> None:
    """One shared predicate over both child types would admit a swap.

    Each supplied value below is a valid published child, just in the wrong
    position, so the refusal isolates the position rather than the value.
    """
    with pytest.raises(ValidationError) as fault_failure:
        FaultRepositoryContext.model_validate(
            {"fault": _repository(), "repository": _repository()}
        )
    with pytest.raises(ValidationError) as repository_failure:
        FaultRepositoryContext.model_validate(
            {"fault": _identity(), "repository": _identity()}
        )
    with pytest.raises(ValidationError) as both_failure:
        FaultRepositoryContext.model_validate(
            {"fault": _repository(), "repository": _identity()}
        )

    assert _failures(fault_failure.value) == ((("fault",), "value_error"),)
    assert _failures(repository_failure.value) == ((("repository",), "value_error"),)
    assert _failures(both_failure.value) == (
        (("fault",), "value_error"),
        (("repository",), "value_error"),
    )


def test_each_child_guard_reports_its_own_field() -> None:
    with pytest.raises(ValidationError) as fault_failure:
        FaultRepositoryContext.model_validate(
            {"fault": SUPPLIED_FAULT, "repository": _repository()}
        )
    with pytest.raises(ValidationError) as repository_failure:
        FaultRepositoryContext.model_validate(
            {"fault": _identity(), "repository": RETAINED_REPOSITORY_ID}
        )

    assert "fault must be a FaultInstanceIdentity" in str(fault_failure.value)
    assert "repository must be a RepositoryIdentity" in str(repository_failure.value)


def test_a_top_level_mapping_with_from_attributes_still_accepts_typed_children() -> (
    None
):
    accepted = FaultRepositoryContext.model_validate(
        {"fault": _identity(), "repository": _repository()},
        from_attributes=True,
    )

    assert accepted == _context()


# --- omission witnesses -------------------------------------------------------


def test_a_missing_fault_is_a_true_omission_beside_a_valid_repository() -> None:
    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate({"repository": _repository()})

    assert _failures(failure.value) == ((("fault",), "missing"),)


def test_a_missing_repository_is_a_true_omission_beside_a_valid_fault() -> None:
    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate({"fault": _identity()})

    assert _failures(failure.value) == ((("repository",), "missing"),)


def test_a_missing_json_fault_is_a_true_omission_beside_a_valid_repository() -> None:
    document = json.dumps({"repository": _repository_payload()})

    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate_json(document)

    assert _failures(failure.value) == ((("fault",), "missing"),)


def test_a_missing_json_repository_is_a_true_omission_beside_a_valid_fault() -> None:
    document = json.dumps({"fault": SUPPLIED_FAULT_TEXT})

    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate_json(document)

    assert _failures(failure.value) == ((("repository",), "missing"),)


def test_a_malformed_json_fault_fails_in_its_own_position() -> None:
    document = json.dumps(_context_payload(fault_text="not-a-uuid"))

    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate_json(document)

    assert _failures(failure.value) == ((("fault",), "uuid_parsing"),)


# --- frozen values ------------------------------------------------------------


def test_identity_field_assignment_and_deletion_are_refused() -> None:
    supplied = _identity()

    with pytest.raises(ValidationError) as assignment:
        supplied.root = SECOND_FAULT
    with pytest.raises(ValidationError) as deletion:
        del supplied.root

    assert _failures(assignment.value) == ((("root",), "frozen_instance"),)
    assert _failures(deletion.value) == ((("root",), "frozen_instance"),)
    assert supplied.root == SUPPLIED_FAULT


@pytest.mark.parametrize("field", ("fault", "repository"))
def test_context_field_assignment_and_deletion_are_refused(field: str) -> None:
    supplied = _context()

    with pytest.raises(ValidationError) as assignment:
        setattr(supplied, field, getattr(supplied, field))
    with pytest.raises(ValidationError) as deletion:
        delattr(supplied, field)

    assert _failures(assignment.value) == (((field,), "frozen_instance"),)
    assert _failures(deletion.value) == (((field,), "frozen_instance"),)
    assert supplied == _context()


# --- revalidation of malformed values at supported reentry points ------------


def test_an_unchecked_identity_holding_uuid_text_is_refused_on_reentry() -> None:
    tampered = FaultInstanceIdentity.model_construct(
        root=SUPPLIED_FAULT_TEXT  # pyright: ignore[reportArgumentType]
    )

    with pytest.raises(ValidationError) as direct:
        FaultInstanceIdentity.model_validate(tampered)
    with pytest.raises(ValidationError) as nested:
        FaultRepositoryContext(fault=tampered, repository=_repository())

    assert _failures(direct.value) == (((), "is_instance_of"),)
    assert _failures(nested.value) == ((("fault",), "is_instance_of"),)


def test_an_unchecked_identity_holding_a_foreign_value_is_refused_on_reentry() -> None:
    tampered = FaultInstanceIdentity.model_construct(
        root=None  # pyright: ignore[reportArgumentType]
    )

    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext(fault=tampered, repository=_repository())

    assert _failures(failure.value) == ((("fault",), "is_instance_of"),)


@pytest.mark.parametrize("field", ("fault", "repository"))
def test_a_context_with_an_untyped_immediate_child_is_refused_on_reentry(
    field: str,
) -> None:
    supplied: dict[str, Any] = {"fault": _identity(), "repository": _repository()}
    supplied[field] = SUPPLIED_FAULT if field == "fault" else _repository_payload()
    tampered = FaultRepositoryContext.model_construct(**supplied)

    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate(tampered)

    assert _failures(failure.value) == (((field,), "value_error"),)


def test_a_predecessor_with_an_unsupported_schema_version_is_refused() -> None:
    tampered = RepositoryIdentity.model_construct(
        schema_version=2,
        provider=ProviderKey(RETAINED_PROVIDER),
        provider_repository_id=ProviderRepositoryId(RETAINED_REPOSITORY_ID),
    )

    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext(fault=_identity(), repository=tampered)

    assert _failures(failure.value) == (
        (("repository", "schema_version"), "literal_error"),
    )


def test_a_predecessor_with_invalid_child_content_is_refused() -> None:
    tampered_provider = RepositoryIdentity.model_construct(
        schema_version=1,
        provider=ProviderKey.model_construct(root="GitHub"),
        provider_repository_id=ProviderRepositoryId(RETAINED_REPOSITORY_ID),
    )
    tampered_identifier = RepositoryIdentity.model_construct(
        schema_version=1,
        provider=ProviderKey(RETAINED_PROVIDER),
        provider_repository_id=ProviderRepositoryId.model_construct(
            root=f" {RETAINED_REPOSITORY_ID} "
        ),
    )

    with pytest.raises(ValidationError) as provider_failure:
        FaultRepositoryContext(fault=_identity(), repository=tampered_provider)
    with pytest.raises(ValidationError) as identifier_failure:
        FaultRepositoryContext(fault=_identity(), repository=tampered_identifier)

    assert _failures(provider_failure.value) == (
        (("repository", "provider"), "value_error"),
    )
    assert _failures(identifier_failure.value) == (
        (("repository", "provider_repository_id"), "value_error"),
    )


def test_inherited_predecessor_normalization_of_valid_raw_children_is_preserved() -> (
    None
):
    # A predecessor built unchecked from raw but VALID strings normalizes under
    # its own published schema. That is inherited valid behavior, not a hole
    # this Slice may close by adding a recursive nominal guard.
    unchecked = RepositoryIdentity.model_construct(
        schema_version=1,
        provider="github",
        provider_repository_id=RETAINED_REPOSITORY_ID,
    )

    accepted = FaultRepositoryContext(fault=_identity(), repository=unchecked)

    assert accepted == _context()
    assert accepted.repository.provider == ProviderKey(RETAINED_PROVIDER)

    # The leniency is the predecessor's own published behavior rather than an
    # artefact of the bypass API: its ordinary constructor accepts the same
    # raw but valid children, and this Slice tightens neither.
    ordinary = RepositoryIdentity(
        provider="github",  # pyright: ignore[reportArgumentType]
        provider_repository_id=RETAINED_REPOSITORY_ID,  # pyright: ignore[reportArgumentType]
    )
    assert FaultRepositoryContext(fault=_identity(), repository=ordinary) == _context()


# --- subclasses: acceptance without a preservation promise -------------------


def test_a_no_added_field_identity_subclass_is_admitted_and_base_normalized() -> None:
    accepted = FaultRepositoryContext(
        fault=UnextendedFaultInstanceIdentity(SUPPLIED_FAULT),
        repository=_repository(),
    )

    assert accepted == _context()
    assert accepted.fault == _identity()


def test_a_no_added_field_predecessor_subclass_is_admitted_and_base_normalized() -> (
    None
):
    accepted = FaultRepositoryContext(
        fault=_identity(),
        repository=UnextendedRepositoryIdentity(
            provider=ProviderKey(RETAINED_PROVIDER),
            provider_repository_id=ProviderRepositoryId(RETAINED_REPOSITORY_ID),
        ),
    )

    assert accepted == _context()
    assert accepted.repository == _repository()


def test_a_predecessor_subclass_extra_field_remains_refused() -> None:
    supplied = ExtendedRepositoryIdentity(
        provider=ProviderKey(RETAINED_PROVIDER),
        provider_repository_id=ProviderRepositoryId(RETAINED_REPOSITORY_ID),
        note="supplied",
    )

    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext(fault=_identity(), repository=supplied)

    assert _failures(failure.value) == ((("repository", "note"), "extra_forbidden"),)


def test_a_subclass_value_is_equal_only_after_base_normalization() -> None:
    """Equality before normalization is not something this Slice promises.

    A base and a subclass instance need not compare equal, and model equality is
    not redefined to force it. What is promised is that a subclass value
    normalizes to the declared base value at every supported entry point, so the
    assertions below are made on the normalized result rather than on the
    supplied instance.
    """
    base = _identity()
    subclass = UnextendedFaultInstanceIdentity(SUPPLIED_FAULT)

    normalized = FaultRepositoryContext(fault=subclass, repository=_repository()).fault
    assert normalized == base
    assert FaultInstanceIdentity.model_validate(subclass) == base
    assert type(FaultInstanceIdentity.model_validate(subclass)) is FaultInstanceIdentity


# --- extra fields under the declared policy -----------------------------------


@pytest.mark.parametrize("extra", ("role", "primary", "schema_version", "evidence"))
def test_context_extra_python_fields_are_refused(extra: str) -> None:
    supplied: dict[str, Any] = {
        "fault": _identity(),
        "repository": _repository(),
        extra: "supplied",
    }

    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate(supplied)

    assert _failures(failure.value) == (((extra,), "extra_forbidden"),)


@pytest.mark.parametrize("extra", ("role", "primary", "schema_version", "evidence"))
def test_context_extra_json_fields_are_refused(extra: str) -> None:
    payload = _context_payload()
    payload[extra] = "supplied"

    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate_json(json.dumps(payload))

    assert _failures(failure.value) == (((extra,), "extra_forbidden"),)


def test_a_nested_predecessor_extra_field_is_refused_in_json() -> None:
    payload = _context_payload()
    repository: dict[str, Any] = payload["repository"]
    repository["alias"] = "pytest-dev/pytest"

    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate_json(json.dumps(payload))

    assert _failures(failure.value) == ((("repository", "alias"), "extra_forbidden"),)


# --- the module's own declared surface ---------------------------------------


def test_the_module_publishes_exactly_eight_symbols() -> None:
    assert fault_module.__all__ == EXPECTED_EXPORTS
    assert [
        node.name
        for node in ast.walk(_fault_source_tree())
        if isinstance(node, ast.ClassDef)
    ] == EXPECTED_EXPORTS


def test_the_module_binds_no_other_name_at_module_level() -> None:
    """`__all__` and a class scan do not see an alias, a factory or a registry.

    The authorized surface is eight models. An alias, a lambda factory, a
    generic type alias, or a module-level collection would each add a ninth
    public thing while leaving `__all__` and the class list untouched, so the
    binding sites themselves are enumerated here.
    """
    tree = _fault_source_tree()
    bound: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                assert isinstance(target, ast.Name), ast.dump(target)
                bound.append(target.id)
        elif isinstance(node, ast.AnnAssign):
            assert isinstance(node.target, ast.Name), ast.dump(node.target)
            bound.append(node.target.id)
        elif isinstance(node, ast.TypeAlias):
            raise AssertionError(f"unexpected type alias: {ast.unparse(node)}")

    assert bound == ["__all__"]
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Lambda)]

    locally_defined = {
        name
        for name, value in vars(fault_module).items()
        if not name.startswith("_")
        and getattr(value, "__module__", None) == fault_module.__name__
    }
    assert locally_defined == set(EXPECTED_EXPORTS)


def test_the_requirement_to_witness_matrix_is_exact() -> None:
    identity_root = FaultInstanceIdentity.model_fields["root"]
    context_fields = FaultRepositoryContext.model_fields
    validators = FaultRepositoryContext.__pydantic_decorators__.field_validators

    assert identity_root.annotation is uuid.UUID
    assert identity_root.is_required()
    assert dict(FaultInstanceIdentity.model_config) == {
        "frozen": True,
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    assert not FaultInstanceIdentity.__pydantic_decorators__.field_validators
    assert not FaultInstanceIdentity.__pydantic_decorators__.model_validators

    assert tuple(context_fields) == ("fault", "repository")
    assert context_fields["fault"].annotation is FaultInstanceIdentity
    assert context_fields["repository"].annotation is RepositoryIdentity
    assert all(field.is_required() for field in context_fields.values())
    assert dict(FaultRepositoryContext.model_config) == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }
    # The binding is the requirement: one before-validator standing over each
    # declared child. The private method names are the module's own business
    # and are checked structurally elsewhere, not frozen twice here.
    assert sorted(
        (validator.info.fields, validator.info.mode)
        for validator in validators.values()
    ) == [(("fault",), "before"), (("repository",), "before")]
    assert not FaultRepositoryContext.__pydantic_decorators__.model_validators


def test_the_module_performs_no_io_and_allocates_no_identifier() -> None:
    tree = _fault_source_tree()
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".")[0])

    assert imported == {"typing", "uuid", "pydantic", "faultatlas"}
    assert not imported & FORBIDDEN_IMPORTS

    called: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if isinstance(target, ast.Attribute):
            called.add(target.attr)
        elif isinstance(target, ast.Name):
            called.add(target.id)

    assert not called & FORBIDDEN_UUID_CALLS
    assert "Field" not in called
    assert "TypeAdapter" not in called


def test_the_module_defines_only_the_declared_validators() -> None:
    defined = [
        node.name
        for node in ast.walk(_fault_source_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    assert defined == [
        "_require_typed_python_fault",
        "_require_typed_python_repository",
        "_require_typed_python_report",
        "_require_typed_python_context",
        "_require_unpadded_text",
        "_require_typed_python_scenario",
        "_require_typed_python_report",
        "_require_unpadded_text",
        "_require_typed_python_occurrence",
        "_require_typed_python_scenario",
        "_require_unpadded_text",
    ]


def test_the_new_symbols_are_not_re_exported_by_the_package_roots() -> None:
    import faultatlas
    import faultatlas.domain as domain_package

    assert faultatlas.__all__ == ["__version__"]
    assert getattr(domain_package, "__all__", None) in (None, [])
    for name in EXPECTED_EXPORTS:
        assert not hasattr(faultatlas, name)
        assert not hasattr(domain_package, name)


def test_the_context_reuses_the_predecessor_type_itself() -> None:
    repository_identity = _context().repository

    assert type(repository_identity) is RepositoryIdentity
    assert FaultRepositoryContext.model_fields["repository"].annotation is (
        RepositoryIdentity
    )
    # No source-object identity is converted into or bound to a fault identity.
    numbered = NumberedSourceObjectIdentity(
        repository_identity=_repository(),
        kind=SourceObjectKind.PULL_REQUEST,
        repository_scoped_number=RepositoryScopedNumber(RETAINED_PULL_REQUEST_NUMBER),
    )
    assert _identity() != numbered
    with pytest.raises(ValidationError) as failure:
        FaultRepositoryContext.model_validate(
            {"fault": numbered, "repository": _repository()}
        )
    assert _failures(failure.value) == ((("fault",), "value_error"),)


# --- roadmap transition -------------------------------------------------------


def test_the_roadmap_records_the_p06_s01_transition() -> None:
    raw = (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8")
    roadmap = " ".join(raw.split())
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    assert "## S1.P06 — Fault Instance Model" in roadmap
    assert "`S1.P06` is active and incomplete" in roadmap
    assert (
        "`S1.P06.S01` — Fault Instance Identity and Repository Context (complete)"
        in roadmap
    )
    assert "`S1.P06.S02` is complete" in roadmap
    assert "`S1.P06.S03` is complete" in roadmap
    assert "`S1.P06.S04` is complete" in roadmap
    assert "`S1.P06.S05` is complete" in roadmap
    assert "`S1.P06.S06` is complete" in roadmap
    assert "`S1.P06.S07` is complete" in roadmap
    assert "`S1.P06.S08` is complete" in roadmap
    assert "`S1.P06.S09` is complete" in roadmap
    assert "`S1.P06.S10` is next and not started" in roadmap
    assert "`S1.P07` through `S1.P10` remain not started" in roadmap

    assert "faultatlas.domain.fault" in current
    for symbol in EXPECTED_EXPORTS:
        assert f"`{symbol}`" in current
    assert "Production Python sources are 20." in current

    # The superseded entry-gate claims must be retired, not left standing.
    assert "`S1.P06` is next and not started" not in roadmap
    assert "`S1.P06` is `eligible_to_begin`" not in roadmap
    assert "`S1.P06` is complete" not in roadmap
    assert "- **S1.P06 — Fault Instance Model**" not in raw


def test_the_roadmap_route_is_provisional_beyond_this_slice() -> None:
    roadmap = " ".join(
        (REPOSITORY_ROOT / "docs/roadmap.md").read_text(encoding="utf-8").split()
    )

    assert "The `S1.P06` route is provisional beyond `S1.P06.S09`." in roadmap
    for index in range(2, 13):
        assert f"`S1.P06.S{index:02d}`" in roadmap
    assert "`S1.P06.S13`" not in roadmap
    # Only S01 through S09 are claimed complete in the route.
    for index in range(10, 13):
        assert f"`S1.P06.S{index:02d}` is complete" not in roadmap


# --- packaging and an isolated installed-wheel smoke -------------------------


ISOLATED_SMOKE = """
import json
import os
import sys
import uuid
from pathlib import Path

installed = Path(os.environ["INSTALLED_ROOT"]).resolve()
checkout = Path(os.environ["CHECKOUT_SOURCE_ROOT"]).resolve()
sys.path = [entry for entry in sys.path if Path(entry).resolve() != checkout]
sys.path.insert(0, str(installed))

import faultatlas.domain.fault as fault_module
from faultatlas.domain.fault import FaultInstanceIdentity, FaultRepositoryContext
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)

resolved = Path(fault_module.__file__).resolve()
assert resolved.is_relative_to(installed), resolved
assert not resolved.is_relative_to(checkout), resolved
assert fault_module.__all__ == [
    "FaultInstanceIdentity",
    "FaultRepositoryContext",
    "FaultReportIdentity",
    "SuppliedFaultReport",
    "FaultScenarioIdentity",
    "FaultOccurrenceIdentity",
    "SuppliedFaultScenario",
    "SuppliedFaultOccurrenceContext",
]

supplied = uuid.UUID("12345678-1234-4234-8234-123456789abc")
identity = FaultInstanceIdentity(supplied)
context = FaultRepositoryContext(
    fault=identity,
    repository=RepositoryIdentity(
        provider=ProviderKey("github"),
        provider_repository_id=ProviderRepositoryId("37489525"),
    ),
)
assert FaultInstanceIdentity.model_validate_json(identity.model_dump_json()) == identity
assert FaultRepositoryContext.model_validate_json(context.model_dump_json()) == context
print(json.dumps({"module": str(resolved), "context": context.model_dump_json()}))
"""


@pytest.fixture(scope="session")
def offline_distributions(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, Path]:
    uv = shutil.which("uv")
    assert uv is not None, "uv must be available to build the supported distributions"

    root = tmp_path_factory.mktemp("fault-identity-package")
    output = root / "distributions"
    output.mkdir()
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "UV_CACHE_DIR": str(root / "uv-cache"),
            "UV_NO_SYNC": "1",
            "UV_OFFLINE": "1",
        }
    )
    result = subprocess.run(
        [uv, "build", "--offline", "--no-create-gitignore", "--out-dir", str(output)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"offline build failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    wheels = tuple(output.glob("*.whl"))
    sdists = tuple(output.glob("*.tar.gz"))
    assert len(wheels) == 1, f"expected one wheel, found {wheels!r}"
    assert len(sdists) == 1, f"expected one sdist, found {sdists!r}"
    return wheels[0], sdists[0]


def test_the_wheel_ships_the_new_module_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    wheel, _ = offline_distributions
    with zipfile.ZipFile(wheel) as archive:
        names = tuple(info.filename for info in archive.infolist() if not info.is_dir())

    modules = sorted(name for name in names if name.endswith(".py"))
    assert modules == [
        "faultatlas/__init__.py",
        "faultatlas/__main__.py",
        "faultatlas/cli.py",
        "faultatlas/domain/__init__.py",
        "faultatlas/domain/compatibility.py",
        "faultatlas/domain/evidence.py",
        "faultatlas/domain/fault.py",
        "faultatlas/domain/fault_evidence_link.py",
        "faultatlas/domain/fault_instance.py",
        "faultatlas/domain/fault_interpretation.py",
        "faultatlas/domain/fault_repair.py",
        "faultatlas/domain/fault_source_relationship.py",
        "faultatlas/domain/fault_test.py",
        "faultatlas/domain/history.py",
        "faultatlas/domain/history_evidence_link.py",
        "faultatlas/domain/identity.py",
        "faultatlas/domain/revision.py",
        "faultatlas/domain/snapshot.py",
        "faultatlas/domain/snapshot_evidence_link.py",
        "faultatlas/domain/source.py",
    ]
    assert len(modules) == 20
    for name in names:
        assert "reference_corpus" not in name
        assert not name.startswith("tests/")
        assert not name.startswith("docs/")


def test_the_sdist_ships_the_new_module_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    _, sdist = offline_distributions
    with tarfile.open(sdist, "r:gz") as archive:
        names = tuple(member.name for member in archive.getmembers() if member.isfile())

    modules = sorted(
        name.split("/src/", 1)[1] for name in names if name.endswith(".py")
    )
    assert modules == [
        "faultatlas/__init__.py",
        "faultatlas/__main__.py",
        "faultatlas/cli.py",
        "faultatlas/domain/__init__.py",
        "faultatlas/domain/compatibility.py",
        "faultatlas/domain/evidence.py",
        "faultatlas/domain/fault.py",
        "faultatlas/domain/fault_evidence_link.py",
        "faultatlas/domain/fault_instance.py",
        "faultatlas/domain/fault_interpretation.py",
        "faultatlas/domain/fault_repair.py",
        "faultatlas/domain/fault_source_relationship.py",
        "faultatlas/domain/fault_test.py",
        "faultatlas/domain/history.py",
        "faultatlas/domain/history_evidence_link.py",
        "faultatlas/domain/identity.py",
        "faultatlas/domain/revision.py",
        "faultatlas/domain/snapshot.py",
        "faultatlas/domain/snapshot_evidence_link.py",
        "faultatlas/domain/source.py",
    ]
    assert len(modules) == 20
    for name in names:
        parts = Path(name).parts
        assert "reference_corpus" not in parts
        assert "tests" not in parts
        assert "docs" not in parts


def test_the_installed_wheel_exercises_the_same_new_types(
    offline_distributions: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    wheel, _ = offline_distributions
    installed = tmp_path / "installed"
    installed.mkdir()
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)

    assert (installed / "faultatlas/domain/fault.py").is_file()

    environment = os.environ.copy()
    environment.update(
        {
            "INSTALLED_ROOT": str(installed),
            "CHECKOUT_SOURCE_ROOT": str(CHECKOUT_SOURCE_ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-I", "-c", ISOLATED_SMOKE],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"isolated wheel smoke failed\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    reported: dict[str, str] = json.loads(result.stdout.strip().splitlines()[-1])
    assert Path(reported["module"]).is_relative_to(installed)
    assert not Path(reported["module"]).is_relative_to(CHECKOUT_SOURCE_ROOT)
    assert json.loads(reported["context"]) == _context_payload()
