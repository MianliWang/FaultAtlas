"""Finite independent examples for the supplied assessment's complete boundary."""

from __future__ import annotations

import copy
import json
import uuid
from collections.abc import Callable
from typing import Any, cast

import pytest
from pydantic import BaseModel, ValidationError

import faultatlas.domain.assessment as module
from faultatlas.domain.assessment import (
    AssessmentAttribution,
    AssessmentBasis,
    AssessmentCondition,
    AssessmentMaterial,
    AssessmentTarget,
    SuppliedAssessment,
    SuppliedAssessmentConflict,
    SuppliedConditionOpinion,
    SuppliedOverallOpinion,
)
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)
from faultatlas.domain.invariant import FaultInvariantIdentity, SuppliedFaultInvariant
from faultatlas.domain.pattern import FaultPatternIdentity, SuppliedFaultPattern
from faultatlas.domain.revision import (
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectKind,
)
from faultatlas.domain.snapshot import (
    RepositorySnapshotDeclaredPathScope,
    RepositorySnapshotIdentity,
)

check_budget: Callable[[object], None] = getattr(module, "_check_domain_budget")

FIELDS: dict[type[BaseModel], tuple[str, ...]] = {
    AssessmentAttribution: ("supplier", "rationale"),
    AssessmentTarget: ("snapshot", "declared_host", "declared_visibility", "scope"),
    AssessmentCondition: ("key", "statement"),
    AssessmentMaterial: ("key", "description", "attribution", "record", "locator"),
    AssessmentBasis: (
        "source",
        "target",
        "context_statement",
        "conditions",
        "materials",
        "material_omission",
    ),
    SuppliedConditionOpinion: (
        "key",
        "condition",
        "position",
        "statement",
        "attribution",
        "material_keys",
    ),
    SuppliedAssessmentConflict: (
        "left_opinion_key",
        "right_opinion_key",
        "attribution",
    ),
    SuppliedOverallOpinion: ("statement", "attribution"),
    SuppliedAssessment: (
        "attribution",
        "basis",
        "opinions",
        "conflicts",
        "overall_opinion",
    ),
}


def sample_wire() -> dict[str, Any]:
    # Defaults and upstream schema versions are authored, not read from a model.
    return {
        "attribution": {
            "supplier": "Example author",
            "rationale": "Synthetic input for a structural review.",
        },
        "basis": {
            "source": {
                "pattern": "00000000-0000-4000-8000-000000000001",
                "pattern_statement": "Repeated evaluation may repeat a side effect.",
            },
            "target": {
                "snapshot": {
                    "repository": {
                        "schema_version": 1,
                        "provider": "github",
                        "provider_repository_id": "1001",
                    },
                    "revision": {
                        "schema_version": 1,
                        "kind": "commit",
                        "algorithm": "sha1",
                        "full_digest": "1111111111111111111111111111111111111111",
                    },
                },
                "declared_host": "github.com",
                "declared_visibility": "public",
                "scope": None,
            },
            "context_statement": None,
            "conditions": [
                {
                    "key": "once",
                    "statement": "A side-effecting expression is evaluated no more than once.",
                }
            ],
            "materials": None,
            "material_omission": None,
        },
        "opinions": [
            {
                "key": "op-a",
                "condition": {
                    "key": "once",
                    "statement": "A side-effecting expression is evaluated no more than once.",
                },
                "position": "unknown",
                "statement": "No target run or inspected target material was supplied.",
                "attribution": {
                    "supplier": "Reviewer A",
                    "rationale": "The evaluation count cannot be established from this file.",
                },
                "material_keys": [],
            }
        ],
        "conflicts": [],
        "overall_opinion": None,
    }


