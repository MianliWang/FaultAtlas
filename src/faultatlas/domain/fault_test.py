"""Supplied fault test material, reported runs, outcomes, and comparability.

This module publishes four things the FaultInstance model must be able to say
separately, and deliberately keeps them apart: what test material a caller has
in mind, that a caller reports having attempted a run of it, what disposition
that attempt reportedly reached, and how one reported outcome compares with
another. A fifth, optional relation attaches an immutable commit identity to a
reported run. Nothing here executes anything.

Test material is not a run. A regression test, a reduced reproduction, a manual
procedure, a test command concept, or a property-oriented check can be described
long before anyone reports running it, and a supplied material value stands
complete with no run and no outcome anywhere. A run is not its outcome either: a
caller may report an attempt while supplying no outcome record at all, so the
existence of a run says nothing about whether it passed, failed, timed out, or
ever started. Keeping the two apart is what lets a caller record "we have a test
for this" and "we tried it" as different pieces of knowledge.

Everything here is caller-reported. FaultAtlas executes no analyzed repository in
this Slice: it starts no process, runs no command, and observes no verdict. A
reported run is a claim that someone says they attempted something, and a
reported outcome is a claim about how that attempt reportedly ended. Neither is
a FaultAtlas observation, and neither may later be read as one. If FaultAtlas is
ever separately authorized to execute anything, that result must be a distinct
value rather than a silent reuse of these, because the difference between what a
caller says happened and what this system watched happen is the whole point of
the separation.

A test-material identity and a run identity are two further independent
UUID-rooted values, each neither a subclass nor an alias of the other or of the
fault, report, scenario, occurrence, and repair-candidate identities. All seven
stay nominally distinct even when one scalar is assigned to all seven. The caller
assigns each UUID; nothing generates, derives, reserves, looks up, deduplicates,
merges, or registers one, no identifier is derived from content, and neither is
an authorization token or a security boundary. Nil and Max are ordinary admitted
values rather than sentinels, no generation version is required or inferred, the
JSON form of each is the ordinary bare UUID string with no wrapper or adapter,
and equality, hashing and ordering are left exactly as Pydantic defines them.

A run identity is emphatically not an acquisition run. The published `S1.P03`
`AcquisitionRunId` and its run models describe the lifecycle of retrieving
evidence, which is a different activity with a different owner; this module does
not import, reuse, alias, or reinterpret them. Nor is a run identity a CI
workflow run, a provider-side run, or an execution performed here. The word
"run" names a caller-designated attempt subject and nothing more, and it does not
even guarantee that the test body started -- that distinction is supplied, when
it is supplied at all, by the outcome layer's `did_not_start`.

Supplied test material binds one material identity to one published
`SuppliedFaultReport` consumed whole and to one statement describing the material
or procedure. The fault subject stays reachable at
`test_material.report.context.fault`, and no fault, repository, report identity,
problem statement, or behavioral deviation is restated. It requires no scenario,
no occurrence, no repair candidate, and no run. Creating one does not establish
that the test exists in any repository, that exact test bytes were retained, that
a locator was inspected, that the material has ever been executed, that it is
sufficient, that it reproduces the fault, that it is evidence, or that it is
regression-complete. It is a knowledge object about a procedure, not captured
code: there is no source or evidence field here, the fault-evidence bridge is
`S1.P06.S09` work, and durable byte contracts remain `S1.P10` work.

A reported run binds one run identity to one supplied test material consumed
whole and to a statement describing the attempted execution context. That
statement is opaque prose and is deliberately not parsed into operating system,
platform, architecture, environment, command, dependency version, or runtime
version fields; describing an invocation is not structuring it. No outcome is
attached to the run record, because a reported attempt and a reported disposition
are separate pieces of knowledge, and no time is recorded.

The reported outcome vocabulary is a bounded FaultAtlas vocabulary for a
caller-reported execution disposition, not a claim that every testing framework
uses these seven states. `passed` and `failed` are the two terminal test
verdicts, a negative verdict being distinct from a failure to run at all.
`errored` reports that execution began or progressed but ended in an error rather
than a normal verdict. `timed_out` reports that the attempt exceeded its relevant
time bound without reaching one. `skipped` reports that the test system's own
disposition deliberately did not execute it. `did_not_start` reports that
environment, setup, or launch conditions prevented execution from starting, and
is deliberately not `failed`. `cancelled` reports that the attempt was cancelled
without reaching `passed` or `failed`.

No `unknown`, `flaky`, `regression_safe`, `fixed`, or `verified` member exists. An
unsupplied outcome is represented by the absence of an outcome record, not by a
member of this enum, so the vocabulary never has to carry a missing state.
Flakiness is an interpretation over several reported runs rather than one run's
terminal disposition, and regression safety and repair correctness are not
outcome kinds at all.

Absence is not a disposition. That no outcome record is supplied for a run means
only that none is supplied here: it does not report that the run failed, passed,
timed out, was skipped, never started, or that its result is unknown as a
positive claim. No boolean, sentinel, or `None` stands for any of those.

A reported outcome binds one reported run consumed whole to one member of that
vocabulary and to an outcome description. It does not mean that FaultAtlas
witnessed the run, that the report is correct, that the repair candidate is
correct, or that any evidence supports it, and it carries no evidence record,
confidence, review, or correctness field. Two outcome records may name the same
run and disagree; this layer neither resolves nor flags that, because it has no
aggregate authority and no registry. Composing or reviewing conflicting reported
knowledge is `S1.P06.S08` and `S1.P09` work.

A run-revision association records that the caller associates one immutable
`GitCommitIdentity` with one reported run. The commit identity is reused whole
and intrinsically, so nothing about where that commit lives is claimed: no
repository membership, no reachability, no base, head, or merge role, no repair
candidate, no before or after role, no application or deployment, and no test
correctness. A run may carry no revision association at all, which is what a
reported run whose exact revision is unavailable or simply unsupplied looks like,
so no `None` and no fabricated revision is ever required. A run may equally carry
several, and this layer has no authority to reconcile them.

A reported comparison relates two reported outcomes in caller-supplied `before`
and `after` roles, with a statement describing the comparison. Exactly two rules
hold it together: the two outcomes must name distinct run subjects, since one run
cannot occupy both roles, and their runs must carry the same full supplied test
material value. The second rule compares whole material records rather than
identity scalars alone, so two runs whose material identities agree while their
material content disagrees are not silently accepted as comparing the same thing.

Nothing else is inferred. No timestamp is required or read, and the roles are
supplied rather than derived from any chronology; no repair candidate,
run-revision association, environment equality, independent execution, shared
machine or process, causation, or regression safety is required or implied.

Fail-to-pass is not regression safety. A comparison whose outcomes happen to be
`failed` then `passed` contains a reported fail-to-pass pattern for one test
material, and that is all it contains, which is why no `fail_to_pass`,
`repair_success`, or `regression_safe` field is published and why nothing here
converts such a pair into a verified fix. One failing test becoming passing does
not establish that unrelated tests still pass, that no new regression exists,
that the repair candidate is correct, or that the root cause is correct; a wider
regression claim would need its own independently reported material and outcomes.

A missing before run is not a before failure. Without a before outcome record no
comparison can be constructed at all, and none is synthesised: a later passing
run never manufactures an earlier `failed`. A missing before run, a missing
before outcome, and before outcomes of `did_not_start`, `failed`, `errored`, or
`timed_out` are six distinct situations and are never flattened into one. For the
same reason a `did_not_start` to `passed` comparison is not a `failed` to
`passed` transition -- it may reflect an environment becoming usable, and this
layer does not infer which -- and neither `timed_out` to `passed` nor `errored`
to `passed` is that transition either.

Distinct run identities are not an independence guarantee. The comparison
requires them because one run cannot fill both roles, not because two identities
prove two independent processes, environments, evidence sources, or statistically
independent trials. Identical outcome or run prose may appear across distinct
runs without merging them, and nothing here becomes independent support by being
referenced twice.

Every model-valued immediate child position is closed to untyped Python input. A
caller must supply an already typed value; a raw UUID, a string, a mapping, an
attribute-backed lookalike, or a foreign model is refused even when its scalar
content matches, because constructing a published identity, report, material,
run, outcome, or commit identity is that value's own responsibility. The outcome
position is closed the same way and requires a typed vocabulary member rather
than relying on incidental strict-mode behaviour. A top-level mapping validated
with `from_attributes=True` does not bypass those guards. JSON is a different
input language: there the declared child schemas and the enum lexeme reconstruct
normally, so a semantic JSON round trip succeeds while a Python round trip
through `model_dump` deliberately does not, and each embedded value is
revalidated under its own published schema so a tampered child is refused at its
own position. The raw text fields carry no nominal guard; their rules are content
rules.

Every supplied text here is a claim handled as opaque prose under one shared rule
stated separately on each field rather than through a shared alias or base. Each
must be present, non-blank, and at most 4096 characters; leading or trailing
whitespace is refused rather than trimmed, so whitespace-only text fails, and a
value that cannot encode as UTF-8 is refused. Admitted Unicode and interior
whitespace, including newlines, are preserved exactly: nothing lowercases,
normalizes, parses, tokenizes, classifies, or rewrites it, and nothing decides
whether what it describes is true, sufficient, or correct. The 4096 limit is a
character bound of this internal contract, not a durable byte-format promise.

That closure is stated over the declared default validation policy, as every
published module here states it. Deliberately relaxing the policy is a different
question this module does not answer: `strict=False`, an altered `extra` setting,
a schema or serializer override, and the string-parsing entry point are not entry
points designed here.

The module performs no I/O. It reads no clock, allocates no identifier, consults
no registry or environment, resolves nothing, and starts no process.
"""

