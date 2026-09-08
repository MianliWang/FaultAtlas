from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import uuid
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, ConfigDict, RootModel, ValidationError

import faultatlas
import faultatlas.domain
import faultatlas.domain.fault_test as test_module
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultOccurrenceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    FaultScenarioIdentity,
    SuppliedFaultReport,
)
from faultatlas.domain.fault_repair import FaultRepairCandidateIdentity
from faultatlas.domain.fault_test import (
    FaultTestMaterialIdentity,
    FaultTestRunIdentity,
    FaultTestRunRevisionAssociation,
    ReportedFaultTestComparison,
    ReportedFaultTestOutcome,
    ReportedFaultTestOutcomeKind,
    ReportedFaultTestRun,
    SuppliedFaultTestMaterial,
)
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)
from faultatlas.domain.revision import (
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectKind,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TEST_SOURCE = REPOSITORY_ROOT / "src/faultatlas/domain/fault_test.py"
CHECKOUT_SOURCE_ROOT = REPOSITORY_ROOT / "src"
ROADMAP = REPOSITORY_ROOT / "docs/roadmap.md"

# Every identifier and every piece of prose below is fixed synthetic supplied
# data. The retained pytest #4412 case supplies no test-material and no run
# identifier, so each is invented here, and no statement below is a historical
# quotation or a claim that FaultAtlas ran anything.
SUPPLIED_FAULT_TEXT = "12345678-1234-4234-8234-123456789abc"
SUPPLIED_FAULT = uuid.UUID(SUPPLIED_FAULT_TEXT)
SECOND_FAULT = uuid.UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")
SUPPLIED_REPORT_TEXT = "87654321-4321-4abc-8def-0123456789ab"
SUPPLIED_REPORT = uuid.UUID(SUPPLIED_REPORT_TEXT)
SECOND_REPORT = uuid.UUID("11111111-2222-4333-8444-555555555555")
SUPPLIED_MATERIAL_TEXT = "2b2b2b2b-3c3c-4d4d-8e8e-9f9f9f9f9f9f"
SUPPLIED_MATERIAL = uuid.UUID(SUPPLIED_MATERIAL_TEXT)
SECOND_MATERIAL = uuid.UUID("74747474-8585-4696-8a7a-b8b8b8b8b8b8")
SUPPLIED_RUN_TEXT = "0a0a0a0a-1b1b-4c2c-8d3d-4e4e4e4e4e4e"
SUPPLIED_RUN = uuid.UUID(SUPPLIED_RUN_TEXT)
SECOND_RUN_TEXT = "5f5f5f5f-6060-4171-8282-939393939393"
SECOND_RUN = uuid.UUID(SECOND_RUN_TEXT)
NIL_UUID = uuid.UUID("00000000-0000-0000-0000-000000000000")
MAX_UUID = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

# Fixed lexemes covering several UUID generation versions plus the two special
# values. None is generated during the run, and none carries an ordering, time,
# or generation-version promise in this contract.
ADMITTED_UUID_TEXT: tuple[tuple[str, int | None], ...] = (
    ("c232ab00-9414-11ec-b3c8-9e6bdeced846", 1),
    ("6fa459ea-ee8a-3ca4-894e-db77e160355e", 3),
    (SUPPLIED_MATERIAL_TEXT, 4),
    ("886313e1-3b8a-5372-9b90-0c9aee199e5d", 5),
    ("018f2c9e-1a2b-7c3d-8e4f-5a6b7c8d9e0f", 7),
    ("00000000-0000-8000-8000-00000000002a", 8),
    ("00000000-0000-0000-0000-000000000000", None),
    ("ffffffff-ffff-ffff-ffff-ffffffffffff", None),
)

RETAINED_PROVIDER = "github"
RETAINED_REPOSITORY_ID = "37489525"
OTHER_REPOSITORY_ID = "37489526"
RETAINED_HEAD_REVISION = "690a63b9218f72662cd3a67c6c200b758c88ce12"
RETAINED_BASE_REVISION = "4c9cde74ab40027b5761ab9e002af116a4a20df3"

PROBLEM_STATEMENT = "Instrumentation can change callback behavior."
BEHAVIORAL_DEVIATION = "The supplied transformed path invokes one callback twice."
SECOND_PROBLEM_STATEMENT = "A cached rewrite may be reused after the source changes."
SECOND_BEHAVIORAL_DEVIATION = "The supplied stale rewrite reports the wrong line."

TEST_STATEMENT = (
    "A regression test asserting the supplied callback is invoked exactly once."
)
SECOND_TEST_STATEMENT = (
    "A reduced reproduction script exercising the supplied rewrite path twice."
)
RUN_STATEMENT = "Reported as run from a local checkout by the reporting caller."
SECOND_RUN_STATEMENT = "Reported as run again by the caller after their edit."
OUTCOME_STATEMENT = "Reported as ending with the assertion the caller described."
SECOND_OUTCOME_STATEMENT = "Reported as ending without the described assertion."
COMPARISON_STATEMENT = (
    "The caller reports the two attempts of one test material for comparison."
)

MATERIAL_FIELDS = ("material", "report", "test_statement")
RUN_FIELDS = ("run", "test_material", "run_statement")
OUTCOME_FIELDS = ("run", "outcome", "outcome_statement")
RUN_REVISION_FIELDS = ("run", "revision")
COMPARISON_FIELDS = ("before", "after", "comparison_statement")
EXPECTED_EXPORTS = [
    "FaultTestMaterialIdentity",
    "SuppliedFaultTestMaterial",
    "FaultTestRunIdentity",
    "ReportedFaultTestRun",
    "ReportedFaultTestOutcomeKind",
    "ReportedFaultTestOutcome",
    "FaultTestRunRevisionAssociation",
    "ReportedFaultTestComparison",
]
EXPECTED_OUTCOME_MEMBERS = (
    ("PASSED", "passed"),
    ("FAILED", "failed"),
    ("ERRORED", "errored"),
    ("TIMED_OUT", "timed_out"),
    ("SKIPPED", "skipped"),
    ("DID_NOT_START", "did_not_start"),
    ("CANCELLED", "cancelled"),
)
TEXT_LIMIT = 4096

# Nothing here executes anything and nothing here judges anything. None of
# these may become a field of any published model in this module: each names an
# authority this Slice does not have, a parsed sub-structure it refuses to
# create, or a state its vocabulary deliberately omits.
FORBIDDEN_TEST_IDENTIFIERS = (
    "acquisition_run",
    "applied",
    "approved",
    "architecture",
    "cause",
    "certainty",
    "command",
    "confidence",
    "correct",
    "correctness",
    "dependency_version",
    "deployed",
    "duration",
    "elapsed",
    "environment",
    "evidence",
    "evidence_record",
    "executed",
    "execution",
    "expected_property",
    "fail_to_pass",
    "finished_at",
    "fixed",
    "fixes",
    "flaky",
    "hypothesis",
    "independent",
    "machine",
    "observed",
    "occurrence",
    "operating_system",
    "outcome_time",
    "platform",
    "proof",
    "proves",
    "regression_free",
    "regression_safe",
    "repair_candidate",
    "repair_success",
    "review",
    "reviewed",
    "root_cause",
    "runtime_version",
    "scenario",
    "source",
    "started_at",
    "status",
    "strength",
    "support",
    "timestamp",
    "unknown",
    "verdict",
    "verification",
    "verified",
    "witnessed",
    "workflow_run",
)
REFUSED_EXTRA_KEYS = (*FORBIDDEN_TEST_IDENTIFIERS, "schema_version")

# The five other UUID-rooted `S1.P06` identities. A material identity and a run
# identity are a sixth and a seventh, and all seven must stay distinct on one
# shared scalar.
PREDECESSOR_UUID_IDENTITIES: tuple[type[RootModel[uuid.UUID]], ...] = (
    FaultInstanceIdentity,
    FaultReportIdentity,
    FaultScenarioIdentity,
    FaultOccurrenceIdentity,
    FaultRepairCandidateIdentity,
)


def _repository(identifier: str = RETAINED_REPOSITORY_ID) -> RepositoryIdentity:
    return RepositoryIdentity(
        provider=ProviderKey(RETAINED_PROVIDER),
        provider_repository_id=ProviderRepositoryId(identifier),
    )


def _context(
    fault: uuid.UUID = SUPPLIED_FAULT,
    repository: str = RETAINED_REPOSITORY_ID,
) -> FaultRepositoryContext:
    return FaultRepositoryContext(
        fault=FaultInstanceIdentity(fault),
        repository=_repository(repository),
    )


def _report(
    report: uuid.UUID = SUPPLIED_REPORT,
    fault: uuid.UUID = SUPPLIED_FAULT,
    repository: str = RETAINED_REPOSITORY_ID,
    problem_statement: str = PROBLEM_STATEMENT,
    behavioral_deviation: str = BEHAVIORAL_DEVIATION,
) -> SuppliedFaultReport:
    return SuppliedFaultReport(
        report=FaultReportIdentity(report),
        context=_context(fault, repository),
        problem_statement=problem_statement,
        behavioral_deviation=behavioral_deviation,
    )


def _second_report() -> SuppliedFaultReport:
    return _report(
        report=SECOND_REPORT,
        fault=SECOND_FAULT,
        problem_statement=SECOND_PROBLEM_STATEMENT,
        behavioral_deviation=SECOND_BEHAVIORAL_DEVIATION,
    )


def _material_identity(
    value: uuid.UUID = SUPPLIED_MATERIAL,
) -> FaultTestMaterialIdentity:
    return FaultTestMaterialIdentity(value)


def _run_identity(value: uuid.UUID = SUPPLIED_RUN) -> FaultTestRunIdentity:
    return FaultTestRunIdentity(value)


def _material(
    material: uuid.UUID = SUPPLIED_MATERIAL,
    report: SuppliedFaultReport | None = None,
    test_statement: str = TEST_STATEMENT,
) -> SuppliedFaultTestMaterial:
    return SuppliedFaultTestMaterial(
        material=_material_identity(material),
        report=_report() if report is None else report,
        test_statement=test_statement,
    )


def _run(
    run: uuid.UUID = SUPPLIED_RUN,
    test_material: SuppliedFaultTestMaterial | None = None,
    run_statement: str = RUN_STATEMENT,
) -> ReportedFaultTestRun:
    return ReportedFaultTestRun(
        run=_run_identity(run),
        test_material=_material() if test_material is None else test_material,
        run_statement=run_statement,
    )


def _outcome(
    run: ReportedFaultTestRun | None = None,
    outcome: ReportedFaultTestOutcomeKind = ReportedFaultTestOutcomeKind.FAILED,
    outcome_statement: str = OUTCOME_STATEMENT,
) -> ReportedFaultTestOutcome:
    return ReportedFaultTestOutcome(
        run=_run() if run is None else run,
        outcome=outcome,
        outcome_statement=outcome_statement,
    )


def _commit(full_digest: str = RETAINED_HEAD_REVISION) -> GitCommitIdentity:
    return GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=full_digest,
    )