def typed_sample() -> SuppliedAssessment:
    snapshot = RepositorySnapshotIdentity(
        repository=RepositoryIdentity(
            provider=ProviderKey("github"),
            provider_repository_id=ProviderRepositoryId("1001"),
        ),
        revision=GitCommitIdentity(
            kind=GitObjectKind.COMMIT,
            algorithm=GitHashAlgorithm.SHA1,
            full_digest="1" * 40,
        ),
    )
    condition = AssessmentCondition(
        key="once",
        statement="A side-effecting expression is evaluated no more than once.",
    )
    basis = AssessmentBasis(
        source=SuppliedFaultPattern(
            pattern=FaultPatternIdentity(
                uuid.UUID("00000000-0000-4000-8000-000000000001")
            ),
            pattern_statement="Repeated evaluation may repeat a side effect.",
        ),
        target=AssessmentTarget(
            snapshot=snapshot, declared_host="github.com", declared_visibility="public"
        ),
        conditions=(condition,),
    )
    return SuppliedAssessment(
        attribution=AssessmentAttribution(
            supplier="Example author",
            rationale="Synthetic input for a structural review.",
        ),
        basis=basis,
        opinions=(
            SuppliedConditionOpinion(
                key="op-a",
                condition=condition,
                position="unknown",
                statement="No target run or inspected target material was supplied.",
                attribution=AssessmentAttribution(
                    supplier="Reviewer A",
                    rationale="The evaluation count cannot be established from this file.",
                ),
            ),
        ),
    )


def fields(value: BaseModel) -> dict[str, Any]:
    return {name: getattr(value, name) for name in type(value).model_fields}


def material_wire(key: str = "note") -> dict[str, Any]:
    return {
        "key": key,
        "description": "Supplied inline note.",
        "attribution": {
            "supplier": "Material supplier",
            "rationale": "Record and locator are declarations only.",
        },
        "record": {
            "schema_version": 1,
            "format_name": "synthetic-note",
            "format_version": "1",
            "canonicalization": "json-sort-keys-compact-utf8-lf-v1",
            "sha256": "a" * 64,
            "byte_length": 1,
        },
        "locator": "https://invalid.example/note; do not execute or fetch",
    }


def rich_wire() -> dict[str, Any]:
    wire = sample_wire()
    wire["basis"]["materials"] = [material_wire(), material_wire("unused")]
    wire["opinions"][0]["material_keys"] = ["note"]
    other = copy.deepcopy(wire["opinions"][0])
    other.update(
        key="op-b",
        position="stated",
        statement="verified by our upstream script",
        attribution={"supplier": "Reviewer B", "rationale": "This remains a claim."},
    )
    wire["opinions"].append(other)
    conflict = {
        "left_opinion_key": "op-a",
        "right_opinion_key": "op-b",
        "attribution": {
            "supplier": "Conflict supplier",
            "rationale": "The caller declares this conflict.",
        },
    }
    wire["conflicts"] = [conflict, copy.deepcopy(conflict)]
    wire["overall_opinion"] = {
        "statement": "applicable",
        "attribution": {
            "supplier": "Overall supplier",
            "rationale": "A supplied opinion only.",
        },
    }
    return wire


def examples() -> dict[type[BaseModel], BaseModel]:
    value = SuppliedAssessment.model_validate_json(json.dumps(rich_wire()))
    assert value.basis.materials is not None and value.overall_opinion is not None
    return {
        AssessmentAttribution: value.attribution,
        AssessmentTarget: value.basis.target,
        AssessmentCondition: value.basis.conditions[0],
        AssessmentMaterial: value.basis.materials[0],
        AssessmentBasis: value.basis,
        SuppliedConditionOpinion: value.opinions[0],
        SuppliedAssessmentConflict: value.conflicts[0],
        SuppliedOverallOpinion: value.overall_opinion,
        SuppliedAssessment: typed_sample(),
    }


def test_exact_surface_and_independently_authored_full_value() -> None:
    assert module.__all__ == [model.__name__ for model in FIELDS]
    value = typed_sample()
    assert value.model_dump(mode="json") == sample_wire()
    assert SuppliedAssessment.model_validate_json(json.dumps(sample_wire())) == value
    assert SuppliedAssessment.model_validate_json(value.model_dump_json()) == value
    for model, expected in FIELDS.items():
        assert tuple(model.model_fields) == expected
        assert {
            k: model.model_config.get(k)
            for k in (
                "frozen",
                "strict",
                "extra",
                "revalidate_instances",
                "validate_default",
            )
        } == {
            "frozen": True,
            "strict": True,
            "extra": "forbid",
            "revalidate_instances": "always",
            "validate_default": True,
        }
        assert not any(
            f.alias or f.validation_alias or f.serialization_alias
            for f in model.model_fields.values()
        )
        assert not model.__pydantic_root_model__


