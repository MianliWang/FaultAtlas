"""Bounded caller composition of one supplied pattern and explicit relations.

The complete supplied pattern is the root. A pattern alone is valid; empty
collections mean only that this composition carries no values of that category,
not known absence, failed search, disproof or completeness. Each collection's
private bound limits this in-memory value, not the world or a durable format.

Root references and invariant membership use full published record equality.
Invariant identities are unique locally, and every carried invariant needs an
explicit relationship to the root. Nothing is inserted, replaced or reconciled.
Duplicate relationship values remain supplied repetitions, not independent
support. An expectation's case need not be an exemplar, and an exemplar needs
no expectation chain. The S02/S04 owners validate their nested case values.

No inferred or transitive edge, evidence propagation, truth, recurrence,
similarity, generality, satisfaction, violation, causation or repair correctness
is established. Applicability/transfer remains P08, support/confidence/review
P09, durable interchange/persistence P10, and extraction later runtime work.
Order is preserved and affects value equality, but encodes no priority,
chronology, confidence, causality, support strength or preference. No sorting
or durable canonicalization is performed.

Python requires typed children and strict tuples; JSON reconstructs through
the published owning schemas. No filesystem, repository, network, environment,
clock, process, model, identifier allocation, discovery or supplied-code
execution occurs. No global registry or cross-composition policy is added.
"""

from typing import Annotated, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from faultatlas.domain.invariant import SuppliedFaultInvariant
from faultatlas.domain.invariant_relationship import (
    FaultInvariantExpectedPropertyAssociation,
    FaultPatternInvariantAssociation,
)
from faultatlas.domain.pattern import SuppliedFaultPattern
from faultatlas.domain.pattern_exemplar import FaultPatternExemplarAssociation

__all__ = ["FaultPatternComposition"]

_MAX_MEMBERS = 4096


def _require_exemplar(value: object, info: ValidationInfo) -> object:
    if info.mode == "python" and not isinstance(value, FaultPatternExemplarAssociation):
        raise ValueError("Python exemplar must be a FaultPatternExemplarAssociation")
    return value


def _require_invariant(value: object, info: ValidationInfo) -> object:
    if info.mode == "python" and not isinstance(value, SuppliedFaultInvariant):
        raise ValueError("Python invariant must be a SuppliedFaultInvariant")
    return value


def _require_pattern_invariant(value: object, info: ValidationInfo) -> object:
    if info.mode == "python" and not isinstance(
        value, FaultPatternInvariantAssociation
    ):
        raise ValueError("Python relation must be a FaultPatternInvariantAssociation")
    return value


def _require_invariant_expectation(value: object, info: ValidationInfo) -> object:
    if info.mode == "python" and not isinstance(
        value, FaultInvariantExpectedPropertyAssociation
    ):
        raise ValueError(
            "Python relation must be a FaultInvariantExpectedPropertyAssociation"
        )
    return value


class FaultPatternComposition(BaseModel):
    """One supplied pattern with locally closed, explicit predecessor values."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    pattern: SuppliedFaultPattern
    exemplar_associations: Annotated[
        tuple[
            Annotated[
                FaultPatternExemplarAssociation, BeforeValidator(_require_exemplar)
            ],
            ...,
        ],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    invariants: Annotated[
        tuple[
            Annotated[SuppliedFaultInvariant, BeforeValidator(_require_invariant)], ...
        ],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    pattern_invariant_associations: Annotated[
        tuple[
            Annotated[
                FaultPatternInvariantAssociation,
                BeforeValidator(_require_pattern_invariant),
            ],
            ...,
        ],
        Field(max_length=_MAX_MEMBERS),
    ] = ()
    invariant_expected_property_associations: Annotated[
        tuple[
            Annotated[
                FaultInvariantExpectedPropertyAssociation,
                BeforeValidator(_require_invariant_expectation),
            ],
            ...,
        ],
        Field(max_length=_MAX_MEMBERS),
    ] = ()

    @field_validator("pattern", mode="before")
    @classmethod
    def _require_pattern(cls, value: object, info: ValidationInfo) -> object:
        if info.mode == "python" and not isinstance(value, SuppliedFaultPattern):
            raise ValueError("pattern must be a SuppliedFaultPattern in Python input")
        return value

    @model_validator(mode="after")
    def _require_reference_integrity(self) -> Self:
        # Identity locates a candidate only; every reference compares full values.
        members = {value.invariant: value for value in self.invariants}
        if len(members) != len(self.invariants):
            raise ValueError("invariants names one identity more than once")

        for index, exemplar in enumerate(self.exemplar_associations):
            if exemplar.pattern != self.pattern:
                raise ValueError(
                    f"exemplar_associations[{index}] has a different pattern"
                )

        unattached = set(members)
        for index, association in enumerate(self.pattern_invariant_associations):
            if association.pattern != self.pattern:
                raise ValueError(
                    f"pattern_invariant_associations[{index}] has a different pattern"
                )
            if members.get(association.invariant.invariant) != association.invariant:
                raise ValueError(
                    f"pattern_invariant_associations[{index}] references a nonmember invariant"
                )
            unattached.discard(association.invariant.invariant)
        if unattached:
            raise ValueError(
                "invariants contains a value not attached to the root pattern"
            )

        for index, association in enumerate(
            self.invariant_expected_property_associations
        ):
            if members.get(association.invariant.invariant) != association.invariant:
                raise ValueError(
                    f"invariant_expected_property_associations[{index}] references a nonmember invariant"
                )
        return self