def _run_revision(
    run: ReportedFaultTestRun | None = None,
    revision: GitCommitIdentity | None = None,
) -> FaultTestRunRevisionAssociation:
    return FaultTestRunRevisionAssociation(
        run=_run() if run is None else run,
        revision=_commit() if revision is None else revision,
    )


def _comparison(
    before: ReportedFaultTestOutcomeKind = ReportedFaultTestOutcomeKind.FAILED,
    after: ReportedFaultTestOutcomeKind = ReportedFaultTestOutcomeKind.PASSED,
    material: SuppliedFaultTestMaterial | None = None,
    comparison_statement: str = COMPARISON_STATEMENT,
) -> ReportedFaultTestComparison:
    """One material, two distinct runs, and the two roles supplied by a caller."""
    shared = _material() if material is None else material
    return ReportedFaultTestComparison(
        before=_outcome(
            run=_run(SUPPLIED_RUN, shared, RUN_STATEMENT),
            outcome=before,
            outcome_statement=OUTCOME_STATEMENT,
        ),
        after=_outcome(
            run=_run(SECOND_RUN, shared, SECOND_RUN_STATEMENT),
            outcome=after,
            outcome_statement=SECOND_OUTCOME_STATEMENT,
        ),
        comparison_statement=comparison_statement,
    )


def _typed_material_mapping(**overrides: object) -> dict[str, Any]:
    mapping: dict[str, Any] = {
        "material": _material_identity(),
        "report": _report(),
        "test_statement": TEST_STATEMENT,
    }
    mapping.update(overrides)
    return mapping


def _typed_run_mapping(**overrides: object) -> dict[str, Any]:
    mapping: dict[str, Any] = {
        "run": _run_identity(),
        "test_material": _material(),
        "run_statement": RUN_STATEMENT,
    }
    mapping.update(overrides)
    return mapping


def _typed_outcome_mapping(**overrides: object) -> dict[str, Any]:
    mapping: dict[str, Any] = {
        "run": _run(),
        "outcome": ReportedFaultTestOutcomeKind.FAILED,
        "outcome_statement": OUTCOME_STATEMENT,
    }
    mapping.update(overrides)
    return mapping


def _typed_run_revision_mapping(**overrides: object) -> dict[str, Any]:
    mapping: dict[str, Any] = {"run": _run(), "revision": _commit()}
    mapping.update(overrides)
    return mapping


def _typed_comparison_mapping(**overrides: object) -> dict[str, Any]:
    comparison = _comparison()
    mapping: dict[str, Any] = {
        "before": comparison.before,
        "after": comparison.after,
        "comparison_statement": COMPARISON_STATEMENT,
    }
    mapping.update(overrides)
    return mapping


def _payload(value: BaseModel) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(value.model_dump_json()))


def _failures(error: ValidationError) -> tuple[tuple[tuple[str | int, ...], str], ...]:
    return tuple((detail["loc"], detail["type"]) for detail in error.errors())


def _paths(error: ValidationError) -> tuple[tuple[str | int, ...], ...]:
    return tuple(detail["loc"] for detail in error.errors())


def _distinct_value_count(*values: object) -> int:
    return len({cast(Any, value) for value in values})


def _test_tree() -> ast.Module:
    return ast.parse(TEST_SOURCE.read_bytes(), filename=TEST_SOURCE.name)


def _roadmap() -> str:
    return " ".join(ROADMAP.read_text(encoding="utf-8").split())


def _published_models() -> tuple[type[BaseModel], ...]:
    return (
        SuppliedFaultTestMaterial,
        ReportedFaultTestRun,
        ReportedFaultTestOutcome,
        FaultTestRunRevisionAssociation,
        ReportedFaultTestComparison,
    )


# --- foreign, lookalike and subclass carriers --------------------------------


class ForeignUuidRoot(RootModel[uuid.UUID]):
    """A different published-shaped model over the same scalar content."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class ForeignSuppliedFaultTestMaterial(BaseModel):
    """A structurally identical record that is not the published type."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    material: FaultTestMaterialIdentity
    report: SuppliedFaultReport
    test_statement: str


class MaterialLookalike:
    """An attribute-backed object carrying the published field names."""

    def __init__(self) -> None:
        self.material = _material_identity()
        self.report = _report()
        self.test_statement = TEST_STATEMENT


class UntypedChildMaterialLookalike:
    """An attribute-backed top-level object whose report child is untyped."""

    def __init__(self) -> None:
        self.material = _material_identity()
        self.report = _report().model_dump()
        self.test_statement = TEST_STATEMENT


class RunLookalike:
    """An attribute-backed object carrying a reported run's field names."""

    def __init__(self) -> None:
        self.run = _run_identity()
        self.test_material = _material()
        self.run_statement = RUN_STATEMENT


class RevisionLookalike:
    """An attribute-backed object carrying a commit identity's field names."""

    def __init__(self) -> None:
        self.kind = GitObjectKind.COMMIT
        self.algorithm = GitHashAlgorithm.SHA1
        self.full_digest = RETAINED_HEAD_REVISION


class UnextendedFaultTestRunIdentity(FaultTestRunIdentity):
    """An ordinary identity subclass that adds no field."""


class UnextendedReportedFaultTestRun(ReportedFaultTestRun):
    """An ordinary reported-run subclass that adds no field."""


class ExtendedReportedFaultTestRun(ReportedFaultTestRun):
    """A reported-run subclass that adds a field the base schema forbids."""

    note: str = "supplied"


class SuppliedText(str):
    """A str subclass carrying an ordinary value."""


# --- the two new identities ---------------------------------------------------


@pytest.mark.parametrize(
    ("identity", "supplied"),
    (
        pytest.param(FaultTestMaterialIdentity, SUPPLIED_MATERIAL, id="material"),
        pytest.param(FaultTestRunIdentity, SUPPLIED_RUN, id="run"),
    ),
)
def test_each_identity_accepts_a_supplied_uuid_through_every_entry_path(
    identity: type[RootModel[uuid.UUID]],
    supplied: uuid.UUID,
) -> None:
    positional = identity(supplied)

    assert positional.root == supplied
    assert identity(root=supplied) == positional
    assert identity.model_validate(supplied) == positional
    assert identity.model_validate(positional) == positional
    # A root model is the scalar, not a one-key record over it.
    with pytest.raises(ValidationError):
        identity.model_validate({"root": supplied})


@pytest.mark.parametrize(
    "identity",
    (FaultTestMaterialIdentity, FaultTestRunIdentity),
    ids=("material", "run"),
)
@pytest.mark.parametrize(("text", "version"), ADMITTED_UUID_TEXT)
def test_each_identity_admits_every_uuid_the_locked_validator_admits(
    identity: type[RootModel[uuid.UUID]],
    text: str,
    version: int | None,
) -> None:
    """Nil, Max and every generation version are ordinary admitted values."""
    supplied = uuid.UUID(text)
    assert supplied.version == version

    value = identity(supplied)

    assert value.root == supplied
    assert json.loads(value.model_dump_json()) == text
    assert identity.model_validate_json(json.dumps(text)) == value


@pytest.mark.parametrize(
    "identity",
    (FaultTestMaterialIdentity, FaultTestRunIdentity),
    ids=("material", "run"),
)
@pytest.mark.parametrize(
    "supplied",
    (
        SUPPLIED_MATERIAL_TEXT,
        SUPPLIED_MATERIAL.bytes,
        SUPPLIED_MATERIAL.int,
        None,
        1,
        1.0,
        ["12345678-1234-4234-8234-123456789abc"],
    ),
)
def test_each_identity_refuses_untyped_python_input(
    identity: type[RootModel[uuid.UUID]],
    supplied: object,
) -> None:
    with pytest.raises(ValidationError):
        identity(cast(Any, supplied))


@pytest.mark.parametrize(
    ("identity", "text"),
    (
        pytest.param(FaultTestMaterialIdentity, SUPPLIED_MATERIAL_TEXT, id="material"),
        pytest.param(FaultTestRunIdentity, SUPPLIED_RUN_TEXT, id="run"),
    ),
)
def test_each_identity_accepts_uuid_text_in_json_and_round_trips_as_a_scalar(
    identity: type[RootModel[uuid.UUID]],
    text: str,
) -> None:
    """The JSON form is the bare UUID string, with no wrapper and no adapter."""
    decoded = identity.model_validate_json(json.dumps(text))

    assert decoded.root == uuid.UUID(text)
    assert json.loads(decoded.model_dump_json()) == text
    assert identity.model_validate_json(decoded.model_dump_json()) == decoded