@pytest.mark.parametrize("model", FIELDS)
def test_required_nullable_defaults_frozen_and_no_extras(
    model: type[BaseModel],
) -> None:
    value = examples()[model]
    data = fields(value)
    with pytest.raises(ValidationError) as extra:
        model.model_validate(data | {"verified": True})
    assert (extra.value.errors()[0]["loc"], extra.value.errors()[0]["type"]) == (
        ("verified",),
        "extra_forbidden",
    )
    with pytest.raises(ValidationError) as frozen:
        setattr(value, FIELDS[model][0], data[FIELDS[model][0]])
    assert frozen.value.errors()[0]["type"] == "frozen_instance"
    for name, info in model.model_fields.items():
        if info.is_required():
            missing = data.copy()
            missing.pop(name)
            with pytest.raises(ValidationError) as absent:
                model.model_validate(missing)
            assert any(
                e["loc"] == (name,) and e["type"] == "missing"
                for e in absent.value.errors()
            )
            with pytest.raises(ValidationError) as null:
                model.model_validate(data | {name: None})
            assert any(e["loc"][0] == name for e in null.value.errors())
        else:
            absent = data.copy()
            absent.pop(name)
            assert getattr(model.model_validate(absent), name) == info.default


@pytest.mark.parametrize("source_kind", ["pattern", "invariant"])
def test_sources_without_faults_and_current_legal_unchecked_values(
    source_kind: str,
) -> None:
    wire = sample_wire()
    if source_kind == "invariant":
        wire["basis"]["source"] = {
            "invariant": "00000000-0000-4000-8000-000000000002",
            "invariant_statement": "  invalid padding  ",
        }
        with pytest.raises(ValidationError, match="leading or trailing"):
            SuppliedAssessment.model_validate_json(json.dumps(wire))
        wire["basis"]["source"]["invariant_statement"] = "A supplied invariant."
    value = SuppliedAssessment.model_validate_json(json.dumps(wire))
    assert value.model_dump(mode="json") == wire
    legal = SuppliedAssessment.model_construct(**fields(value))
    assert SuppliedAssessment.model_validate(legal) == value
    assert "fault_instance" not in value.model_dump_json()
    if source_kind == "invariant":
        assert value.basis.source == SuppliedFaultInvariant(
            invariant=FaultInvariantIdentity(
                uuid.UUID("00000000-0000-4000-8000-000000000002")
            ),
            invariant_statement="A supplied invariant.",
        )


@pytest.mark.parametrize(
    "change", ["provider", "host", "visibility", "revision", "scope", "mixed_source"]
)
def test_target_and_source_owner_failures(change: str) -> None:
    wire = sample_wire()
    if change == "provider":
        wire["basis"]["target"]["snapshot"]["repository"]["provider"] = "other"
    elif change == "host":
        wire["basis"]["target"]["declared_host"] = "ghe.example"
    elif change == "visibility":
        wire["basis"]["target"]["declared_visibility"] = "private"
    elif change == "revision":
        del wire["basis"]["target"]["snapshot"]["revision"]
    elif change == "scope":
        snap = copy.deepcopy(wire["basis"]["target"]["snapshot"])
        snap["revision"]["full_digest"] = "2" * 40
        wire["basis"]["target"]["scope"] = {"snapshot": snap, "declared_paths": []}
    else:
        wire["basis"]["source"]["invariant"] = "00000000-0000-4000-8000-000000000002"
    with pytest.raises(ValidationError) as failure:
        SuppliedAssessment.model_validate_json(json.dumps(wire))
    errors = failure.value.errors()
    if change in ("provider", "scope"):
        assert errors[0]["loc"] == ("basis", "target")
    elif change in ("host", "visibility"):
        assert errors[0]["type"] == "literal_error"
    elif change == "revision":
        assert (
            errors[0]["loc"] == ("basis", "target", "snapshot", "revision")
            and errors[0]["type"] == "missing"
        )
    else:
        assert any(e["type"] == "extra_forbidden" for e in errors)


