"""Caller designation of a complete supplied case as a pattern exemplar.

Both endpoints retain their supplied content. Naming a pattern or fault alone
does not select that content; equal identifiers with different endpoint values
therefore remain distinct association values. Equality uses the owning models'
ordinary value contracts, including tuple order, without normalization.

This designation does not verify matching, recurrence, similarity, causation,
case equivalence, invariant truth, applicability, transfer, support, confidence,
review, or repair correctness. It does not assert that every nested report or
interpretation instantiates the pattern or is true. No nested source, history,
evidence, outcome, or expected-property claim is promoted to a pattern claim.

Separate links may share either endpoint, within or across repositories,
including a multi-repository case. Neither a second case nor a second repository
is required. Repetition does not establish independent observations. No inverse
or transitive relation, uniqueness, ordering, or completeness policy is added.
A proposition without links stays valid; missing links imply no negative fact.

Python endpoints must already have their declared types and are revalidated by
their owners. JSON reconstructs them through the published native language; it
is not a new durable interchange format. Ordinary subclasses normalize to the
declared base values. No object-identity or validation-policy-override guarantee
is made. Revalidating a bounded case retains its predecessor's costs.

Invariants remain later P07 work, applicability/transfer P08, generic support,
confidence/review P09, persistence P10, and extraction later runtime work. This
module performs no I/O, discovery, clock/environment reads, identifier
allocation, process execution, or external-repository execution.
"""

import json

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from faultatlas.domain.fault_instance import FaultInstance
from faultatlas.domain.pattern import SuppliedFaultPattern

__all__ = ["FaultPatternExemplarAssociation"]


class FaultPatternExemplarAssociation(BaseModel):
    """The caller designates this supplied case for this supplied proposition."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    pattern: SuppliedFaultPattern
    fault_instance: FaultInstance

    @field_validator("pattern", mode="before")
    @classmethod
    def _require_typed_python_pattern(
        cls, value: object, info: ValidationInfo
    ) -> object:
        if info.mode == "python" and not isinstance(value, SuppliedFaultPattern):
            raise ValueError("pattern must be a SuppliedFaultPattern in Python input")
        return value

    @field_validator("fault_instance", mode="before")
    @classmethod
    def _require_typed_python_fault_instance(
        cls, value: object, info: ValidationInfo
    ) -> object:
        # A before-guard materializes JSON arrays as lists. Delegate the JSON
        # dictionary to the owner's strict tuple grammar, as the P06 bridge
        # does, without rewriting collections or bypassing its constraints.
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
