"""Bounded composition of one fault's published records, with reference integrity.

This module publishes the first aggregate in the FaultInstance model. It
composes the values `S1.P06.S01` through `S1.P06.S07` already published and
redefines none of them: every member of every collection is a predecessor
value, admitted whole and unchanged, and this module adds no field of its own
to any of them.

What the aggregate owns is reference integrity, and only that. It refuses a
composition whose parts point at records the composition does not contain, and
it refuses one that names a single subject twice. It resolves nothing else. It
does not infer a missing record, choose among conflicting reported outcomes,
choose a winning explanation or hypothesis, infer causation, infer repair
correctness, infer evidence support, deduplicate by similarity, build a graph
or registry, or execute anything.

The logical subject is the fault, not a report. One fault may be described by
more than one supplied report, so the aggregate anchors on a
`FaultInstanceIdentity` and carries one or more reports whose own
`report.context.fault` equals it. Logical fault identity, report identity and
repository context therefore stay three separate things. Reports for one fault
may carry different repository contexts, and composing them asserts only that a
caller placed them under one fault subject: it claims no cross-repository
applicability, no shared code, and no relationship between those repositories.

A minimal instance is one identity and one substantive report. An identity
alone is not a fault instance, which is why `reports` requires at least one
member; every later layer is optional, and a composition carrying no scenario,
occurrence, source or history association, repair candidate, test material,
run, outcome, comparison, explanation, hypothesis or expected property is an
ordinary and complete value of this type. Gap tolerance is the design.

An absent collection says one thing only: this composition carries no values of
that category. It does not say that none exists, that none was found, that a
search was performed, that the category is unavailable, unsupported or
impossible, or that anything was disproved. These are membership collections
rather than completeness or evidence states, which is why an omitted collection
and an explicitly empty one are the same value and why no `None`, missing-state
vocabulary, or boolean stands beside them. Explicit `None` is refused, because
a null would invite exactly the reading the empty tuple refuses.

Nothing here claims completeness. A `FaultInstance` is a bounded composition,
never an assertion that every fact about the fault has been collected, so no
`complete`, `completeness`, `exhaustive`, `fully_observed`, `fully_reproduced`,
or `resolved` field exists.

Reference integrity is by whole published record, not by matching an embedded
identifier. Two records may carry one subject identity while disagreeing in
their supplied content, and a scalar match would silently pick one of them. So
a scenario's report must be an exact member of `reports`, an occurrence's
scenario an exact member of `scenarios`, a repair association's candidate an
exact member of `repair_candidates`, a run's test material an exact member of
`test_materials`, an outcome's run an exact member of `test_runs`, a
comparison's before and after exact members of `test_outcomes`, and every
report-anchored record's report an exact member of `reports`. A dangling
reference is refused rather than repaired: nothing is auto-inserted from the
value that referenced it.

Within one composition each primary subject identity occurs at most once in its
own collection, whether the two records are identical or contradictory. That is
local composition integrity and not a global registry: the same identity may be
composed again in another `FaultInstance`, and nothing here records that it
was. Uniqueness is per nominal identity type, so one UUID scalar may still name
a fault, a report, a scenario and a run at once, exactly as the published
identities allow. Collections without a subject identity of their own --
outcomes, comparisons, and every association -- carry no uniqueness rule,
because repetition there is a caller's supplied claim rather than a collision.

Conflicts survive composition. `S1.P06.S06` permits two outcome records to name
one run and disagree, so a composition carrying both is valid here and this
layer neither rejects the conflict, chooses a winner, marks the run flaky, nor
derives a confidence. Explanations and hypotheses with distinct identities may
contradict each other about one report, and several repair candidates may
address one report. Resolving any of that is `S1.P09` work.

Reference closure creates no semantic edge a predecessor did not publish. That
a report is associated with a pull request and a candidate with a change set
from it does not make the pull request support the candidate. That a candidate
revision equals a test run's revision does not make the run a test of the
candidate. A `failed` to `passed` comparison does not make a repair candidate
correct, a passing outcome does not verify an expected property, and an
explanation beside a candidate does not make it the reason for the repair.
Nothing here requires a candidate revision to equal a change set's head, a run
revision to equal a repair revision, a comparison's later revision to equal a
candidate revision, or a source object's repository to equal its report's:
those stay independent supplied relations and this module states no coherence
rule over them.

Order is preserved exactly as supplied and means nothing. This module neither
sorts nor canonicalises any collection, and position carries no priority,
confidence, causality, chronology, or ownership. Because tuple equality
includes order, two compositions of the same records in different orders are
unequal at this value layer; a canonical durable ordering is `S1.P10` work and
is deliberately not decided here.

No evidence is consumed. The evidence bridge is `S1.P06.S09` work, so no
durable record reference, history-fact evidence link, or snapshot evidence link
is imported or composed, and the `S1.P06.S04` associations stay the weak
associations they were published as rather than becoming support.

Each collection is bounded to a fixed maximum length. That bound limits one
in-memory composition and nothing else: it is not a claim that more records
cannot exist, and it is not a durable-format limit, which remains `S1.P10`
work. The bound is module-private and is not published.

The composition is closed to untyped Python input. The composed subject must
already be a published `FaultInstanceIdentity` rather than the scalar inside
one, every collection must be a tuple when it is supplied, and every member
must already be the published type it declares, so a bare UUID, a list, a
mapping, an attribute-backed lookalike, or a foreign model is refused even when
its content matches. JSON is a different input
language: there the declared members reconstruct normally and a semantic round
trip succeeds, while a Python round trip through `model_dump` deliberately does
not, because that projection has already turned typed children into mappings.

That closure is stated over the declared default validation policy, as every
published module here states it. Deliberately relaxing the policy is a
different question this module does not answer.

The module performs no I/O. It reads no clock, no environment and no
filesystem, opens no network connection, consults no registry, allocates no
identifier, resolves nothing, starts no process, and executes no analyzed
repository.
"""