def test_empty_matching_scope_and_optional_states() -> None:
    value = typed_sample()
    target = value.basis.target
    scope = RepositorySnapshotDeclaredPathScope(
        snapshot=target.snapshot, declared_paths=()
    )
    scoped = AssessmentTarget.model_validate(fields(target) | {"scope": scope})
    assert AssessmentTarget.model_validate_json(scoped.model_dump_json()) == scoped
    assert scope.declared_paths == ()
    for materials, omission in (
        (None, None),
        (None, " Explicit omission "),
        ((), None),
    ):
        basis = AssessmentBasis.model_validate(
            fields(value.basis)
            | {"materials": materials, "material_omission": omission}
        )
        assert basis.materials == materials and basis.material_omission == omission
    with pytest.raises(ValidationError, match="cannot coexist"):
        AssessmentBasis.model_validate(
            fields(value.basis) | {"materials": (), "material_omission": "omitted"}
        )


@pytest.mark.parametrize(
    "change",
    [
        "condition_duplicate",
        "material_duplicate",
        "opinion_duplicate",
        "condition_text",
        "missing_condition",
        "missing_material",
        "material_ref_duplicate",
        "missing_conflict",
        "self_conflict",
    ],
)
def test_local_reference_failures_have_valid_prerequisites(change: str) -> None:
    wire = rich_wire()
    SuppliedAssessment.model_validate_json(json.dumps(wire))
    if change == "condition_duplicate":
        wire["basis"]["conditions"] *= 2
    elif change == "material_duplicate":
        wire["basis"]["materials"].append(copy.deepcopy(wire["basis"]["materials"][0]))
    elif change == "opinion_duplicate":
        wire["opinions"].append(copy.deepcopy(wire["opinions"][0]))
    elif change == "condition_text":
        wire["opinions"][0]["condition"]["statement"] = "Changed under the same key."
    elif change == "missing_condition":
        wire["opinions"][0]["condition"]["key"] = "absent"
    elif change == "missing_material":
        wire["opinions"][0]["material_keys"] = ["absent"]
    elif change == "material_ref_duplicate":
        wire["opinions"][0]["material_keys"] = ["note", "note"]
    elif change == "missing_conflict":
        wire["conflicts"][0]["left_opinion_key"] = "absent"
    else:
        wire["conflicts"][0]["left_opinion_key"] = "op-b"
    expected = {
        "condition_duplicate": "basis condition keys",
        "material_duplicate": "basis material keys",
        "opinion_duplicate": "assessment opinion keys",
        "condition_text": "full-value basis member",
        "missing_condition": "full-value basis member",
        "missing_material": "absent material key",
        "material_ref_duplicate": "opinion material keys",
        "missing_conflict": "absent opinion key",
        "self_conflict": "distinct opinion keys",
    }[change]
    with pytest.raises(ValidationError, match=expected):
        SuppliedAssessment.model_validate_json(json.dumps(wire))


def test_full_equal_reconstructed_conditions_and_explicit_conflicts() -> None:
    value = SuppliedAssessment.model_validate_json(json.dumps(rich_wire()))
    condition = AssessmentCondition.model_validate_json(
        value.basis.conditions[0].model_dump_json()
    )
    assert (
        condition == value.basis.conditions[0]
        and condition is not value.basis.conditions[0]
    )
    opinion = SuppliedConditionOpinion.model_validate(
        fields(value.opinions[0]) | {"condition": condition}
    )
    assert (
        SuppliedAssessment.model_validate(
            fields(value) | {"opinions": (opinion, value.opinions[1])}
        )
        == value
    )
    assert value.conflicts[0] == value.conflicts[1]
    other = AssessmentCondition(key="other", statement="Another condition.")
    basis = AssessmentBasis.model_validate(
        fields(value.basis) | {"conditions": (*value.basis.conditions, other)}
    )
    cross = SuppliedConditionOpinion.model_validate(
        fields(value.opinions[1]) | {"condition": other}
    )
    assert (
        SuppliedAssessment.model_validate(
            fields(value) | {"basis": basis, "opinions": (opinion, cross)}
        ).conflicts
        == value.conflicts
    )
    no_conflicts = SuppliedAssessment.model_validate(fields(value) | {"conflicts": ()})
    assert no_conflicts.conflicts == () and len(no_conflicts.opinions) == 2