import uuid
from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    RootModel,
    StringConstraints,
    ValidationInfo,
    field_validator,
    model_validator,
)

from faultatlas.domain.fault import SuppliedFaultReport
from faultatlas.domain.revision import GitCommitIdentity

__all__ = [
    "FaultTestMaterialIdentity",
    "SuppliedFaultTestMaterial",
    "FaultTestRunIdentity",
    "ReportedFaultTestRun",
    "ReportedFaultTestOutcomeKind",
    "ReportedFaultTestOutcome",
    "FaultTestRunRevisionAssociation",
    "ReportedFaultTestComparison",
]


class FaultTestMaterialIdentity(RootModel[uuid.UUID]):
    """Caller-assigned name for one supplied test-material subject."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class SuppliedFaultTestMaterial(BaseModel):
    """Supplied test material or procedure for one published fault report."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    material: FaultTestMaterialIdentity
    report: SuppliedFaultReport
    test_statement: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]

    @field_validator("material", mode="before")
    @classmethod
    def _require_typed_python_material(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, FaultTestMaterialIdentity):
            raise ValueError(
                "material must be a FaultTestMaterialIdentity in Python input"
            )
        return value

    @field_validator("report", mode="before")
    @classmethod
    def _require_typed_python_report(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, SuppliedFaultReport):
            raise ValueError("report must be a SuppliedFaultReport in Python input")
        return value

    @field_validator("test_statement", mode="after")
    @classmethod
    def _require_unpadded_text(cls, value: str, info: ValidationInfo) -> str:
        if value != value.strip():
            raise ValueError(
                f"{info.field_name} must not have leading or trailing whitespace"
            )
        return value


