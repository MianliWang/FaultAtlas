"""Association between one composed fault record and one evidence record.

This module owns the single cross-domain relation between the published
`S1.P06` fault-knowledge layer and the published durable evidence-record
reference. Neither side changes: `S1.P06.S08` keeps its exact published
seventeen-field surface and gains no evidence field, the evidence layer stays
unchanged, and the relation lives here rather than in either domain module.
Turning one bounded knowledge composition into an implicit evidence graph is
exactly what that separation refuses.

The claim is exactly one level deep, and it is the same weak, uniform claim the
published history-fact and snapshot-fact evidence links already make. A link
records that its caller associated one substantive record already composed
inside one supplied `FaultInstance` with one supplied durable evidence-record
reference, and nothing else. It does not claim that the referenced record was
read, parsed, or inspected, that the record contains, corroborates, supports,
derives, verifies, or proves the subject, that the subject was observed in that
record, or that the subject is correct, true, verified, or authoritative. It
does not raise confidence, confirm a hypothesis, accept an explanation,
establish that a repair candidate is correct, or establish that a reported test
run was independently reproduced. No support role, strength, status,
confidence, review state, or verification outcome is recorded, and every
association carries the same meaning. Generic support, confidence and review
remain `S1.P09` work.

The subject position admits exactly the eleven substantive record types
`S1.P06.S01` through `S1.P06.S07` publish: a supplied report, scenario,
occurrence context, repair candidate or test material; a reported test run,
outcome or comparison; and a supplied explanation, hypothesis or expected
property. Each is reused whole and unchanged, and this module adds no field to
any of them.

Everything else is excluded, and the exclusions are the boundary rather than an
oversight. The `FaultInstance` aggregate itself is excluded: it is a caller's
bounded composition rather than a substantive claim, so associating a record
with it would attach evidence to the act of composing. `FaultInstanceIdentity`
and every other identity are excluded, because a name is not a record and a
UUID scalar carries no content a record could bear on. The five association
records `S1.P06.S04` through `S1.P06.S06` publish -- report to source object,
report to history fact, candidate to revision, candidate to change set, and run
to revision -- are excluded because they are themselves weak caller-declared
relations, and evidence attached to a relation about records rather than to the
records would be a claim about the caller's own act of associating. The
published history-fact and snapshot-fact evidence links are excluded for the
same reason and because each remains the authority for its own domain.
`PullRequestChangeSet` and the repository, snapshot and history aggregate
values are excluded because they are not `S1.P06` knowledge records at all.

The subject must already be an exact member of the supplied composition.
Membership is by whole published record, exactly as `S1.P06.S08` decides its
own reference integrity, and for the same reason: two records may carry one
subject identity while disagreeing in their supplied content, so matching an
embedded UUID, report identity, run identity or subject identity would silently
associate evidence with a record the caller did not supply. A same-identity
record that differs anywhere else is a different record and is refused. Each
admitted type is checked against the one collection that carries it, and a
subject the composition does not carry is refused rather than repaired: nothing
is auto-inserted, and the supplied `FaultInstance` is never mutated,
reconstructed, or returned altered.

No association chaining exists, and this boundary is load-bearing. That a
composition carries a report associated with a history fact, and that the same
history fact is elsewhere associated with a durable record, does not associate
the report with that record. That a report is associated with a pull request
and a repair candidate with a change set from it manufactures no evidence
linkage for the candidate. Every such chain stays exactly as long as the links
a caller explicitly supplied, and no link of this type is ever derived,
inferred, computed, or returned by anything here. Constructing one is the
caller's separate and deliberate act.

The referenced record is identified as a whole. There is no evidence
identifier, strength, support role, confidence, verification state, kind, field
pointer, JSON pointer, semantic path, byte span, locator, artifact path, or
request that would locate the subject inside the record, and byte offsets are
not a substitute for one. The link does not say where inside the record the
subject can be found, or that it can be found there at all.

Each link carries exactly one subject and one record. Associating one subject
with several records is several independent link values, and one record may be
associated with several subjects the same way. Two identical links are simply
equal values. No registry, collection model, ordering, precedence, uniqueness,
deduplication, or completeness semantics over multiple links exists here.
Absence of a link says one thing only: none is supplied here. It does not say
that the subject is unsupported, that no evidence exists, that a search was
performed and found nothing, or that anything was disproved.

All three positions are closed to untyped Python input. A caller must supply
already published values; a mapping, an attribute-backed lookalike, a foreign
model, a bare UUID, or a string is refused even when its own children are
published values, because constructing a published record is the predecessor
layer's responsibility and not this relation's. Strictness alone cannot express
that: a strict constraint is not applicable to a union schema, a strict union
still admits a mapping whose children are typed, and a strict model field still
admits one too, so each position carries its own guard and `from_attributes`
cannot bypass them.

JSON stays a different input language: there the declared values reconstruct
normally, each admitted type reconstructs preserving its own exact type and
value, and a semantic round trip succeeds. One transport step is required to
keep that true, and exactly one is performed. A guard standing above a value
hands its result back as an already materialized Python object, and the
composed collections `S1.P06.S08` declares are tuples, which a strict schema
refuses to read from the lists a parsed array produces. So in JSON input the
composition is reconstructed by the published aggregate's own JSON grammar
rather than rewritten here. Delegating decides nothing: the aggregate applies
every bound, uniqueness rule and reference-integrity rule it declares, and this
module accepts and refuses exactly the durable forms it does. Rewriting the
supplied payload instead -- turning every parsed array into a tuple -- would
decide something, because it would assume a shape no published schema states,
and would silently corrupt any position a predecessor declares as a list. No
admitted subject and no evidence reference carries a leaf whose durable form
differs from its Python form, so nothing else is decoded and no other transport
exists here.

Validating one link performs one bounded membership check against one
collection of the supplied composition. `S1.P06.S08` records separately that
its own reference-integrity validation can become expensive near its published
bound; that is an implementation cost of the predecessor and is not repaired,
changed, or newly guaranteed here. This module states no complexity guarantee.

The module performs no I/O. It reads no clock, no environment and no
filesystem, opens no network connection, consults no registry, allocates no
identifier, resolves nothing, starts no process, never inspects the record it
references, and executes no analyzed repository.
"""