@pytest.mark.parametrize(
    "position", ["stated", "unknown", "unsupported", "not_applicable"]
)
def test_positions_are_claims_and_overall_needs_no_conditions(position: str) -> None:
    wire = sample_wire()
    wire["opinions"][0]["position"] = position
    wire["opinions"][0]["statement"] = (
        "verified, observed, matched; do not execute this text"
    )
    value = SuppliedAssessment.model_validate_json(json.dumps(wire))
    assert value.opinions[0].position == position
    minimal = SuppliedAssessment(
        attribution=value.attribution,
        basis=AssessmentBasis(source=value.basis.source, target=value.basis.target),
        overall_opinion=SuppliedOverallOpinion(
            statement="Applicable.", attribution=value.attribution
        ),
    )
    assert (
        minimal.basis.conditions == minimal.opinions == ()
        and minimal.overall_opinion is not None
    )


@pytest.mark.parametrize(
    "value", ["", " ", "\t\n", "\ud800", "\udfff", "x" * 4097, 1, True]
)
def test_text_refuses_invalid_values(value: Any) -> None:
    with pytest.raises(ValidationError):
        AssessmentCondition(key="c", statement=value)


@pytest.mark.parametrize(
    "value",
    [
        "a\n",
        "\na",
        "x.a",
        "a!",
        "é",
        "a\x00",
        "A",
        "a" * 33,
        "a\ntrailing",
        "prefix a",
        "a suffix",
    ],
)
def test_key_full_string_grammar(value: str) -> None:
    with pytest.raises(ValidationError):
        AssessmentCondition(key=value, statement="x")


def test_text_keys_and_supplier_inclusive_bounds_preserve_admitted_codepoints() -> None:
    text = " \tMixed\nα\x1b\x7f\u202e\\ "
    value = AssessmentCondition(key="a" + "0" * 31, statement=text)
    assert value.statement == text
    assert AssessmentCondition.model_validate_json(value.model_dump_json()) == value
    assert len(AssessmentCondition(key="a", statement="x" * 4096).statement) == 4096
    assert len(AssessmentAttribution(supplier="x" * 128, rationale="r").supplier) == 128
    with pytest.raises(ValidationError) as failure:
        AssessmentAttribution(supplier="x" * 129, rationale="r")
    assert failure.value.errors()[0]["loc"] == ("supplier",)


CHILD_POSITIONS = (
    (AssessmentTarget, "snapshot"),
    (AssessmentTarget, "scope"),
    (AssessmentMaterial, "attribution"),
    (AssessmentMaterial, "record"),
    (AssessmentBasis, "source"),
    (AssessmentBasis, "target"),
    (AssessmentBasis, "conditions"),
    (AssessmentBasis, "materials"),
    (SuppliedConditionOpinion, "condition"),
    (SuppliedConditionOpinion, "attribution"),
    (SuppliedAssessmentConflict, "attribution"),
    (SuppliedOverallOpinion, "attribution"),
    (SuppliedAssessment, "attribution"),
    (SuppliedAssessment, "basis"),
    (SuppliedAssessment, "opinions"),
    (SuppliedAssessment, "conflicts"),
    (SuppliedAssessment, "overall_opinion"),
)


def child_data(
    model: type[BaseModel], field: str
) -> tuple[dict[str, Any], BaseModel, bool]:
    data = fields(examples()[model])
    if model is SuppliedAssessment:
        data = fields(SuppliedAssessment.model_validate_json(json.dumps(rich_wire())))
    if model is AssessmentTarget and field == "scope":
        data[field] = RepositorySnapshotDeclaredPathScope(
            snapshot=data["snapshot"], declared_paths=()
        )
    value = data[field]
    return (
        data,
        cast(tuple[BaseModel, ...], value)[0]
        if isinstance(value, tuple)
        else cast(BaseModel, value),
        isinstance(value, tuple),
    )