class FaultTestRunIdentity(RootModel[uuid.UUID]):
    """Caller-assigned name for one reported test-run subject."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class ReportedFaultTestRun(BaseModel):
    """Caller-reported attempt to run one supplied test material."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    run: FaultTestRunIdentity
    test_material: SuppliedFaultTestMaterial
    run_statement: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]

    @field_validator("run", mode="before")
    @classmethod
    def _require_typed_python_run(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, FaultTestRunIdentity):
            raise ValueError("run must be a FaultTestRunIdentity in Python input")
        return value

    @field_validator("test_material", mode="before")
    @classmethod
    def _require_typed_python_test_material(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, SuppliedFaultTestMaterial):
            raise ValueError(
                "test_material must be a SuppliedFaultTestMaterial in Python input"
            )
        return value

    @field_validator("run_statement", mode="after")
    @classmethod
    def _require_unpadded_text(cls, value: str, info: ValidationInfo) -> str:
        if value != value.strip():
            raise ValueError(
                f"{info.field_name} must not have leading or trailing whitespace"
            )
        return value


class ReportedFaultTestOutcomeKind(StrEnum):
    """Bounded vocabulary of caller-reported execution dispositions."""

    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"
    DID_NOT_START = "did_not_start"
    CANCELLED = "cancelled"