import uuid
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from faultatlas.domain.fault import (
    FaultInstanceIdentity,
    SuppliedFaultOccurrenceContext,
    SuppliedFaultReport,
    SuppliedFaultScenario,
)
from faultatlas.domain.fault_interpretation import (
    SuppliedFaultExpectedProperty,
    SuppliedFaultExplanation,
    SuppliedFaultHypothesis,
)
from faultatlas.domain.fault_repair import (
    FaultRepairCandidateChangeSetAssociation,
    FaultRepairCandidateRevisionAssociation,
    SuppliedFaultRepairCandidate,
)
from faultatlas.domain.fault_source_relationship import (
    FaultReportHistoryFactAssociation,
    FaultReportSourceObjectAssociation,
)
from faultatlas.domain.fault_test import (
    FaultTestRunRevisionAssociation,
    ReportedFaultTestComparison,
    ReportedFaultTestOutcome,
    ReportedFaultTestRun,
    SuppliedFaultTestMaterial,
)

__all__ = [
    "FaultInstance",
]

# One in-memory composition is bounded here. The bound is not a claim about how
# many records may exist, and not a durable-format limit; it is private.
_MAX_MEMBERS = 4096


class FaultInstance(BaseModel):
    """Caller-composed bounded set of one fault's published records."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    fault: FaultInstanceIdentity
    reports: Annotated[
        tuple[SuppliedFaultReport, ...],
        Field(min_length=1, max_length=_MAX_MEMBERS),
    ]
    scenarios: Annotated[
        tuple[SuppliedFaultScenario, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    occurrences: Annotated[
        tuple[SuppliedFaultOccurrenceContext, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    source_object_associations: Annotated[
        tuple[FaultReportSourceObjectAssociation, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    history_fact_associations: Annotated[
        tuple[FaultReportHistoryFactAssociation, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    repair_candidates: Annotated[
        tuple[SuppliedFaultRepairCandidate, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    repair_revision_associations: Annotated[
        tuple[FaultRepairCandidateRevisionAssociation, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    repair_change_set_associations: Annotated[
        tuple[FaultRepairCandidateChangeSetAssociation, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    test_materials: Annotated[
        tuple[SuppliedFaultTestMaterial, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    test_runs: Annotated[
        tuple[ReportedFaultTestRun, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    test_outcomes: Annotated[
        tuple[ReportedFaultTestOutcome, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    test_run_revision_associations: Annotated[
        tuple[FaultTestRunRevisionAssociation, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    test_comparisons: Annotated[
        tuple[ReportedFaultTestComparison, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    explanations: Annotated[
        tuple[SuppliedFaultExplanation, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    hypotheses: Annotated[
        tuple[SuppliedFaultHypothesis, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    expected_properties: Annotated[
        tuple[SuppliedFaultExpectedProperty, ...],
        Field(max_length=_MAX_MEMBERS),
    ] = ()

    @field_validator("fault", mode="before")
    @classmethod
    def _require_typed_python_fault(cls, value: object, info: ValidationInfo) -> object:
        """The composed subject is a published identity, not a scalar.

        A `RootModel` field reconstructs from its own root type even under
        `strict=True`, so without this a bare `uuid.UUID` would be accepted
        here and the aggregate would be minting the identity rather than
        composing one a caller already published. Every predecessor closes its
        identity positions the same way. JSON stays a different input language:
        there the declared schema reconstructs normally.
        """
        if info.mode == "python" and not isinstance(value, FaultInstanceIdentity):
            raise ValueError("fault must be a FaultInstanceIdentity in Python input")
        return value

    @model_validator(mode="after")
    def _require_reports_name_the_composed_fault(self) -> Self:
        for index, report in enumerate(self.reports):
            if report.context.fault != self.fault:
                raise ValueError(
                    f"reports[{index}] describes a different fault subject"
                )
        return self

    @model_validator(mode="after")
    def _require_unique_primary_subjects(self) -> Self:
        """One subject identity appears at most once in its own collection.

        Two records naming one subject are refused whether they are identical
        or contradictory, because choosing between them is not this layer's
        judgement to make. Uniqueness is per nominal identity type, so one
        scalar may still name a report and a run at the same time.
        """
        subjects: tuple[tuple[str, tuple[uuid.UUID, ...]], ...] = (
            ("reports", tuple(record.report.root for record in self.reports)),
            ("scenarios", tuple(record.scenario.root for record in self.scenarios)),
            (
                "occurrences",
                tuple(record.occurrence.root for record in self.occurrences),
            ),
            (
                "repair_candidates",
                tuple(record.candidate.root for record in self.repair_candidates),
            ),
            (
                "test_materials",
                tuple(record.material.root for record in self.test_materials),
            ),
            ("test_runs", tuple(record.run.root for record in self.test_runs)),
            (
                "explanations",
                tuple(record.explanation.root for record in self.explanations),
            ),
            (
                "hypotheses",
                tuple(record.hypothesis.root for record in self.hypotheses),
            ),
            (
                "expected_properties",
                tuple(
                    record.expected_property.root for record in self.expected_properties
                ),
            ),
        )
        for name, identifiers in subjects:
            if len(set(identifiers)) != len(identifiers):
                raise ValueError(f"{name} names one subject identity more than once")
        return self

    @model_validator(mode="after")
    def _require_report_references_are_members(self) -> Self:
        """Every report-anchored record points at a report this composition has.

        Membership is by whole record. Two reports may share one identity while
        disagreeing in their supplied text, so matching the embedded identifier
        would silently choose one of them.
        """
        anchored: tuple[tuple[str, tuple[SuppliedFaultReport, ...]], ...] = (
            ("scenarios", tuple(record.report for record in self.scenarios)),
            (
                "source_object_associations",
                tuple(record.report for record in self.source_object_associations),
            ),
            (
                "history_fact_associations",
                tuple(record.report for record in self.history_fact_associations),
            ),
            (
                "repair_candidates",
                tuple(record.report for record in self.repair_candidates),
            ),
            (
                "test_materials",
                tuple(record.report for record in self.test_materials),
            ),
            ("explanations", tuple(record.report for record in self.explanations)),
            ("hypotheses", tuple(record.report for record in self.hypotheses)),
            (
                "expected_properties",
                tuple(record.report for record in self.expected_properties),
            ),
        )
        for name, referenced in anchored:
            for index, report in enumerate(referenced):
                if report not in self.reports:
                    raise ValueError(
                        f"{name}[{index}] references a report this composition "
                        f"does not carry"
                    )
        return self

    @model_validator(mode="after")
    def _require_layer_references_are_members(self) -> Self:
        """Every record pointing at a non-report layer points inside it.

        Nothing is auto-inserted: a referenced value the composition does not
        already carry makes the reference dangling, not the composition larger.
        """
        edges: tuple[tuple[str, tuple[object, ...], tuple[object, ...]], ...] = (
            (
                "occurrences",
                tuple(record.scenario for record in self.occurrences),
                self.scenarios,
            ),
            (
                "repair_revision_associations",
                tuple(record.candidate for record in self.repair_revision_associations),
                self.repair_candidates,
            ),
            (
                "repair_change_set_associations",
                tuple(
                    record.candidate for record in self.repair_change_set_associations
                ),
                self.repair_candidates,
            ),
            (
                "test_runs",
                tuple(record.test_material for record in self.test_runs),
                self.test_materials,
            ),
            (
                "test_outcomes",
                tuple(record.run for record in self.test_outcomes),
                self.test_runs,
            ),
            (
                "test_run_revision_associations",
                tuple(record.run for record in self.test_run_revision_associations),
                self.test_runs,
            ),
            (
                "test_comparisons.before",
                tuple(record.before for record in self.test_comparisons),
                self.test_outcomes,
            ),
            (
                "test_comparisons.after",
                tuple(record.after for record in self.test_comparisons),
                self.test_outcomes,
            ),
        )
        for name, referenced, members in edges:
            for index, value in enumerate(referenced):
                if value not in members:
                    raise ValueError(
                        f"{name}[{index}] references a value this composition "
                        f"does not carry"
                    )
        return self