@pytest.mark.parametrize(("model", "field"), CHILD_POSITIONS)
@pytest.mark.parametrize("from_attributes", [False, True])
@pytest.mark.parametrize("kind", ["mapping", "lookalike"])
def test_python_child_guards_cannot_be_bypassed_by_attributes(
    model: type[BaseModel], field: str, from_attributes: bool, kind: str
) -> None:
    from types import SimpleNamespace

    data, child, sequence = child_data(model, field)
    assert model.model_validate(data)
    invalid = fields(child) if kind == "mapping" else SimpleNamespace(**fields(child))
    data[field] = (invalid, *data[field][1:]) if sequence else invalid
    with pytest.raises(ValidationError) as failure:
        model.model_validate(data, from_attributes=from_attributes)
    location = (field, 0) if sequence else (field,)
    assert failure.value.errors()[0]["loc"] == location
    assert "declared typed Python child" in failure.value.errors()[0]["msg"]


@pytest.mark.parametrize(("model", "field"), CHILD_POSITIONS)
def test_invalid_preconstructed_children_are_revalidated_at_owner(
    model: type[BaseModel], field: str
) -> None:
    data, child, sequence = child_data(model, field)
    first = next(iter(type(child).model_fields))
    broken = type(child).model_construct(**(fields(child) | {first: None}))
    data[field] = (broken, *data[field][1:]) if sequence else broken
    with pytest.raises(ValidationError) as failure:
        model.model_validate(data)
    prefix = (field, 0) if sequence else (field,)
    assert any(
        e["loc"][: len(prefix)] == prefix and first in e["loc"]
        for e in failure.value.errors()
    )


@pytest.mark.parametrize(
    ("model", "field"),
    [
        (AssessmentBasis, "conditions"),
        (AssessmentBasis, "materials"),
        (SuppliedConditionOpinion, "material_keys"),
        (SuppliedAssessment, "opinions"),
        (SuppliedAssessment, "conflicts"),
    ],
)
@pytest.mark.parametrize("container", ["list", "set", "generator", "string"])
def test_python_collection_language_is_strict(
    model: type[BaseModel], field: str, container: str
) -> None:
    value = examples()[model]
    if model is SuppliedAssessment:
        value = SuppliedAssessment.model_validate_json(json.dumps(rich_wire()))
    data = fields(value)
    old = data[field]
    invalid = {
        "list": lambda: list(old),
        "set": lambda: set(old),
        "generator": lambda: iter(old),
        "string": lambda: "not-a-tuple",
    }[container]()
    with pytest.raises(ValidationError) as failure:
        model.model_validate(data | {field: invalid})
    assert (
        failure.value.errors()[0]["loc"] == (field,)
        and failure.value.errors()[0]["type"] == "tuple_type"
    )
    assert model.model_validate_json(value.model_dump_json()) == value


def test_ordinary_subclass_and_nonempty_native_scope_preserve_owner_values() -> None:
    from faultatlas.domain.revision import GitRepositoryPath

    class Child(AssessmentCondition):
        pass

    value = typed_sample()
    condition = Child(key="once", statement=value.basis.conditions[0].statement)
    basis = AssessmentBasis.model_validate(
        fields(value.basis) | {"conditions": (condition,)}
    )
    assert type(basis.conditions[0]) is AssessmentCondition and basis == value.basis
    scope = RepositorySnapshotDeclaredPathScope(
        snapshot=basis.target.snapshot,
        declared_paths=(GitRepositoryPath("src/a.py"), GitRepositoryPath("src/β.py")),
    )
    target = AssessmentTarget.model_validate(fields(basis.target) | {"scope": scope})
    rooted = AssessmentBasis.model_validate(fields(basis) | {"target": target})
    assert AssessmentBasis.model_validate_json(rooted.model_dump_json()) == rooted


def normalized_counts(value: Any) -> tuple[int, int, int, int]:
    # Independent arithmetic over authored primitives, not constructor output.
    if isinstance(value, dict):
        child = [
            normalized_counts(x)
            for pair in cast(dict[str, Any], value).items()
            for x in pair
        ]
        return (
            1 + sum(x[0] for x in child),
            1 + sum(x[1] for x in child),
            sum(x[2] for x in child),
            1 + max((x[3] for x in child), default=0),
        )
    if isinstance(value, list):
        child = [normalized_counts(x) for x in cast(list[Any], value)]
        return (
            1 + sum(x[0] for x in child),
            sum(x[1] for x in child),
            sum(x[2] for x in child),
            1 + max((x[3] for x in child), default=0),
        )
    return 1, 0, len(value) if isinstance(value, str) else 0, 0