@pytest.mark.parametrize(
    "identity",
    (FaultTestMaterialIdentity, FaultTestRunIdentity),
    ids=("material", "run"),
)
@pytest.mark.parametrize(
    "wrapper",
    (
        {"root": SUPPLIED_MATERIAL_TEXT},
        {"value": SUPPLIED_MATERIAL_TEXT},
        {"uuid": SUPPLIED_MATERIAL_TEXT},
    ),
)
def test_no_wrapper_object_json_form_is_published(
    identity: type[RootModel[uuid.UUID]],
    wrapper: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        identity.model_validate_json(json.dumps(wrapper))


@pytest.mark.parametrize(
    "identity",
    (FaultTestMaterialIdentity, FaultTestRunIdentity),
    ids=("material", "run"),
)
def test_each_identity_declares_the_published_value_profile(
    identity: type[RootModel[uuid.UUID]],
) -> None:
    assert identity.model_config == {
        "frozen": True,
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }


@pytest.mark.parametrize(
    ("identity", "supplied"),
    (
        pytest.param(FaultTestMaterialIdentity, SUPPLIED_MATERIAL, id="material"),
        pytest.param(FaultTestRunIdentity, SUPPLIED_RUN, id="run"),
    ),
)
def test_each_identity_is_frozen_and_allocates_nothing(
    identity: type[RootModel[uuid.UUID]],
    supplied: uuid.UUID,
) -> None:
    value = identity(supplied)

    with pytest.raises(ValidationError):
        value.root = supplied
    assert identity(supplied).root == supplied
    assert identity(supplied) == value


def test_neither_identity_is_a_subclass_or_alias_of_the_other_or_a_predecessor() -> (
    None
):
    for identity in (FaultTestMaterialIdentity, FaultTestRunIdentity):
        for other in (*PREDECESSOR_UUID_IDENTITIES, FaultTestMaterialIdentity):
            if other is identity:
                continue
            assert not issubclass(identity, other)
            assert not issubclass(other, identity)
            assert identity is not other
    assert not issubclass(FaultTestRunIdentity, FaultTestMaterialIdentity)
    assert not issubclass(FaultTestMaterialIdentity, FaultTestRunIdentity)


@pytest.mark.parametrize("shared", (SUPPLIED_FAULT, NIL_UUID, MAX_UUID))
def test_all_seven_p06_identities_stay_distinct_on_one_shared_scalar(
    shared: uuid.UUID,
) -> None:
    """Seven names over one scalar are seven values, not one."""
    values = [
        identity(shared)
        for identity in (
            *PREDECESSOR_UUID_IDENTITIES,
            FaultTestMaterialIdentity,
            FaultTestRunIdentity,
        )
    ]

    assert len(values) == 7
    assert _distinct_value_count(*values) == 7
    for value in values:
        assert value.root == shared
    assert len({json.loads(value.model_dump_json()) for value in values}) == 1


def test_a_run_identity_is_not_an_acquisition_run() -> None:
    """The `S1.P03` acquisition vocabulary is not imported, aliased, or reused."""
    source = TEST_SOURCE.read_text(encoding="utf-8")
    imported = {
        alias.name if isinstance(node, ast.Import) else cast(str, node.module)
        for node in ast.walk(_test_tree())
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    }

    assert "faultatlas.domain.source" not in imported
    # The prose says the acquisition vocabulary is excluded; the executable
    # body below the module docstring must not name it at all.
    body = source.split('"""', 2)[-1]
    for forbidden in ("AcquisitionRunId", "AcquisitionRun", "acquisition_run"):
        assert forbidden not in body, forbidden
    assert "not an acquisition run" in " ".join(source.split())


@pytest.mark.parametrize(
    ("identity", "supplied"),
    (
        pytest.param(FaultTestMaterialIdentity, SUPPLIED_MATERIAL, id="material"),
        pytest.param(FaultTestRunIdentity, SUPPLIED_RUN, id="run"),
    ),
)
def test_a_foreign_uuid_root_model_is_not_a_published_identity(
    identity: type[RootModel[uuid.UUID]],
    supplied: uuid.UUID,
) -> None:
    foreign = ForeignUuidRoot(supplied)

    assert foreign.root == identity(supplied).root
    assert foreign != identity(supplied)
    with pytest.raises(ValidationError):
        identity.model_validate(foreign)


@pytest.mark.parametrize(
    ("identity", "supplied"),
    (
        pytest.param(FaultTestMaterialIdentity, SUPPLIED_MATERIAL, id="material"),
        pytest.param(FaultTestRunIdentity, SUPPLIED_RUN, id="run"),
    ),
)
def test_equal_identities_hash_equally_and_carry_no_ordering(
    identity: type[RootModel[uuid.UUID]],
    supplied: uuid.UUID,
) -> None:
    first = identity(supplied)
    second = identity(supplied)

    assert first == second
    assert hash(first) == hash(second)
    assert _distinct_value_count(first, second) == 1
    with pytest.raises(TypeError):
        _ = first < second  # type: ignore[operator]


# --- the five published records: shape, profile and round trip -----------------


@pytest.mark.parametrize(
    ("model", "fields"),
    (
        pytest.param(SuppliedFaultTestMaterial, MATERIAL_FIELDS, id="material"),
        pytest.param(ReportedFaultTestRun, RUN_FIELDS, id="run"),
        pytest.param(ReportedFaultTestOutcome, OUTCOME_FIELDS, id="outcome"),
        pytest.param(
            FaultTestRunRevisionAssociation, RUN_REVISION_FIELDS, id="run-revision"
        ),
        pytest.param(ReportedFaultTestComparison, COMPARISON_FIELDS, id="comparison"),
    ),
)
def test_each_record_declares_exactly_its_fields_in_order(
    model: type[BaseModel],
    fields: tuple[str, ...],
) -> None:
    assert tuple(model.model_fields) == fields


@pytest.mark.parametrize("model", _published_models(), ids=lambda m: m.__name__)
def test_each_record_declares_the_published_value_profile(
    model: type[BaseModel],
) -> None:
    assert model.model_config == {
        "frozen": True,
        "extra": "forbid",
        "strict": True,
        "revalidate_instances": "always",
        "validate_default": True,
    }


@pytest.mark.parametrize(
    ("value", "keys"),
    (
        pytest.param(_material(), MATERIAL_FIELDS, id="material"),
        pytest.param(_run(), RUN_FIELDS, id="run"),
        pytest.param(_outcome(), OUTCOME_FIELDS, id="outcome"),
        pytest.param(_run_revision(), RUN_REVISION_FIELDS, id="run-revision"),
        pytest.param(_comparison(), COMPARISON_FIELDS, id="comparison"),
    ),
)
def test_each_json_payload_carries_exactly_the_declared_keys(
    value: BaseModel,
    keys: tuple[str, ...],
) -> None:
    assert tuple(_payload(value)) == keys


@pytest.mark.parametrize(
    ("value", "model"),
    (
        pytest.param(_material(), SuppliedFaultTestMaterial, id="material"),
        pytest.param(_run(), ReportedFaultTestRun, id="run"),
        pytest.param(_outcome(), ReportedFaultTestOutcome, id="outcome"),
        pytest.param(
            _run_revision(), FaultTestRunRevisionAssociation, id="run-revision"
        ),
        pytest.param(_comparison(), ReportedFaultTestComparison, id="comparison"),
    ),
)
def test_each_record_round_trips_through_json(
    value: BaseModel,
    model: type[BaseModel],
) -> None:
    assert model.model_validate_json(value.model_dump_json()) == value


@pytest.mark.parametrize(
    ("value", "model", "first"),
    (
        pytest.param(_material(), SuppliedFaultTestMaterial, "material", id="material"),
        pytest.param(_run(), ReportedFaultTestRun, "run", id="run"),
        pytest.param(_outcome(), ReportedFaultTestOutcome, "run", id="outcome"),
        pytest.param(
            _run_revision(), FaultTestRunRevisionAssociation, "run", id="run-revision"
        ),
        pytest.param(
            _comparison(), ReportedFaultTestComparison, "before", id="comparison"
        ),
    ),
)
def test_each_record_refuses_its_own_python_dump(
    value: BaseModel,
    model: type[BaseModel],
    first: str,
) -> None:
    """Python and JSON are different input languages, deliberately."""
    with pytest.raises(ValidationError) as failure:
        model.model_validate(value.model_dump())

    assert _paths(failure.value)[0] == (first,)


@pytest.mark.parametrize(
    ("value", "model"),
    (
        pytest.param(_material(), SuppliedFaultTestMaterial, id="material"),
        pytest.param(_run(), ReportedFaultTestRun, id="run"),
        pytest.param(_outcome(), ReportedFaultTestOutcome, id="outcome"),
        pytest.param(
            _run_revision(), FaultTestRunRevisionAssociation, id="run-revision"
        ),
        pytest.param(_comparison(), ReportedFaultTestComparison, id="comparison"),
    ),
)
def test_each_record_accepts_its_own_typed_instance(
    value: BaseModel,
    model: type[BaseModel],
) -> None:
    assert model.model_validate(value) == value


@pytest.mark.parametrize(
    ("model", "fields"),
    (
        pytest.param(SuppliedFaultTestMaterial, MATERIAL_FIELDS, id="material"),
        pytest.param(ReportedFaultTestRun, RUN_FIELDS, id="run"),
        pytest.param(ReportedFaultTestOutcome, OUTCOME_FIELDS, id="outcome"),
        pytest.param(
            FaultTestRunRevisionAssociation, RUN_REVISION_FIELDS, id="run-revision"
        ),
        pytest.param(ReportedFaultTestComparison, COMPARISON_FIELDS, id="comparison"),
    ),
)
def test_no_record_declares_a_forbidden_field(
    model: type[BaseModel],
    fields: tuple[str, ...],
) -> None:
    for forbidden in FORBIDDEN_TEST_IDENTIFIERS:
        assert forbidden not in model.model_fields, (model.__name__, forbidden)
    assert set(model.model_fields) == set(fields)


@pytest.mark.parametrize(
    "value",
    (_material(), _run(), _outcome(), _run_revision(), _comparison()),
    ids=("material", "run", "outcome", "run-revision", "comparison"),
)
def test_no_record_json_payload_carries_a_forbidden_key(value: BaseModel) -> None:
    text = value.model_dump_json()

    for forbidden in FORBIDDEN_TEST_IDENTIFIERS:
        assert f'"{forbidden}":' not in text, forbidden


# --- supplied test material ----------------------------------------------------


def test_test_material_is_built_from_already_typed_values() -> None:
    material = _material()

    assert material.material == _material_identity()
    assert material.report == _report()
    assert material.test_statement == TEST_STATEMENT
    # The fault subject stays reachable without being restated here.
    assert material.report.context.fault == FaultInstanceIdentity(SUPPLIED_FAULT)


def test_test_material_needs_no_run_outcome_scenario_or_candidate() -> None:
    """Material may be described long before anyone reports running it."""
    material = _material()

    assert set(SuppliedFaultTestMaterial.model_fields) == set(MATERIAL_FIELDS)
    for absent in ("run", "outcome", "scenario", "occurrence", "repair_candidate"):
        assert absent not in SuppliedFaultTestMaterial.model_fields, absent
    assert _payload(material) == {
        "material": SUPPLIED_MATERIAL_TEXT,
        "report": _payload(_report()),
        "test_statement": TEST_STATEMENT,
    }


@pytest.mark.parametrize(
    "statement",
    (
        "A regression test in the analyzed repository.",
        "A reduced reproduction the caller wrote by hand.",
        "A manual procedure with no automation at all.",
        "A test command concept, not a command line.",
        "A property-oriented check over the described input.",
    ),
)
def test_any_kind_of_material_is_described_by_one_opaque_statement(
    statement: str,
) -> None:
    """Nothing classifies what kind of material the prose describes."""
    material = _material(test_statement=statement)

    assert material.test_statement == statement
    assert tuple(SuppliedFaultTestMaterial.model_fields) == MATERIAL_FIELDS


def test_test_material_creates_no_source_or_evidence_field() -> None:
    """A knowledge object about a procedure is not captured code."""
    for absent in ("source", "evidence", "evidence_record", "locator", "bytes"):
        assert absent not in SuppliedFaultTestMaterial.model_fields, absent
    text = _material().model_dump_json()
    assert "sha256" not in text
    assert "byte_length" not in text


def test_one_report_may_carry_several_test_materials() -> None:
    first = _material()
    second = _material(material=SECOND_MATERIAL, test_statement=SECOND_TEST_STATEMENT)

    assert first.report == second.report
    assert first != second
    assert _distinct_value_count(first, second) == 2


def test_one_test_material_identity_across_two_reports_stays_two_values() -> None:
    """Sharing an identity scalar merges nothing: the whole record differs."""
    first = _material()
    second = _material(report=_second_report())

    assert first.material == second.material
    assert first != second


# --- the reported run ----------------------------------------------------------


def test_a_reported_run_consumes_its_test_material_whole() -> None:
    run = _run()

    assert run.run == _run_identity()
    assert run.test_material == _material()
    assert run.run_statement == RUN_STATEMENT
    assert run.test_material.report.context.fault == FaultInstanceIdentity(
        SUPPLIED_FAULT
    )


def test_a_reported_run_carries_no_outcome_and_no_time() -> None:
    """A reported attempt and a reported disposition are separate knowledge."""
    for absent in (
        "outcome",
        "outcome_statement",
        "started_at",
        "finished_at",
        "duration",
        "timestamp",
    ):
        assert absent not in ReportedFaultTestRun.model_fields, absent
    assert tuple(_payload(_run())) == RUN_FIELDS


def test_the_run_statement_is_not_parsed_into_environment_fields() -> None:
    """Describing an invocation is deliberately not structuring it."""
    supplied = (
        "Reported as run on the caller's laptop with python 3.13 and "
        "pytest 8, via `pytest -k rewrite`, on linux/x86_64."
    )
    run = _run(run_statement=supplied)

    assert run.run_statement == supplied
    for absent in (
        "operating_system",
        "platform",
        "architecture",
        "environment",
        "command",
        "dependency_version",
        "runtime_version",
    ):
        assert absent not in ReportedFaultTestRun.model_fields, absent


def test_one_test_material_may_carry_several_reported_runs() -> None:
    shared = _material()
    first = _run(SUPPLIED_RUN, shared)
    second = _run(SECOND_RUN, shared, SECOND_RUN_STATEMENT)

    assert first.test_material == second.test_material == shared
    assert first != second
    assert _distinct_value_count(first, second) == 2


def test_identical_run_prose_does_not_merge_two_reported_runs() -> None:
    shared = _material()
    first = _run(SUPPLIED_RUN, shared, RUN_STATEMENT)
    second = _run(SECOND_RUN, shared, RUN_STATEMENT)

    assert first.run_statement == second.run_statement
    assert first != second


def test_a_reported_run_is_not_a_faultatlas_execution() -> None:
    """The module starts no process and describes the claim as reported."""
    prose = " ".join(TEST_SOURCE.read_text(encoding="utf-8").split())

    assert "Everything here is caller-reported." in prose
    assert "FaultAtlas executes no analyzed repository in this Slice" in prose
    body = TEST_SOURCE.read_text(encoding="utf-8").split('"""', 2)[-1]
    for forbidden in ("subprocess", "os.system", "Popen", "shutil"):
        assert forbidden not in body, forbidden


# --- the reported outcome vocabulary -------------------------------------------


def test_the_outcome_vocabulary_publishes_exactly_seven_members_in_order() -> None:
    assert (
        tuple((member.name, member.value) for member in ReportedFaultTestOutcomeKind)
        == EXPECTED_OUTCOME_MEMBERS
    )
    assert len(ReportedFaultTestOutcomeKind) == 7


@pytest.mark.parametrize(
    "absent",
    (
        "unknown",
        "flaky",
        "regression_safe",
        "fixed",
        "verified",
        "pending",
        "not_run",
        "inconclusive",
    ),
)
def test_the_outcome_vocabulary_publishes_no_interpretive_member(absent: str) -> None:
    values = {member.value for member in ReportedFaultTestOutcomeKind}
    names = {member.name for member in ReportedFaultTestOutcomeKind}

    assert absent not in values
    assert absent.upper() not in names


def test_the_outcome_vocabulary_is_a_str_enum_with_stable_lexemes() -> None:
    for member in ReportedFaultTestOutcomeKind:
        assert isinstance(member, str)
        assert member.value == member.value.strip().lower()
        assert ReportedFaultTestOutcomeKind(member.value) is member


@pytest.mark.parametrize("supplied", ("Passed", "PASSED", "pass", "fail", "", " "))
def test_an_unlisted_outcome_lexeme_is_refused(supplied: str) -> None:
    with pytest.raises(ValueError, match="is not a valid"):
        ReportedFaultTestOutcomeKind(supplied)


def test_did_not_start_is_not_failed_and_neither_is_errored_or_timed_out() -> None:
    """Four dispositions this layer refuses to flatten into one."""
    distinct = (
        ReportedFaultTestOutcomeKind.FAILED,
        ReportedFaultTestOutcomeKind.DID_NOT_START,
        ReportedFaultTestOutcomeKind.ERRORED,
        ReportedFaultTestOutcomeKind.TIMED_OUT,
    )

    assert _distinct_value_count(*distinct) == 4
    assert _distinct_value_count(*(member.value for member in distinct)) == 4


# --- the reported outcome ------------------------------------------------------


@pytest.mark.parametrize("kind", tuple(ReportedFaultTestOutcomeKind))
def test_every_vocabulary_member_is_admitted_and_serializes_as_its_lexeme(
    kind: ReportedFaultTestOutcomeKind,
) -> None:
    outcome = _outcome(outcome=kind)

    assert outcome.outcome is kind
    assert _payload(outcome)["outcome"] == kind.value
    assert (
        ReportedFaultTestOutcome.model_validate_json(outcome.model_dump_json())
        == outcome
    )


def test_an_outcome_carries_no_evidence_confidence_or_review_field() -> None:
    for absent in (
        "evidence",
        "evidence_record",
        "confidence",
        "certainty",
        "review",
        "reviewed",
        "verified",
        "witnessed",
        "correctness",
    ):
        assert absent not in ReportedFaultTestOutcome.model_fields, absent


def test_two_outcomes_may_name_one_run_and_disagree() -> None:
    """This layer has no aggregate authority and neither resolves nor flags it."""
    run = _run()
    passed = _outcome(run=run, outcome=ReportedFaultTestOutcomeKind.PASSED)
    failed = _outcome(run=run, outcome=ReportedFaultTestOutcomeKind.FAILED)

    assert passed.run == failed.run
    assert passed.outcome is not failed.outcome
    assert _distinct_value_count(passed, failed) == 2


def test_an_absent_outcome_record_is_not_a_disposition() -> None:
    """A run with no outcome record reports nothing about how it ended."""
    run = _run()

    assert "outcome" not in ReportedFaultTestRun.model_fields
    assert "outcome" not in _payload(run)
    for kind in ReportedFaultTestOutcomeKind:
        assert kind.value not in run.model_dump_json()
    # No boolean, sentinel or None stands in for a missing disposition.
    assert None not in run.model_dump().values()


def test_an_outcome_is_not_a_faultatlas_observation() -> None:
    prose = " ".join(TEST_SOURCE.read_text(encoding="utf-8").split())

    assert "It does not mean that FaultAtlas witnessed the run" in prose
    assert "must be a distinct value rather than a silent reuse of these" in prose


# --- the run-revision association ----------------------------------------------


def test_a_run_revision_association_reuses_the_commit_identity_whole() -> None:
    association = _run_revision()

    assert association.run == _run()
    assert association.revision == _commit()
    assert _payload(association)["revision"] == _payload(_commit())


def test_a_run_revision_association_claims_no_membership_role_or_correctness() -> None:
    for absent in (
        "repository",
        "reachable",
        "role",
        "base",
        "head",
        "merge",
        "repair_candidate",
        "before",
        "after",
        "applied",
        "deployed",
        "correct",
    ):
        assert absent not in FaultTestRunRevisionAssociation.model_fields, absent
    assert tuple(FaultTestRunRevisionAssociation.model_fields) == RUN_REVISION_FIELDS


def test_a_revision_unrelated_to_the_reports_repository_is_admitted() -> None:
    """No membership is claimed, so no membership can be checked here."""
    material = _material(report=_report(repository=OTHER_REPOSITORY_ID))
    association = _run_revision(run=_run(test_material=material))

    assert association.revision == _commit()
    assert association.run.test_material.report.context.repository == _repository(
        OTHER_REPOSITORY_ID
    )


def test_a_run_may_carry_no_revision_association_at_all() -> None:
    """An unavailable revision is an absent association, not a `None` field."""
    run = _run()

    assert "revision" not in ReportedFaultTestRun.model_fields
    assert "revision" not in _payload(run)
    assert None not in run.model_dump().values()


def test_a_run_may_carry_several_revision_associations() -> None:
    run = _run()
    first = _run_revision(run=run, revision=_commit(RETAINED_HEAD_REVISION))
    second = _run_revision(run=run, revision=_commit(RETAINED_BASE_REVISION))

    assert first.run == second.run
    assert first != second
    assert _distinct_value_count(first, second) == 2


def test_one_revision_may_serve_runs_of_two_different_reports() -> None:
    first = _run_revision(run=_run(test_material=_material()))
    second = _run_revision(
        run=_run(
            SECOND_RUN,
            _material(material=SECOND_MATERIAL, report=_second_report()),
            SECOND_RUN_STATEMENT,
        )
    )

    assert first.revision == second.revision
    assert (
        first.run.test_material.report.context.fault
        != second.run.test_material.report.context.fault
    )


# --- the reported comparison ---------------------------------------------------


def test_a_comparison_relates_two_reported_outcomes_in_supplied_roles() -> None:
    comparison = _comparison()

    assert comparison.before.outcome is ReportedFaultTestOutcomeKind.FAILED
    assert comparison.after.outcome is ReportedFaultTestOutcomeKind.PASSED
    assert comparison.before.run.run != comparison.after.run.run
    assert comparison.before.run.test_material == comparison.after.run.test_material
    assert comparison.comparison_statement == COMPARISON_STATEMENT


def test_a_comparison_refuses_one_run_in_both_roles() -> None:
    outcome = _outcome()

    with pytest.raises(ValidationError) as failure:
        ReportedFaultTestComparison(
            before=outcome,
            after=_outcome(
                run=outcome.run,
                outcome=ReportedFaultTestOutcomeKind.PASSED,
                outcome_statement=SECOND_OUTCOME_STATEMENT,
            ),
            comparison_statement=COMPARISON_STATEMENT,
        )

    assert _failures(failure.value) == (((), "value_error"),)
    assert "distinct run subjects" in str(failure.value)


def test_a_comparison_refuses_two_different_supplied_test_materials() -> None:
    with pytest.raises(ValidationError) as failure:
        ReportedFaultTestComparison(
            before=_outcome(run=_run(SUPPLIED_RUN, _material())),
            after=_outcome(
                run=_run(
                    SECOND_RUN,
                    _material(
                        material=SECOND_MATERIAL, test_statement=SECOND_TEST_STATEMENT
                    ),
                    SECOND_RUN_STATEMENT,
                ),
                outcome=ReportedFaultTestOutcomeKind.PASSED,
            ),
            comparison_statement=COMPARISON_STATEMENT,
        )

    assert _failures(failure.value) == (((), "value_error"),)
    assert "same supplied test material" in str(failure.value)


def test_the_material_rule_compares_whole_records_not_identity_scalars() -> None:
    """Equal identities over different content are not the same material."""
    first = _material(test_statement=TEST_STATEMENT)
    second = _material(test_statement=SECOND_TEST_STATEMENT)

    assert first.material == second.material
    assert first != second
    with pytest.raises(ValidationError) as failure:
        ReportedFaultTestComparison(
            before=_outcome(run=_run(SUPPLIED_RUN, first)),
            after=_outcome(
                run=_run(SECOND_RUN, second, SECOND_RUN_STATEMENT),
                outcome=ReportedFaultTestOutcomeKind.PASSED,
            ),
            comparison_statement=COMPARISON_STATEMENT,
        )

    assert "same supplied test material" in str(failure.value)


def test_a_comparison_requires_no_chronology_candidate_or_environment() -> None:
    for absent in (
        "started_at",
        "finished_at",
        "timestamp",
        "duration",
        "repair_candidate",
        "revision",
        "environment",
        "independent",
        "machine",
    ):
        assert absent not in ReportedFaultTestComparison.model_fields, absent
    assert tuple(ReportedFaultTestComparison.model_fields) == COMPARISON_FIELDS


@pytest.mark.parametrize(
    ("before", "after"),
    (
        (ReportedFaultTestOutcomeKind.PASSED, ReportedFaultTestOutcomeKind.FAILED),
        (ReportedFaultTestOutcomeKind.PASSED, ReportedFaultTestOutcomeKind.PASSED),
        (ReportedFaultTestOutcomeKind.SKIPPED, ReportedFaultTestOutcomeKind.SKIPPED),
        (
            ReportedFaultTestOutcomeKind.CANCELLED,
            ReportedFaultTestOutcomeKind.DID_NOT_START,
        ),
    ),
)
def test_the_roles_are_supplied_rather_than_derived_from_any_ordering(
    before: ReportedFaultTestOutcomeKind,
    after: ReportedFaultTestOutcomeKind,
) -> None:
    """Any pair of dispositions is admitted; nothing infers which came first."""
    comparison = _comparison(before=before, after=after)

    assert comparison.before.outcome is before
    assert comparison.after.outcome is after


# --- semantic counterexamples ---------------------------------------------------


def test_a_fail_to_pass_comparison_is_not_a_verified_fix() -> None:
    """The pattern is reported; no field converts it into regression safety."""
    comparison = _comparison(
        before=ReportedFaultTestOutcomeKind.FAILED,
        after=ReportedFaultTestOutcomeKind.PASSED,
    )

    for absent in ("fail_to_pass", "repair_success", "regression_safe", "fixed"):
        assert absent not in ReportedFaultTestComparison.model_fields, absent
    text = comparison.model_dump_json()
    for absent in ("fail_to_pass", "repair_success", "regression_safe", "verified"):
        assert absent not in text, absent
    assert tuple(_payload(comparison)) == COMPARISON_FIELDS


def test_one_test_passing_says_nothing_about_any_other_test() -> None:
    """A wider claim needs its own independently reported material and outcomes."""
    narrow = _comparison(
        before=ReportedFaultTestOutcomeKind.FAILED,
        after=ReportedFaultTestOutcomeKind.PASSED,
    )
    other_material = _material(
        material=SECOND_MATERIAL, test_statement=SECOND_TEST_STATEMENT
    )

    assert narrow.before.run.test_material != other_material
    # Nothing in the narrow comparison reaches the other material at all.
    assert SECOND_TEST_STATEMENT not in narrow.model_dump_json()


def test_a_missing_before_outcome_manufactures_no_earlier_failure() -> None:
    """Without a before record no comparison exists, and none is synthesised."""
    after_only = _outcome(
        run=_run(SECOND_RUN, _material(), SECOND_RUN_STATEMENT),
        outcome=ReportedFaultTestOutcomeKind.PASSED,
    )

    with pytest.raises(ValidationError) as failure:
        ReportedFaultTestComparison(
            after=after_only,
            comparison_statement=COMPARISON_STATEMENT,
        )  # pyright: ignore[reportCallIssue]

    assert ("before",) in _paths(failure.value)
    assert ReportedFaultTestOutcomeKind.FAILED.value not in after_only.model_dump_json()


@pytest.mark.parametrize(
    "before",
    (
        ReportedFaultTestOutcomeKind.DID_NOT_START,
        ReportedFaultTestOutcomeKind.ERRORED,
        ReportedFaultTestOutcomeKind.TIMED_OUT,
    ),
)
def test_a_non_failed_before_is_not_a_failed_to_passed_transition(
    before: ReportedFaultTestOutcomeKind,
) -> None:
    comparison = _comparison(before=before, after=ReportedFaultTestOutcomeKind.PASSED)
    failed_to_passed = _comparison(
        before=ReportedFaultTestOutcomeKind.FAILED,
        after=ReportedFaultTestOutcomeKind.PASSED,
    )

    assert comparison.before.outcome is not ReportedFaultTestOutcomeKind.FAILED
    assert comparison != failed_to_passed
    assert _payload(comparison)["before"]["outcome"] == before.value


def test_the_six_before_situations_stay_six_distinct_situations() -> None:
    """A missing run, a missing outcome and four dispositions never flatten."""
    material = _material()
    missing_run = material
    missing_outcome = _run(SUPPLIED_RUN, material)
    dispositions = tuple(
        _outcome(run=missing_outcome, outcome=kind)
        for kind in (
            ReportedFaultTestOutcomeKind.DID_NOT_START,
            ReportedFaultTestOutcomeKind.FAILED,
            ReportedFaultTestOutcomeKind.ERRORED,
            ReportedFaultTestOutcomeKind.TIMED_OUT,
        )
    )

    assert _distinct_value_count(missing_run, missing_outcome, *dispositions) == 6
    assert "outcome" not in _payload(missing_outcome)
    assert "run" not in _payload(missing_run)


def test_distinct_run_identities_are_not_an_independence_guarantee() -> None:
    """Two identities are two subjects, not two independent trials."""
    shared = _material()
    comparison = ReportedFaultTestComparison(
        before=_outcome(
            run=_run(SUPPLIED_RUN, shared, RUN_STATEMENT),
            outcome=ReportedFaultTestOutcomeKind.FAILED,
            outcome_statement=OUTCOME_STATEMENT,
        ),
        after=_outcome(
            run=_run(SECOND_RUN, shared, RUN_STATEMENT),
            outcome=ReportedFaultTestOutcomeKind.PASSED,
            outcome_statement=OUTCOME_STATEMENT,
        ),
        comparison_statement=COMPARISON_STATEMENT,
    )

    # Identical run and outcome prose across two distinct subjects is admitted
    # and merges nothing, and no independence field is published.
    assert comparison.before.run.run_statement == comparison.after.run.run_statement
    assert comparison.before.outcome_statement == comparison.after.outcome_statement
    assert comparison.before != comparison.after
    for absent in ("independent", "trials", "process", "machine"):
        assert absent not in ReportedFaultTestComparison.model_fields, absent


def test_test_material_existing_does_not_imply_a_run_or_an_outcome() -> None:
    material = _material()

    assert "run" not in _payload(material)
    assert "outcome" not in _payload(material)
    assert set(_payload(material)) == set(MATERIAL_FIELDS)


def test_no_collection_field_and_no_module_registry_is_published() -> None:
    """Nothing here accumulates runs, outcomes or comparisons."""
    for model in _published_models():
        for name, field in model.model_fields.items():
            annotation = str(field.annotation)
            assert "list" not in annotation.lower(), (model.__name__, name)
            assert "tuple" not in annotation.lower(), (model.__name__, name)
            assert "dict" not in annotation.lower(), (model.__name__, name)
    module_values = {
        name: getattr(test_module, name)
        for name in dir(test_module)
        if not name.startswith("_")
    }
    for name, value in module_values.items():
        assert not isinstance(value, list | dict | set), name


# --- child guards, omission, frozen, extras -------------------------------------


@pytest.mark.parametrize(
    ("model", "field", "supplied", "label"),
    (
        pytest.param(
            SuppliedFaultTestMaterial,
            "material",
            SUPPLIED_MATERIAL,
            "bare uuid",
            id="material-bare-uuid",
        ),
        pytest.param(
            SuppliedFaultTestMaterial,
            "material",
            SUPPLIED_MATERIAL_TEXT,
            "uuid text",
            id="material-uuid-text",
        ),
        pytest.param(
            SuppliedFaultTestMaterial,
            "material",
            ForeignUuidRoot(SUPPLIED_MATERIAL),
            "foreign root",
            id="material-foreign",
        ),
        pytest.param(
            SuppliedFaultTestMaterial,
            "material",
            FaultTestRunIdentity(SUPPLIED_MATERIAL),
            "sibling identity",
            id="material-sibling",
        ),
        pytest.param(
            SuppliedFaultTestMaterial,
            "report",
            _report().model_dump(),
            "python dump",
            id="report-dump",
        ),
        pytest.param(
            SuppliedFaultTestMaterial,
            "report",
            MaterialLookalike(),
            "lookalike",
            id="report-lookalike",
        ),
        pytest.param(
            ReportedFaultTestRun, "run", SUPPLIED_RUN, "bare uuid", id="run-bare-uuid"
        ),
        pytest.param(
            ReportedFaultTestRun,
            "run",
            FaultTestMaterialIdentity(SUPPLIED_RUN),
            "sibling identity",
            id="run-sibling",
        ),
        pytest.param(
            ReportedFaultTestRun,
            "test_material",
            _material().model_dump(),
            "python dump",
            id="material-child-dump",
        ),
        pytest.param(
            ReportedFaultTestRun,
            "test_material",
            MaterialLookalike(),
            "lookalike",
            id="material-child-lookalike",
        ),
        pytest.param(
            ReportedFaultTestRun,
            "test_material",
            ForeignSuppliedFaultTestMaterial(
                material=_material_identity(),
                report=_report(),
                test_statement=TEST_STATEMENT,
            ),
            "foreign model",
            id="material-child-foreign",
        ),
        pytest.param(
            ReportedFaultTestOutcome,
            "run",
            _run().model_dump(),
            "python dump",
            id="outcome-run-dump",
        ),
        pytest.param(
            ReportedFaultTestOutcome,
            "run",
            RunLookalike(),
            "lookalike",
            id="outcome-run-lookalike",
        ),
        pytest.param(
            ReportedFaultTestOutcome,
            "outcome",
            "failed",
            "bare lexeme",
            id="outcome-text",
        ),
        pytest.param(
            FaultTestRunRevisionAssociation,
            "revision",
            RevisionLookalike(),
            "lookalike",
            id="revision-lookalike",
        ),
        pytest.param(
            FaultTestRunRevisionAssociation,
            "revision",
            _commit().model_dump(),
            "python dump",
            id="revision-dump",
        ),
        pytest.param(
            ReportedFaultTestComparison,
            "before",
            _outcome().model_dump(),
            "python dump",
            id="before-dump",
        ),
        pytest.param(
            ReportedFaultTestComparison,
            "after",
            _outcome().model_dump(),
            "python dump",
            id="after-dump",
        ),
    ),
)
def test_each_model_valued_position_is_closed_to_untyped_python_input(
    model: type[BaseModel],
    field: str,
    supplied: object,
    label: str,
) -> None:
    builders: dict[type[BaseModel], Callable[..., dict[str, Any]]] = {
        SuppliedFaultTestMaterial: _typed_material_mapping,
        ReportedFaultTestRun: _typed_run_mapping,
        ReportedFaultTestOutcome: _typed_outcome_mapping,
        FaultTestRunRevisionAssociation: _typed_run_revision_mapping,
        ReportedFaultTestComparison: _typed_comparison_mapping,
    }
    mapping = builders[model](**{field: supplied})

    with pytest.raises(ValidationError) as failure:
        model(**mapping)

    assert _failures(failure.value) == (((field,), "value_error"),), label


@pytest.mark.parametrize(
    ("model", "builder"),
    (
        pytest.param(SuppliedFaultTestMaterial, _typed_material_mapping, id="material"),
        pytest.param(ReportedFaultTestRun, _typed_run_mapping, id="run"),
        pytest.param(ReportedFaultTestOutcome, _typed_outcome_mapping, id="outcome"),
        pytest.param(
            FaultTestRunRevisionAssociation,
            _typed_run_revision_mapping,
            id="run-revision",
        ),
    ),
)
def test_a_top_level_mapping_still_guards_each_child(
    model: type[BaseModel],
    builder: Callable[..., dict[str, Any]],
) -> None:
    """`model_validate` over a typed mapping is admitted; a raw child is not."""
    assert model.model_validate(builder()) == model(**builder())

    first = next(iter(model.model_fields))
    with pytest.raises(ValidationError) as failure:
        model.model_validate(builder(**{first: {"root": SUPPLIED_RUN}}))

    assert _paths(failure.value)[0] == (first,)


def test_from_attributes_reads_a_top_level_object_but_still_guards_its_children() -> (
    None
):
    """A relaxed top-level read is not a relaxed child read."""
    material = SuppliedFaultTestMaterial.model_validate(
        MaterialLookalike(), from_attributes=True
    )

    assert material == _material()
    with pytest.raises(ValidationError) as failure:
        SuppliedFaultTestMaterial.model_validate(
            UntypedChildMaterialLookalike(), from_attributes=True
        )

    assert _failures(failure.value) == ((("report",), "value_error"),)


@pytest.mark.parametrize(
    ("model", "builder", "fields"),
    (
        pytest.param(
            SuppliedFaultTestMaterial,
            _typed_material_mapping,
            MATERIAL_FIELDS,
            id="material",
        ),
        pytest.param(ReportedFaultTestRun, _typed_run_mapping, RUN_FIELDS, id="run"),
        pytest.param(
            ReportedFaultTestOutcome,
            _typed_outcome_mapping,
            OUTCOME_FIELDS,
            id="outcome",
        ),
        pytest.param(
            FaultTestRunRevisionAssociation,
            _typed_run_revision_mapping,
            RUN_REVISION_FIELDS,
            id="run-revision",
        ),
    ),
)
def test_a_true_omission_fails_at_its_own_position(
    model: type[BaseModel],
    builder: Callable[..., dict[str, Any]],
    fields: tuple[str, ...],
) -> None:
    for omitted in fields:
        supplied = {name: value for name, value in builder().items() if name != omitted}
        with pytest.raises(ValidationError) as failure:
            model(**supplied)

        assert _failures(failure.value) == (((omitted,), "missing"),), omitted


@pytest.mark.parametrize(
    ("value", "fields"),
    (
        pytest.param(_material(), MATERIAL_FIELDS, id="material"),
        pytest.param(_run(), RUN_FIELDS, id="run"),
        pytest.param(_outcome(), OUTCOME_FIELDS, id="outcome"),
        pytest.param(_run_revision(), RUN_REVISION_FIELDS, id="run-revision"),
        pytest.param(_comparison(), COMPARISON_FIELDS, id="comparison"),
    ),
)
def test_each_record_is_frozen_against_assignment_and_deletion(
    value: BaseModel,
    fields: tuple[str, ...],
) -> None:
    for field in fields:
        with pytest.raises(ValidationError):
            setattr(value, field, getattr(value, field))
        with pytest.raises((AttributeError, ValidationError)):
            delattr(value, field)


@pytest.mark.parametrize("extra", REFUSED_EXTRA_KEYS)
def test_an_extra_key_is_refused_in_python_input(extra: str) -> None:
    with pytest.raises(ValidationError) as failure:
        ReportedFaultTestOutcome(**_typed_outcome_mapping(**{extra: "supplied"}))

    assert _failures(failure.value) == (((extra,), "extra_forbidden"),)


@pytest.mark.parametrize("extra", REFUSED_EXTRA_KEYS)
def test_an_extra_key_is_refused_in_json_input(extra: str) -> None:
    payload = _payload(_outcome())
    payload[extra] = "supplied"

    with pytest.raises(ValidationError) as failure:
        ReportedFaultTestOutcome.model_validate_json(json.dumps(payload))

    assert _failures(failure.value) == (((extra,), "extra_forbidden"),)


def test_an_extra_key_inside_an_embedded_child_is_refused_at_its_own_path() -> None:
    payload = _payload(_run())
    payload["test_material"]["report"]["verified"] = True

    with pytest.raises(ValidationError) as failure:
        ReportedFaultTestRun.model_validate_json(json.dumps(payload))

    assert _failures(failure.value) == (
        (("test_material", "report", "verified"), "extra_forbidden"),
    )


def _tamper_material_identity(payload: dict[str, Any]) -> None:
    payload["test_material"]["material"] = "not-a-uuid"


def _tamper_report_text(payload: dict[str, Any]) -> None:
    payload["test_material"]["report"]["problem_statement"] = " padded"


def _tamper_run_identity(payload: dict[str, Any]) -> None:
    payload["run"] = "not-a-uuid"


@pytest.mark.parametrize(
    ("path", "mutate"),
    (
        pytest.param(
            ("test_material", "material"),
            _tamper_material_identity,
            id="material-identity",
        ),
        pytest.param(
            ("test_material", "report", "problem_statement"),
            _tamper_report_text,
            id="report-text",
        ),
        pytest.param(("run",), _tamper_run_identity, id="run-identity"),
    ),
)
def test_a_tampered_child_is_refused_under_its_own_published_schema(
    path: tuple[str, ...],
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    payload = _payload(_run())
    mutate(payload)

    with pytest.raises(ValidationError) as failure:
        ReportedFaultTestRun.model_validate_json(json.dumps(payload))

    assert path in _paths(failure.value)


def test_a_no_added_field_subclass_is_admitted_and_base_normalized() -> None:
    subclass = UnextendedReportedFaultTestRun(**_typed_run_mapping())
    outcome = _outcome(run=subclass)

    assert isinstance(subclass, ReportedFaultTestRun)
    assert type(outcome.run) is ReportedFaultTestRun
    assert outcome.run == _run()


def test_a_subclass_extra_field_remains_refused() -> None:
    extended = ExtendedReportedFaultTestRun(**_typed_run_mapping())

    assert extended.note == "supplied"
    with pytest.raises(ValidationError) as failure:
        ReportedFaultTestRun.model_validate_json(extended.model_dump_json())

    assert _failures(failure.value) == ((("note",), "extra_forbidden"),)


# --- the four supplied-text fields ----------------------------------------------

TEXT_POSITIONS: tuple[tuple[str, str, Callable[[str], BaseModel]], ...] = (
    (
        "test_statement",
        "SuppliedFaultTestMaterial",
        lambda supplied: _material(test_statement=supplied),
    ),
    (
        "run_statement",
        "ReportedFaultTestRun",
        lambda supplied: _run(run_statement=supplied),
    ),
    (
        "outcome_statement",
        "ReportedFaultTestOutcome",
        lambda supplied: _outcome(outcome_statement=supplied),
    ),
    (
        "comparison_statement",
        "ReportedFaultTestComparison",
        lambda supplied: _comparison(comparison_statement=supplied),
    ),
)
TEXT_IDS = tuple(field for field, _, _ in TEXT_POSITIONS)


@pytest.mark.parametrize(("field", "owner", "build"), TEXT_POSITIONS, ids=TEXT_IDS)
@pytest.mark.parametrize(
    "supplied",
    (
        "x",
        "Multi\nline\nstatement.",
        "Tab\tseparated statement.",
        "Unicode: café — naïve — 変更 — 🛠",
        "a" * TEXT_LIMIT,
        "Inner  double  spaces stay.",
    ),
)
def test_an_admitted_statement_is_preserved_exactly(
    field: str,
    owner: str,
    build: Callable[[str], BaseModel],
    supplied: str,
) -> None:
    value = build(supplied)

    assert getattr(value, field) == supplied
    assert _payload(value)[field] == supplied
    assert type(value).model_validate_json(value.model_dump_json()) == value
    assert type(value).__name__ == owner


@pytest.mark.parametrize(("field", "owner", "build"), TEXT_POSITIONS, ids=TEXT_IDS)
@pytest.mark.parametrize(
    "supplied",
    (
        "",
        " ",
        "\n",
        "\t",
        "   \n  ",
        " leading",
        "trailing ",
        "\nleading newline",
        "trailing newline\n",
        "a" * (TEXT_LIMIT + 1),
    ),
)
def test_a_refused_statement_is_refused_at_its_own_position(
    field: str,
    owner: str,
    build: Callable[[str], BaseModel],
    supplied: str,
) -> None:
    with pytest.raises(ValidationError) as failure:
        build(supplied)

    assert _paths(failure.value) == ((field,),), owner


@pytest.mark.parametrize(("field", "owner", "build"), TEXT_POSITIONS, ids=TEXT_IDS)
@pytest.mark.parametrize("supplied", (None, 1, 1.0, b"bytes", ["text"], SUPPLIED_FAULT))
def test_a_non_string_statement_is_refused(
    field: str,
    owner: str,
    build: Callable[[str], BaseModel],
    supplied: object,
) -> None:
    with pytest.raises(ValidationError) as failure:
        build(cast(Any, supplied))

    assert _paths(failure.value) == ((field,),), owner


@pytest.mark.parametrize(("field", "owner", "build"), TEXT_POSITIONS, ids=TEXT_IDS)
def test_an_unencodable_statement_is_refused_at_the_field(
    field: str,
    owner: str,
    build: Callable[[str], BaseModel],
) -> None:
    """Text that cannot encode as UTF-8 is refused where it is supplied."""
    with pytest.raises(ValidationError) as failure:
        build("lone surrogate \ud800")

    assert _failures(failure.value) == (((field,), "string_unicode"),), owner


def test_a_str_subclass_statement_normalizes_to_str() -> None:
    material = _material(test_statement=SuppliedText(TEST_STATEMENT))

    assert material.test_statement == TEST_STATEMENT
    assert type(material.test_statement) is str


@pytest.mark.parametrize(
    ("owner", "field"),
    (
        ("SuppliedFaultTestMaterial", "test_statement"),
        ("ReportedFaultTestRun", "run_statement"),
        ("ReportedFaultTestOutcome", "outcome_statement"),
        ("ReportedFaultTestComparison", "comparison_statement"),
    ),
)
def test_each_text_bound_is_declared_inline_on_its_own_field(
    owner: str,
    field: str,
) -> None:
    """The shared rule is restated per field, not shared through an alias.

    That no shared public alias is exported is held by the `__all__` lock; this
    asserts only that the literal bound is declared where each field is.
    """
    (owner_class,) = [
        node
        for node in _test_tree().body
        if isinstance(node, ast.ClassDef) and node.name == owner
    ]
    annotations = {
        node.target.id: ast.unparse(node.annotation)
        for node in owner_class.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }

    assert "StringConstraints(min_length=1, max_length=4096)" in annotations[field], (
        owner
    )


# --- the module's own surface and boundaries ------------------------------------


def test_the_module_publishes_exactly_eight_symbols_in_order() -> None:
    assert test_module.__all__ == EXPECTED_EXPORTS
    assert [
        node.name for node in ast.walk(_test_tree()) if isinstance(node, ast.ClassDef)
    ] == EXPECTED_EXPORTS


DECLARED_VALIDATORS = (
    "_require_typed_python_material",
    "_require_typed_python_report",
    "_require_unpadded_text",
    "_require_typed_python_run",
    "_require_typed_python_test_material",
    "_require_unpadded_text",
    "_require_typed_python_run",
    "_require_typed_python_outcome",
    "_require_unpadded_text",
    "_require_typed_python_run",
    "_require_typed_python_revision",
    "_require_typed_python_outcome",
    "_require_unpadded_text",
    "_require_distinct_run_subjects",
    "_require_one_supplied_test_material",
)


def test_the_module_defines_only_the_declared_validators() -> None:
    """A derivation or a helper added anywhere in the module must fail here.

    `__all__` and the class-name list pin what is exported, not what exists: a
    classmethod deriving an outcome from a comparison, or any other function,
    changes neither and would otherwise be invisible.
    """
    functions = [
        node.name
        for node in ast.walk(_test_tree())
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]

    assert tuple(functions) == DECLARED_VALIDATORS
    for name in functions:
        assert name.startswith("_")
        assert name not in test_module.__all__


@pytest.mark.parametrize("model", _published_models(), ids=lambda m: m.__name__)
def test_no_record_publishes_an_attribute_beyond_its_fields(
    model: type[BaseModel],
) -> None:
    """A verdict may not arrive as a property or method either.

    Pydantic fields are not class attributes, so a clean value model adds no
    public name of its own. A `regression_safe` or `fail_to_pass` property
    would leave `model_fields` and the JSON payload untouched while still being
    reachable on the record.
    """
    beyond = {name for name in dir(model) if not name.startswith("_")} - set(
        dir(BaseModel)
    )

    assert beyond == set(), model.__name__
    assert model.model_computed_fields == {}


@pytest.mark.parametrize(
    "identity",
    (FaultTestMaterialIdentity, FaultTestRunIdentity),
    ids=("material", "run"),
)
def test_neither_identity_publishes_an_attribute_beyond_its_root(
    identity: type[RootModel[uuid.UUID]],
) -> None:
    beyond = {name for name in dir(identity) if not name.startswith("_")} - set(
        dir(RootModel)
    )

    assert beyond == set()
    assert identity.model_computed_fields == {}


def test_the_outcome_vocabulary_publishes_no_helper_beyond_its_members() -> None:
    beyond = {
        name for name in dir(ReportedFaultTestOutcomeKind) if not name.startswith("_")
    } - {name for name, _ in EXPECTED_OUTCOME_MEMBERS}

    assert beyond <= set(dir(str)) | {"name", "value"}
    for name in beyond:
        assert not callable(getattr(ReportedFaultTestOutcomeKind, name, None)) or (
            name in dir(str)
        )


def test_the_module_is_not_re_exported_from_the_package_or_domain_root() -> None:
    assert faultatlas.__all__ == ["__version__"]
    assert not hasattr(faultatlas.domain, "__all__")
    for symbol in EXPECTED_EXPORTS:
        assert not hasattr(faultatlas, symbol)
        assert not hasattr(faultatlas.domain, symbol)


def test_the_module_imports_only_its_declared_predecessors() -> None:
    imported = {
        alias.name if isinstance(node, ast.Import) else cast(str, node.module)
        for node in ast.walk(_test_tree())
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    }

    # An exact set: the evidence layer, the S1.P06.S04 bridge, the S1.P06.S05
    # repair module, the history layer and the P03 acquisition module are all
    # excluded by this equality rather than by a name list.
    assert imported == {
        "uuid",
        "enum",
        "typing",
        "pydantic",
        "faultatlas.domain.fault",
        "faultatlas.domain.revision",
    }


def test_the_module_performs_no_io() -> None:
    called = {
        node.func.id
        for node in ast.walk(_test_tree())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert not called & {"open", "eval", "exec", "compile", "__import__", "print"}
    body = " ".join(TEST_SOURCE.read_text(encoding="utf-8").split('"""', 2)[-1].split())
    for forbidden in (
        "import os",
        "import io",
        "Path(",
        "requests",
        "urllib",
        "now(",
        "subprocess",
    ):
        assert forbidden not in body, forbidden


@pytest.mark.parametrize(
    "relative",
    (
        "src/faultatlas/domain/fault.py",
        "src/faultatlas/domain/fault_repair.py",
        "src/faultatlas/domain/fault_source_relationship.py",
        "src/faultatlas/domain/history.py",
        "src/faultatlas/domain/revision.py",
        "src/faultatlas/domain/evidence.py",
    ),
)
def test_no_predecessor_production_module_imports_this_one(relative: str) -> None:
    source = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")

    assert "fault_test" not in source
    for symbol in EXPECTED_EXPORTS:
        assert symbol not in source


def test_the_tracked_production_inventory_is_seventeen_modules() -> None:
    tracked = subprocess.run(  # noqa: S603 - literal argv, no shell
        ["git", "ls-files", "src/"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
    )
    assert tracked.returncode == 0, tracked.stderr
    observed = sorted(tracked.stdout.decode("utf-8").split())

    assert observed == [f"src/{name}" for name in EXPECTED_PRODUCTION_MODULES]
    assert len(observed) == 17
    assert "src/faultatlas/domain/fault_test.py" in observed


# --- the roadmap transition -------------------------------------------------


def _current_status_section() -> str:
    roadmap = _roadmap()
    start = roadmap.index("## Current status")
    end = roadmap.index("## Program stages")
    assert start < end
    return roadmap[start:end]


def test_the_current_status_section_states_exactly_the_live_lifecycle() -> None:
    section = _current_status_section()

    assert "`S1.P06` is active and incomplete" in section
    for index in range(1, 7):
        assert f"`S1.P06.S{index:02d}` is complete" in section, index
    assert "`S1.P06.S07` is next and not started" in section
    assert "`S1.P07` through `S1.P10` remain not started" in section

    for index in range(7, 13):
        assert f"`S1.P06.S{index:02d}` is complete" not in section, index
    for index in range(1, 7):
        assert f"`S1.P06.S{index:02d}` is next and not started" not in section, index
    assert "`S1.P06` is complete" not in section
    assert "`S1.P06` is `eligible_to_begin`" not in section


def test_the_roadmap_carries_exactly_one_live_gate() -> None:
    roadmap = _roadmap()

    live_next = re.findall(
        r"`(S1\.P\d\d(?:\.S\d\d)?)` is next and not started", roadmap
    )
    assert live_next, "the roadmap names no next gate"
    assert set(live_next) == {"S1.P06.S07"}, sorted(set(live_next))
    live_phases = re.findall(r"`(S1\.P\d\d)` is active and incomplete", roadmap)
    assert set(live_phases) == {"S1.P06"}, sorted(set(live_phases))
    for line in ROADMAP.read_text(encoding="utf-8").splitlines():
        if "next and not started" in line:
            assert "`S1.P06.S07`" in line, line


def test_the_roadmap_records_the_p06_s06_transition() -> None:
    raw = ROADMAP.read_text(encoding="utf-8")
    roadmap = _roadmap()
    mapping = roadmap.split("## Current-code mapping", 1)
    assert len(mapping) == 2, "roadmap must retain a current-code mapping section"
    current = mapping[1]

    assert "`S1.P06.S06` is complete" in roadmap
    assert "`S1.P06.S07` is next and not started" in roadmap
    assert (
        "`S1.P06.S06` — Test Material, Reported Runs, Outcomes, and "
        "Comparability (complete)" in roadmap
    )
    assert "The `S1.P06` route is provisional beyond `S1.P06.S06`." in roadmap

    assert "faultatlas.domain.fault_test" in current
    for symbol in EXPECTED_EXPORTS:
        assert f"`{symbol}`" in current
    assert "Production Python sources are 17." in current
    assert "`test_material.report.context.fault`" in roadmap

    # The superseded live gate and the provisional S06 title must be retired.
    assert "`S1.P06.S06` is next and not started" not in roadmap
    assert (
        "`S1.P06.S06` — Test material, reported outcomes, and comparability "
        "(next, not started)" not in roadmap
    )
    assert "`S1.P06.S07` is complete" not in roadmap
    assert "Production Python sources are 16." not in current
    assert "- **S1.P06 — Fault Instance Model**" not in raw


def test_the_roadmap_states_the_s06_decisions_and_non_claims() -> None:
    roadmap = _roadmap()

    assert "production Python sources move from 16 to 17" in roadmap
    assert "Test material is not a run" in roadmap
    assert "A run is not its outcome" in roadmap
    assert "FaultAtlas executes no analyzed repository here" in roadmap
    assert "Neither is a FaultAtlas observation" in roadmap
    assert "A run identity is not an acquisition run" in roadmap
    assert "bounded seven-member vocabulary" in roadmap
    assert "Absence is not a disposition." in roadmap
    assert "Fail-to-pass is not regression safety." in roadmap
    assert "A missing before run is not a before failure." in roadmap
    assert "Distinct run identities are not an independence guarantee." in roadmap
    assert "six distinct situations" in roadmap
    assert "all seven `S1.P06` UUID-rooted identities stay nominally distinct" in (
        roadmap
    )


def test_the_roadmap_preserves_the_predecessor_history_as_written() -> None:
    roadmap = _roadmap()

    assert (
        "`S1.P06.S01` publishes one new production module, `faultatlas.domain.fault`, "
        "whose initial `__all__` is exactly `FaultInstanceIdentity` and "
        "`FaultRepositoryContext`." in roadmap
    )
    assert "production Python sources move from 15 to 16" in roadmap
    assert "`S1.P05` is complete" in roadmap
    assert "`S1.P06` was `eligible_to_begin`" in roadmap


# --- packaging and an isolated installed-wheel smoke --------------------------


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

import faultatlas.domain.fault_test as test_module
from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    FaultReportIdentity,
    FaultRepositoryContext,
    SuppliedFaultReport,
)
from faultatlas.domain.fault_test import (
    FaultTestMaterialIdentity,
    FaultTestRunIdentity,
    FaultTestRunRevisionAssociation,
    ReportedFaultTestComparison,
    ReportedFaultTestOutcome,
    ReportedFaultTestOutcomeKind,
    ReportedFaultTestRun,
    SuppliedFaultTestMaterial,
)
from faultatlas.domain.identity import (
    ProviderKey,
    ProviderRepositoryId,
    RepositoryIdentity,
)
from faultatlas.domain.revision import (
    GitCommitIdentity,
    GitHashAlgorithm,
    GitObjectKind,
)

module = Path(test_module.__file__).resolve()
assert module.is_relative_to(installed), module
assert not module.is_relative_to(checkout), module
assert test_module.__all__ == [
    "FaultTestMaterialIdentity",
    "SuppliedFaultTestMaterial",
    "FaultTestRunIdentity",
    "ReportedFaultTestRun",
    "ReportedFaultTestOutcomeKind",
    "ReportedFaultTestOutcome",
    "FaultTestRunRevisionAssociation",
    "ReportedFaultTestComparison",
]

report = SuppliedFaultReport(
    report=FaultReportIdentity(uuid.UUID(os.environ["REPORT_UUID"])),
    context=FaultRepositoryContext(
        fault=FaultInstanceIdentity(uuid.UUID(os.environ["FAULT_UUID"])),
        repository=RepositoryIdentity(
            provider=ProviderKey("github"),
            provider_repository_id=ProviderRepositoryId(os.environ["REPOSITORY_ID"]),
        ),
    ),
    problem_statement=os.environ["PROBLEM_STATEMENT"],
    behavioral_deviation=os.environ["BEHAVIORAL_DEVIATION"],
)
material = SuppliedFaultTestMaterial(
    material=FaultTestMaterialIdentity(uuid.UUID(os.environ["MATERIAL_UUID"])),
    report=report,
    test_statement=os.environ["TEST_STATEMENT"],
)


def reported_run(run_uuid, statement):
    return ReportedFaultTestRun(
        run=FaultTestRunIdentity(uuid.UUID(run_uuid)),
        test_material=material,
        run_statement=statement,
    )


before_run = reported_run(os.environ["RUN_UUID"], os.environ["RUN_STATEMENT"])
after_run = reported_run(
    os.environ["SECOND_RUN_UUID"], os.environ["SECOND_RUN_STATEMENT"]
)
outcome = ReportedFaultTestOutcome(
    run=before_run,
    outcome=ReportedFaultTestOutcomeKind.FAILED,
    outcome_statement=os.environ["OUTCOME_STATEMENT"],
)
after_outcome = ReportedFaultTestOutcome(
    run=after_run,
    outcome=ReportedFaultTestOutcomeKind.PASSED,
    outcome_statement=os.environ["SECOND_OUTCOME_STATEMENT"],
)
run_revision = FaultTestRunRevisionAssociation(
    run=before_run,
    revision=GitCommitIdentity(
        kind=GitObjectKind.COMMIT,
        algorithm=GitHashAlgorithm.SHA1,
        full_digest=os.environ["HEAD_REVISION"],
    ),
)
comparison = ReportedFaultTestComparison(
    before=outcome,
    after=after_outcome,
    comparison_statement=os.environ["COMPARISON_STATEMENT"],
)

for value, model in (
    (material, SuppliedFaultTestMaterial),
    (before_run, ReportedFaultTestRun),
    (outcome, ReportedFaultTestOutcome),
    (run_revision, FaultTestRunRevisionAssociation),
    (comparison, ReportedFaultTestComparison),
):
    assert model.model_validate_json(value.model_dump_json()) == value

print(
    json.dumps(
        {
            "module": str(module),
            "material_identity": FaultTestMaterialIdentity(
                uuid.UUID(os.environ["MATERIAL_UUID"])
            ).model_dump_json(),
            "run_identity": FaultTestRunIdentity(
                uuid.UUID(os.environ["RUN_UUID"])
            ).model_dump_json(),
            "outcome_kinds": [member.value for member in ReportedFaultTestOutcomeKind],
            "material": material.model_dump_json(),
            "run": before_run.model_dump_json(),
            "outcome": outcome.model_dump_json(),
            "run_revision": run_revision.model_dump_json(),
            "comparison": comparison.model_dump_json(),
        }
    )
)
"""


@pytest.fixture(scope="session")
def offline_distributions(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, Path]:
    uv = shutil.which("uv")
    assert uv is not None, "uv must be available to build the supported distributions"

    root = tmp_path_factory.mktemp("fault-test-package")
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


EXPECTED_PRODUCTION_MODULES = [
    "faultatlas/__init__.py",
    "faultatlas/__main__.py",
    "faultatlas/cli.py",
    "faultatlas/domain/__init__.py",
    "faultatlas/domain/compatibility.py",
    "faultatlas/domain/evidence.py",
    "faultatlas/domain/fault.py",
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


def test_the_wheel_ships_the_test_module_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    wheel, _ = offline_distributions
    with zipfile.ZipFile(wheel) as archive:
        names = tuple(info.filename for info in archive.infolist() if not info.is_dir())

    modules = sorted(name for name in names if name.endswith(".py"))
    assert modules == EXPECTED_PRODUCTION_MODULES
    assert len(modules) == 17
    assert "faultatlas/domain/fault_test.py" in modules
    for name in names:
        assert "reference_corpus" not in name
        assert not name.startswith("tests/")
        assert not name.startswith("docs/")


def test_the_sdist_ships_the_test_module_and_no_corpus_or_test_material(
    offline_distributions: tuple[Path, Path],
) -> None:
    _, sdist = offline_distributions
    with tarfile.open(sdist, "r:gz") as archive:
        names = tuple(member.name for member in archive.getmembers() if member.isfile())

    modules = sorted(
        name.split("/src/", 1)[1] for name in names if name.endswith(".py")
    )
    assert modules == EXPECTED_PRODUCTION_MODULES
    assert len(modules) == 17
    assert "faultatlas/domain/fault_test.py" in modules
    for name in names:
        parts = Path(name).parts
        assert "reference_corpus" not in parts
        assert "tests" not in parts
        assert "docs" not in parts


def test_the_installed_wheel_exercises_all_eight_new_symbols(
    offline_distributions: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """All eight S06 symbols must run from the wheel copy, not the checkout."""
    wheel, _ = offline_distributions
    installed = tmp_path / "installed"
    installed.mkdir()
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)

    assert (installed / "faultatlas/domain/fault_test.py").is_file()

    environment = os.environ.copy()
    environment.update(
        {
            "INSTALLED_ROOT": str(installed),
            "CHECKOUT_SOURCE_ROOT": str(CHECKOUT_SOURCE_ROOT),
            "FAULT_UUID": SUPPLIED_FAULT_TEXT,
            "REPORT_UUID": SUPPLIED_REPORT_TEXT,
            "MATERIAL_UUID": SUPPLIED_MATERIAL_TEXT,
            "RUN_UUID": SUPPLIED_RUN_TEXT,
            "SECOND_RUN_UUID": SECOND_RUN_TEXT,
            "REPOSITORY_ID": RETAINED_REPOSITORY_ID,
            "HEAD_REVISION": RETAINED_HEAD_REVISION,
            "PROBLEM_STATEMENT": PROBLEM_STATEMENT,
            "BEHAVIORAL_DEVIATION": BEHAVIORAL_DEVIATION,
            "TEST_STATEMENT": TEST_STATEMENT,
            "RUN_STATEMENT": RUN_STATEMENT,
            "SECOND_RUN_STATEMENT": SECOND_RUN_STATEMENT,
            "OUTCOME_STATEMENT": OUTCOME_STATEMENT,
            "SECOND_OUTCOME_STATEMENT": SECOND_OUTCOME_STATEMENT,
            "COMPARISON_STATEMENT": COMPARISON_STATEMENT,
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
    reported: dict[str, Any] = json.loads(result.stdout.strip().splitlines()[-1])
    assert Path(reported["module"]).is_relative_to(installed)
    assert not Path(reported["module"]).is_relative_to(CHECKOUT_SOURCE_ROOT)
    assert json.loads(reported["material_identity"]) == SUPPLIED_MATERIAL_TEXT
    assert json.loads(reported["run_identity"]) == SUPPLIED_RUN_TEXT
    assert tuple(reported["outcome_kinds"]) == tuple(
        value for _, value in EXPECTED_OUTCOME_MEMBERS
    )
    assert json.loads(reported["material"]) == _payload(_material())
    assert json.loads(reported["run"]) == _payload(_run())
    assert json.loads(reported["outcome"]) == _payload(_outcome())
    assert json.loads(reported["run_revision"]) == _payload(_run_revision())
    assert json.loads(reported["comparison"]) == _payload(_comparison())