import json
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
    model_validator,
)

from faultatlas.domain.evidence import DurableEvidenceRecordReference
from faultatlas.domain.fault import (
    SuppliedFaultOccurrenceContext,
    SuppliedFaultReport,
    SuppliedFaultScenario,
)
from faultatlas.domain.fault_instance import FaultInstance
from faultatlas.domain.fault_interpretation import (
    SuppliedFaultExpectedProperty,
    SuppliedFaultExplanation,
    SuppliedFaultHypothesis,
)
from faultatlas.domain.fault_repair import SuppliedFaultRepairCandidate
from faultatlas.domain.fault_test import (
    ReportedFaultTestComparison,
    ReportedFaultTestOutcome,
    ReportedFaultTestRun,
    SuppliedFaultTestMaterial,
)

__all__ = [
    "FaultInstanceEvidenceLink",
]

_AdmittedSubject = (
    SuppliedFaultReport
    | SuppliedFaultScenario
    | SuppliedFaultOccurrenceContext
    | SuppliedFaultRepairCandidate
    | SuppliedFaultTestMaterial
    | ReportedFaultTestRun
    | ReportedFaultTestOutcome
    | ReportedFaultTestComparison
    | SuppliedFaultExplanation
    | SuppliedFaultHypothesis
    | SuppliedFaultExpectedProperty
)

# Each admitted subject type and the one composed collection that must already
# carry it. Membership is decided by whole-record equality against that
# collection, so this mapping selects where to look and never what to accept.
_SUBJECT_COLLECTIONS: dict[type[BaseModel], str] = {
    SuppliedFaultReport: "reports",
    SuppliedFaultScenario: "scenarios",
    SuppliedFaultOccurrenceContext: "occurrences",
    SuppliedFaultRepairCandidate: "repair_candidates",
    SuppliedFaultTestMaterial: "test_materials",
    ReportedFaultTestRun: "test_runs",
    ReportedFaultTestOutcome: "test_outcomes",
    ReportedFaultTestComparison: "test_comparisons",
    SuppliedFaultExplanation: "explanations",
    SuppliedFaultHypothesis: "hypotheses",
    SuppliedFaultExpectedProperty: "expected_properties",
}

_ADMITTED_SUBJECT_TYPES: tuple[type[BaseModel], ...] = tuple(_SUBJECT_COLLECTIONS)


class FaultInstanceEvidenceLink(BaseModel):
    """Supplied association from one composed record to one durable record."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    fault_instance: FaultInstance
    subject: _AdmittedSubject
    evidence_record: DurableEvidenceRecordReference

    @field_validator("fault_instance", mode="before")
    @classmethod
    def _require_typed_python_fault_instance(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        """Typed in Python input; read by the aggregate's own grammar in JSON.

        Standing here at all materializes the parsed payload, and the composed
        collections are tuples a strict schema will not read from the lists an
        array parses to. Reconstructing through the published aggregate leaves
        every rule it declares to it, rather than assuming a shape here. The
        published evidence layer already decodes an embedded snapshot this way
        and this follows it.

        The reconstruction is reached by what the value is, not merely by what
        the ambient input language is. A mode reports the language a whole
        document arrived in, not the provenance of one value inside it: a
        published composition can reach this position while that language is
        not Python, and string input is a third language again. Only a mapping
        read from JSON is a parsed composition, so only that is decoded, and
        anything else is left for the declared schema to accept or refuse.
        A mapping that has no durable form at all is refused as one more
        invalid input rather than escaping as an encoder error a caller
        catching a validation failure would never see.
        """
        if info.mode == "json" and isinstance(value, dict):
            try:
                encoded = json.dumps(value)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "fault_instance must be a durable composition in JSON input"
                ) from error
            return FaultInstance.model_validate_json(encoded)
        if info.mode == "python" and not isinstance(value, FaultInstance):
            raise ValueError("fault_instance must be a FaultInstance in Python input")
        return value

    @field_validator("subject", mode="before")
    @classmethod
    def _require_typed_python_subject(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(value, _ADMITTED_SUBJECT_TYPES):
            raise ValueError(
                "subject must be an admitted published S1.P06 record in Python input"
            )
        return value

    @field_validator("evidence_record", mode="before")
    @classmethod
    def _require_typed_python_evidence_record(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value,
            DurableEvidenceRecordReference,
        ):
            raise ValueError(
                "evidence_record must be a DurableEvidenceRecordReference in "
                "Python input"
            )
        return value

    @model_validator(mode="after")
    def _require_subject_is_composed_member(self) -> Self:
        """The subject is already an exact whole record of the composition.

        Two records may carry one subject identity while disagreeing in their
        supplied content, so a same-identity match would associate evidence
        with a record the caller did not supply. Nothing is auto-inserted: a
        subject the composition does not carry makes the link invalid, not the
        composition larger.
        """
        collection = _SUBJECT_COLLECTIONS[type(self.subject)]
        if self.subject not in getattr(self.fault_instance, collection):
            raise ValueError(f"subject is not a member of fault_instance.{collection}")
        return self