@pytest.mark.parametrize("budget", ["nodes", "objects", "strings", "depth"])
def test_private_budget_exact_limit_and_one_over_without_identity_dedup(
    budget: str,
) -> None:
    if budget == "nodes":
        valid = [0] * 8191
        invalid = [0] * 8192
    elif budget == "objects":
        same: dict[str, Any] = {}
        valid = [same] * 512
        invalid = [same] * 513
    elif budget == "strings":
        valid = {"k": "x" * 131071}
        invalid = {"kk": "x" * 131071}
    else:
        valid = 0
        for _ in range(32):
            valid = [valid]
        invalid = [valid]
    check_budget(valid)
    message = {
        "nodes": "node budget",
        "objects": "object budget",
        "strings": "string budget",
        "depth": "container depth",
    }[budget]
    with pytest.raises(ValueError, match=message):
        check_budget(invalid)


@pytest.mark.parametrize("root", ["basis", "assessment"])
def test_actual_root_normalized_string_bound_includes_defaults(root: str) -> None:
    wire = sample_wire()
    wire["opinions"] = []
    wire["basis"]["conditions"] = [
        {"key": f"c{i}", "statement": "x" * (3144 if i == 0 else 4096)}
        for i in range(32)
    ]
    data = wire["basis"] if root == "basis" else wire
    offset = 131072 - normalized_counts(data)[2]
    wire["basis"]["conditions"][0]["statement"] = "x" * (3144 + offset)
    assert len(wire["basis"]["conditions"][0]["statement"]) <= 4096
    assert normalized_counts(data)[2] == 131072
    model = AssessmentBasis if root == "basis" else SuppliedAssessment
    value = model.model_validate_json(json.dumps(data))
    assert value.model_dump(mode="json") == data
    wire["basis"]["conditions"][0]["statement"] += "x"
    with pytest.raises(ValidationError, match="normalized string budget") as failure:
        model.model_validate_json(json.dumps(data))
    assert failure.value.errors()[0]["loc"] == ()


def populated_wire() -> dict[str, Any]:
    wire = sample_wire()
    wire["basis"]["materials"] = [
        {
            "key": f"m{i}",
            "description": "x",
            "attribution": {"supplier": "s", "rationale": "r"},
            "record": None,
            "locator": None,
        }
        for i in range(128)
    ]
    opinion = wire["opinions"][0]
    wire["opinions"] = [copy.deepcopy(opinion) | {"key": f"o{i}"} for i in range(80)]
    snap = copy.deepcopy(wire["basis"]["target"]["snapshot"])
    wire["basis"]["target"]["scope"] = {"snapshot": snap, "declared_paths": []}
    return wire


def test_actual_assessment_object_budget_and_one_over() -> None:
    wire = populated_wire()
    # Exactly 509 records before adding one condition and an attributed overall.
    assert normalized_counts(wire)[1] == 509
    wire["basis"]["conditions"].append({"key": "other", "statement": "x"})
    wire["overall_opinion"] = {
        "statement": "x",
        "attribution": {"supplier": "s", "rationale": "r"},
    }
    assert normalized_counts(wire)[1] == 512
    value = SuppliedAssessment.model_validate_json(json.dumps(wire))
    assert value.model_dump(mode="json") == wire
    wire["basis"]["conditions"].append({"key": "third", "statement": "x"})
    with pytest.raises(ValidationError, match="normalized object budget") as failure:
        SuppliedAssessment.model_validate_json(json.dumps(wire))
    assert failure.value.errors()[0]["loc"] == ()


