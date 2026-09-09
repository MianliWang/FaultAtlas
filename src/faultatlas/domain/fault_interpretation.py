"""Case-local supplied explanation, hypothesis, and expected property.

This module publishes three kinds of caller-supplied knowledge about one
published fault report, and deliberately keeps them apart because they are
three different epistemic acts. An explanation is an account a caller offers of
why or how the reported behavioral deviation arises. A hypothesis is a
proposition a caller explicitly retains as tentative. An expected property is a
statement of behavior a caller says ought to hold for this report. Each is a
claim someone made; none is a finding this system reached.

Nothing here is promoted by being represented. Constructing any of these three
records does not make it an observed fact, a deterministic derivation, a
reviewed interpretation, a verified root cause, an evidence-backed conclusion,
or a reusable pattern or invariant. The record says a caller supplied it, and
stops there.

A report may carry none, one, or several of each kind, and the three counts are
independent: a report with four hypotheses and no explanation is an ordinary
state, and so is a report with an expected property and nothing else. Nothing
requires a reproduction, scenario, occurrence, repair candidate, test material,
reported run, or reported outcome to exist before any of these values can be
built, because a caller can explain, hypothesise, or state an expectation
before anything has been run or reproduced.

The three identities are three further independent UUID-rooted values, each
neither a subclass nor an alias of the others or of the fault, report,
scenario, occurrence, repair-candidate, test-material, and run identities. All
ten stay nominally distinct even when one scalar is assigned to all ten. The
caller assigns each UUID; nothing generates, derives, reserves, looks up,
deduplicates, merges, or registers one, no identifier is derived from content,
and none is an authorization token or a security boundary. Nil and Max are
ordinary admitted values rather than sentinels, no generation version is
required or inferred, the JSON form of each is the ordinary bare UUID string
with no wrapper or adapter, and equality, hashing and ordering are left exactly
as Pydantic defines them.

An explanation is a supplied explanatory claim, not a promoted fact. It may
describe why or how the deviation arises, and it may carry an account that is
root-cause shaped -- a caller naming a mechanism is doing exactly what this
record is for. What it may not do is assert that the root cause is therefore
established, that the account was accepted, reviewed, supported, or verified,
or that it is more probable than any hypothesis about the same report. There is
no `root_cause`, `accepted`, `verified`, `confidence`, or `review` field,
because each would record a judgement no one made here.

A hypothesis stays a hypothesis. It may propose a possible cause, a mechanism,
a condition, an account reconciling conflicting observations, or a prediction,
and it remains explicitly tentative merely by being represented in this
position. No `confirmed`, `rejected`, `supported`, `disproved`, `probability`,
`confidence`, `review`, or `evidence` field exists, so the record cannot carry
its own resolution. A later success does not prove an earlier hypothesis, and a
hypothesis used as fixture material in this repository is a supplied
proposition there too, never a historical fact promoted by appearing in a test.

An expected property is case-local. Its carrier scopes it to exactly one
supplied fault report, and that scoping is the whole point: the property is
what a caller expects of this case, not a law about programs. It may express
behavior about return values, exceptions, evaluation count, execution order,
side-effect count or order, resource behavior, or timing behavior. It is not a
passing test, a verified invariant, a universal program law, a cross-instance
pattern, a repair acceptance criterion, or proof that the current behavior is
wrong. Generalising a case-local property across instances is `S1.P07` work and
is not begun here.

Nothing inspects the prose to decide whether it sounds broad. No natural
language is parsed, scope-checked, or classified anywhere in this module, so a
caller who writes a sweeping sentence has still supplied one case-local record
and nothing more; breadth of phrasing is not breadth of claim.

The three kinds do not convert into one another. There is no promotion,
lifecycle, or transition from hypothesis to explanation, and none in the other
direction. The same prose may appear as a hypothesis and as an explanation
while the two records stay distinct, because they carry different identities
and different epistemic roles; identical explanation and expected-property text
is structurally permitted for the same reason. One report may carry several
explanations or hypotheses that contradict each other, and this layer chooses
no winner: no uniqueness, precedence, replacement, supersession, or conflict
resolution exists here. Bounded composition and reference integrity are
`S1.P06.S08` work, generic review and confidence are `S1.P09` work, and the
fault-evidence bridge is `S1.P06.S09` work.

Nothing is inferred from the repair or test layers. That a repair candidate
exists does not make an explanation true; that a candidate carries a revision
does not make a root cause known; a reported `failed` to `passed` comparison
neither confirms an explanation nor verifies an expected property; a reported
`passed` outcome does not satisfy an expected property universally; a later
reported success does not disprove an earlier hypothesis; and a merge accepts
nothing. This module publishes no relation at all to repair candidates, test
material, reported runs, outcomes, comparisons, source objects, history facts,
or evidence records, and co-presence in one repository manufactures none.

Both model-valued positions of every record are closed to untyped Python input.
A caller must supply an already typed value; a raw UUID, a string, a mapping,
an attribute-backed lookalike, or a foreign model is refused even when its
scalar content matches, because constructing a published identity or report is
that value's own responsibility. A top-level mapping validated with
`from_attributes=True` does not bypass those guards. JSON is a different input
language: there the declared child schemas reconstruct normally, so a semantic
JSON round trip succeeds while a Python round trip through `model_dump`
deliberately does not, and each embedded value is revalidated under its own
published schema so a tampered child is refused at its own position. No field
declares an input or output alias, and no field is optional or nullable, so an
absent claim is an absent record rather than a null.

Every supplied text here is a claim handled as opaque prose under one shared
rule stated separately on each field rather than through a shared alias or base.
Each must be present, non-blank, and at most 4096 characters; leading or
trailing whitespace is refused rather than trimmed, so whitespace-only text
fails, and a value that cannot encode as UTF-8 is refused. Admitted Unicode and
interior whitespace, including newlines, are preserved exactly: nothing
lowercases, normalizes, parses, tokenizes, classifies, or rewrites it, and
nothing decides whether what it says is true, sufficient, or correct. The 4096
limit is a character bound of this internal contract, not a durable byte-format
promise.

That closure is stated over the declared default validation policy, as every
published module here states it. Deliberately relaxing the policy is a
different question this module does not answer: `strict=False`, an altered
`extra` setting, a schema or serializer override, and the string-parsing entry
point are not entry points designed here.

The module performs no I/O. It reads no clock, allocates no identifier,
consults no registry or environment, resolves nothing, opens no file or
network connection, mutates no filesystem, starts no process, and executes no
analyzed repository.
"""