class ReportedFaultTestOutcome(BaseModel):
    """Caller-reported disposition of one reported test run."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    run: ReportedFaultTestRun
    outcome: ReportedFaultTestOutcomeKind
    outcome_statement: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]

    @field_validator("run", mode="before")
    @classmethod
    def _require_typed_python_run(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ReportedFaultTestRun):
            raise ValueError("run must be a ReportedFaultTestRun in Python input")
        return value

    @field_validator("outcome", mode="before")
    @classmethod
    def _require_typed_python_outcome(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value,
            ReportedFaultTestOutcomeKind,
        ):
            raise ValueError(
                "outcome must be a ReportedFaultTestOutcomeKind in Python input"
            )
        return value

    @field_validator("outcome_statement", mode="after")
    @classmethod
    def _require_unpadded_text(cls, value: str, info: ValidationInfo) -> str:
        if value != value.strip():
            raise ValueError(
                f"{info.field_name} must not have leading or trailing whitespace"
            )
        return value


class FaultTestRunRevisionAssociation(BaseModel):
    """Supplied association from one reported run to one commit revision."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    run: ReportedFaultTestRun
    revision: GitCommitIdentity

    @field_validator("run", mode="before")
    @classmethod
    def _require_typed_python_run(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ReportedFaultTestRun):
            raise ValueError("run must be a ReportedFaultTestRun in Python input")
        return value

    @field_validator("revision", mode="before")
    @classmethod
    def _require_typed_python_revision(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, GitCommitIdentity):
            raise ValueError("revision must be a GitCommitIdentity in Python input")
        return value


class ReportedFaultTestComparison(BaseModel):
    """Supplied before-and-after relation over two reported outcomes."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    before: ReportedFaultTestOutcome
    after: ReportedFaultTestOutcome
    comparison_statement: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]

    @field_validator("before", "after", mode="before")
    @classmethod
    def _require_typed_python_outcome(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, ReportedFaultTestOutcome):
            raise ValueError(
                f"{info.field_name} must be a ReportedFaultTestOutcome in Python input"
            )
        return value

    @field_validator("comparison_statement", mode="after")
    @classmethod
    def _require_unpadded_text(cls, value: str, info: ValidationInfo) -> str:
        if value != value.strip():
            raise ValueError(
                f"{info.field_name} must not have leading or trailing whitespace"
            )
        return value

    @model_validator(mode="after")
    def _require_distinct_run_subjects(self) -> Self:
        if self.before.run.run == self.after.run.run:
            raise ValueError("before and after must report distinct run subjects")
        return self

    @model_validator(mode="after")
    def _require_one_supplied_test_material(self) -> Self:
        if self.before.run.test_material != self.after.run.test_material:
            raise ValueError(
                "before and after must report the same supplied test material"
            )
        return self