def test_actual_assessment_node_budget_and_one_over() -> None:
    wire = populated_wire()
    wire["basis"]["target"]["scope"]["declared_paths"] = [f"p{i}" for i in range(4096)]
    remainder = 8192 - normalized_counts(wire)[0]
    assert 0 < remainder <= 128 * len(wire["opinions"])
    for opinion in wire["opinions"]:
        count = min(remainder, 128)
        opinion["material_keys"] = [f"m{i}" for i in range(count)]
        remainder -= count
    assert (
        remainder == 0
        and normalized_counts(wire)[0] == 8192
        and normalized_counts(wire)[1] <= 512
    )
    value = SuppliedAssessment.model_validate_json(json.dumps(wire))
    assert value.model_dump(mode="json") == wire
    opinion = next(x for x in wire["opinions"] if not x["material_keys"])
    opinion["material_keys"] = ["m0"]
    with pytest.raises(ValidationError, match="normalized node budget") as failure:
        SuppliedAssessment.model_validate_json(json.dumps(wire))
    assert failure.value.errors()[0]["loc"] == ()


@pytest.mark.parametrize(
    "field", ["conditions", "materials", "opinions", "conflicts", "material_keys"]
)
@pytest.mark.parametrize("mode", ["python", "json"])
def test_local_collection_bounds_with_valid_prerequisites(
    field: str, mode: str
) -> None:
    wire = sample_wire()
    if field == "conditions":
        wire["basis"]["conditions"] = [
            wire["basis"]["conditions"][0],
            *({"key": f"c{i}", "statement": "x"} for i in range(63)),
        ]
        model = AssessmentBasis
        data = wire["basis"]
        maximum = 64
    elif field == "materials":
        wire["basis"]["materials"] = [
            {
                "key": f"m{i}",
                "description": "x",
                "attribution": {"supplier": "s", "rationale": "r"},
                "record": None,
                "locator": None,
            }
            for i in range(128)
        ]
        model = AssessmentBasis
        data = wire["basis"]
        maximum = 128
    elif field == "opinions":
        wire["opinions"] = [
            copy.deepcopy(wire["opinions"][0]) | {"key": f"o{i}"} for i in range(128)
        ]
        model = SuppliedAssessment
        data = wire
        maximum = 128
    elif field == "conflicts":
        wire = rich_wire()
        wire["conflicts"] = [copy.deepcopy(wire["conflicts"][0]) for _ in range(64)]
        model = SuppliedAssessment
        data = wire
        maximum = 64
    else:
        data = copy.deepcopy(wire["opinions"][0])
        data["material_keys"] = [f"m{i}" for i in range(128)]
        model = SuppliedConditionOpinion
        maximum = 128
    valid = model.model_validate_json(json.dumps(data))
    assert len(getattr(valid, field)) == maximum
    inputs = fields(valid)
    if mode == "python":
        collection = inputs[field]
        extra = collection[0]
        if field in ("conditions", "materials", "opinions"):
            extra = type(extra)(**(fields(extra) | {"key": "extra"}))
        elif field == "material_keys":
            extra = "extra"
        inputs[field] = (*collection, extra)
    else:
        extra = copy.deepcopy(data[field][0])
        if field in ("conditions", "materials", "opinions"):
            extra["key"] = "extra"
        elif field == "material_keys":
            extra = "extra"
        data[field].append(extra)
    with pytest.raises(ValidationError) as failure:
        if mode == "python":
            model.model_validate(inputs)
        else:
            model.model_validate_json(json.dumps(data))
    assert (
        failure.value.errors()[0]["loc"] == (field,)
        and failure.value.errors()[0]["type"] == "too_long"
    )


def test_reflexive_conflict_is_rejected_by_its_own_record() -> None:
    with pytest.raises(ValidationError, match="distinct opinion keys"):
        SuppliedAssessmentConflict(
            left_opinion_key="a",
            right_opinion_key="a",
            attribution=AssessmentAttribution(supplier="s", rationale="r"),
        )


def test_foreign_model_child_is_not_an_attribute_based_substitute() -> None:
    class Foreign(BaseModel):
        key: str
        statement: str

    value = typed_sample()
    data = fields(value.basis) | {
        "conditions": (
            Foreign(key="once", statement=value.basis.conditions[0].statement),
        )
    }
    with pytest.raises(ValidationError, match="declared typed Python child"):
        AssessmentBasis.model_validate(data, from_attributes=True)
