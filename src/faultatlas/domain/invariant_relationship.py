"""Explicit associations among supplied propositions and a composed expectation.

A pattern-invariant link records only that the caller associates these complete
propositions. It assigns no logical role: no violation, preservation, entailment,
proof, derivation, definition, necessary/sufficient condition or matching rule.
It needs no case, expectation, exemplar or evidence, and neither proposition
needs a link to exist independently.

An invariant-expected-property link records the caller's association with one
exact case-local expectation in this supplied composition. After owner validation,
the selected expectation must be a full-record-equal member of the case's
expected-properties collection. Equal independently constructed records qualify;
matching only an identifier, text or report does not. No record is inserted,
substituted or modified, and no lookup occurs outside this case. The case owner
already checks its report references; this module does not repeat that algorithm.
Any included report of a valid multi-repository case may carry the member.

Membership establishes placement, not semantic truth. The expectation remains
case-local and the invariant remains a supplied proposition. Disagreeing or false
prose is admitted without proving instantiation, specialization, entailment,
satisfaction, violation, support or generalization. A standalone expectation
remains valid outside a composition; only this link requires its inclusion.

Ordinary canonical base-value equality includes every field, all supplied text,
and the complete case's tuple order/content. Separate links can share either
endpoint across cases or repositories without global uniqueness, deduplication,
replacement, supersession, winner selection, ordering or completeness. Equal
hashable values have equal hashes; unequal ones may collide. Hash is not a
durable identifier. Missing links imply no negative fact, and duplicates are not
independent observations.

These links create no exemplar, inverse, transitive or case-to-case relation.
Sharing an invariant merges no patterns. An exemplar and a pattern-invariant link
create no links to case expectations; a case expectation's evidence association
does not transfer to a proposition. No inferred support, confidence, review,
applicability, transfer, counterexample, refinement or repair-correctness result
exists. Composition and accumulated vertical assurance remain later P07 work;
P08/P09/P10 and later runtime ownership are unchanged.

Python requires typed endpoints and owners revalidate them. Native JSON delegates
only the case dictionary to its owning validator, preserving strict tuples and
all inherited constraints. Ordinary subclasses normalize; object identity and
explicit validation-policy/schema overrides are not promised. The full-member
search is bounded, but construction also retains predecessor revalidation costs.
This module performs no I/O, clock/environment access, allocation, process/model
execution, supplied-code interpretation, discovery, caching or external execution.
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

from faultatlas.domain.fault_instance import FaultInstance
from faultatlas.domain.fault_interpretation import SuppliedFaultExpectedProperty
from faultatlas.domain.invariant import SuppliedFaultInvariant
from faultatlas.domain.pattern import SuppliedFaultPattern

__all__ = [
    "FaultPatternInvariantAssociation",
    "FaultInvariantExpectedPropertyAssociation",
]


class FaultPatternInvariantAssociation(BaseModel):
    """Caller association of two full propositions, without a logical role."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    pattern: SuppliedFaultPattern
    invariant: SuppliedFaultInvariant

    @field_validator("pattern", mode="before")
    @classmethod
    def _require_typed_python_pattern(
        cls, value: object, info: ValidationInfo
    ) -> object:
        if info.mode == "python" and not isinstance(value, SuppliedFaultPattern):
            raise ValueError("pattern must be a SuppliedFaultPattern in Python input")
        return value

    @field_validator("invariant", mode="before")
    @classmethod
    def _require_typed_python_invariant(
        cls, value: object, info: ValidationInfo
    ) -> object:
        if info.mode == "python" and not isinstance(value, SuppliedFaultInvariant):
            raise ValueError(
                "invariant must be a SuppliedFaultInvariant in Python input"
            )
        return value


class FaultInvariantExpectedPropertyAssociation(BaseModel):
    """Caller association with one exact expectation in a supplied case."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    invariant: SuppliedFaultInvariant
    fault_instance: FaultInstance
    expected_property: SuppliedFaultExpectedProperty

    @field_validator("invariant", mode="before")
    @classmethod
    def _require_typed_python_invariant(
        cls, value: object, info: ValidationInfo
    ) -> object:
        if info.mode == "python" and not isinstance(value, SuppliedFaultInvariant):
            raise ValueError(
                "invariant must be a SuppliedFaultInvariant in Python input"
            )
        return value

    @field_validator("fault_instance", mode="before")
    @classmethod
    def _require_typed_python_fault_instance(
        cls, value: object, info: ValidationInfo
    ) -> object:
        # A before-guard materializes JSON arrays. Let the owner reconstruct its
        # strict tuples and validate its full constraints, without rewriting data.
        if info.mode == "json" and isinstance(value, dict):
            try:
                encoded = json.dumps(value)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "fault_instance must be a composition in JSON input"
                ) from error
            return FaultInstance.model_validate_json(encoded)
        if info.mode == "python" and not isinstance(value, FaultInstance):
            raise ValueError("fault_instance must be a FaultInstance in Python input")
        return value

    @field_validator("expected_property", mode="before")
    @classmethod
    def _require_typed_python_expected_property(
        cls, value: object, info: ValidationInfo
    ) -> object:
        if info.mode == "python" and not isinstance(
            value, SuppliedFaultExpectedProperty
        ):
            raise ValueError(
                "expected_property must be a SuppliedFaultExpectedProperty in Python input"
            )
        return value

    @model_validator(mode="after")
    def _require_full_expected_property_member(self) -> Self:
        if self.expected_property not in self.fault_instance.expected_properties:
            raise ValueError(
                "expected_property is not a full-record member of fault_instance.expected_properties"
            )
        return self