import uuid
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    RootModel,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from faultatlas.domain.fault import SuppliedFaultReport

__all__ = [
    "FaultExplanationIdentity",
    "SuppliedFaultExplanation",
    "FaultHypothesisIdentity",
    "SuppliedFaultHypothesis",
    "FaultExpectedPropertyIdentity",
    "SuppliedFaultExpectedProperty",
]


class FaultExplanationIdentity(RootModel[uuid.UUID]):
    """Caller-assigned name for one supplied explanation record."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class SuppliedFaultExplanation(BaseModel):
    """Caller-supplied explanatory account of one published fault report."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    explanation: FaultExplanationIdentity
    report: SuppliedFaultReport
    explanation_statement: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]

    @field_validator("explanation", mode="before")
    @classmethod
    def _require_typed_python_explanation(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, FaultExplanationIdentity):
            raise ValueError(
                "explanation must be a FaultExplanationIdentity in Python input"
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

    @field_validator("explanation_statement", mode="after")
    @classmethod
    def _require_unpadded_text(cls, value: str, info: ValidationInfo) -> str:
        if value != value.strip():
            raise ValueError(
                f"{info.field_name} must not have leading or trailing whitespace"
            )
        return value


class FaultHypothesisIdentity(RootModel[uuid.UUID]):
    """Caller-assigned name for one supplied hypothesis record."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class SuppliedFaultHypothesis(BaseModel):
    """Caller-supplied tentative proposition about one published fault report."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    hypothesis: FaultHypothesisIdentity
    report: SuppliedFaultReport
    hypothesis_statement: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]

    @field_validator("hypothesis", mode="before")
    @classmethod
    def _require_typed_python_hypothesis(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, FaultHypothesisIdentity):
            raise ValueError(
                "hypothesis must be a FaultHypothesisIdentity in Python input"
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

    @field_validator("hypothesis_statement", mode="after")
    @classmethod
    def _require_unpadded_text(cls, value: str, info: ValidationInfo) -> str:
        if value != value.strip():
            raise ValueError(
                f"{info.field_name} must not have leading or trailing whitespace"
            )
        return value


class FaultExpectedPropertyIdentity(RootModel[uuid.UUID]):
    """Caller-assigned name for one supplied expected-property record."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class SuppliedFaultExpectedProperty(BaseModel):
    """Caller-supplied case-local expectation for one published fault report."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    expected_property: FaultExpectedPropertyIdentity
    report: SuppliedFaultReport
    expected_property_statement: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]

    @field_validator("expected_property", mode="before")
    @classmethod
    def _require_typed_python_expected_property(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value,
            FaultExpectedPropertyIdentity,
        ):
            raise ValueError(
                "expected_property must be a FaultExpectedPropertyIdentity in "
                "Python input"
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

    @field_validator("expected_property_statement", mode="after")
    @classmethod
    def _require_unpadded_text(cls, value: str, info: ValidationInfo) -> str:
        if value != value.strip():
            raise ValueError(
                f"{info.field_name} must not have leading or trailing whitespace"
            )
        return value
