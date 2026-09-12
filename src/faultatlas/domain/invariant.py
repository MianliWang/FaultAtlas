"""Independent caller-supplied identity and reusable-property proposition.

The caller supplies a property asserted or required to remain satisfied
throughout the situations or operations described by its text. This records
the proposition, not its truth. A property remaining satisfied does not mean
that every variable or program value must stay constant.

A pattern proposes a recurring fault abstraction; this value proposes a
property to maintain; a case-local expected property stays attached to its
particular report. Identical wording does not convert those kinds. No pattern,
case, exemplar, expected property, evidence, proof or observed violation is
required, consumed or created, and no prior record is promoted here.

Conditions, observation points and exceptions may be retained as opaque text.
Nothing parses, classifies, evaluates or repairs their meaning, requires an
English template, or interprets missing conditions as universal applicability.
False or competing propositions are representable without choosing a winner.
Construction establishes no proof, induction, empirical regularity, universality,
satisfiability, verification, conformance, violation, confidence, review,
applicability, transfer, causation or repair correctness. A missing counterexample
is not proof; a counterexample mentioned in prose is not a checked refutation.

Identity names only the caller's subject. Nil and Max UUIDs are ordinary values;
no generation version, allocation, derivation, namespace registry, canonical
key or collision resolution is introduced. Equal canonical base values compare
equal. Identity and content remain separate: different identities may carry one
text, and one identity may carry separate texts without reconciliation. Unequal
nominal identities may have equal hashes; Python hash is no durable identifier.

Python requires a typed identity child and revalidates it; JSON reconstructs
that child normally. Ordinary subclasses normalize under the owning schemas.
Values are promised, not object identity or guarantees under policy/schema
overrides. Supplied text is strict, unpadded and 1–4096 characters, preserving
admitted Unicode and interior whitespace without normalization. The locked
string validator rejects lone surrogates during validation.

No relationships or composition are added. Applicability/transfer remains P08,
generic support/confidence/review P09, durable interchange/persistence P10,
and discovery/extraction later runtime work. This module has no I/O, clock or
environment access, identifier generation, subprocess or model calls, supplied
code execution, embeddings, caches, or execution of analyzed repositories.
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

__all__ = ["FaultInvariantIdentity", "SuppliedFaultInvariant"]


class FaultInvariantIdentity(RootModel[uuid.UUID]):
    """Caller-assigned name for a proposed reusable-property subject."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    root: uuid.UUID


class SuppliedFaultInvariant(BaseModel):
    """Caller-supplied reusable property, without a truth or scope verdict."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    invariant: FaultInvariantIdentity
    invariant_statement: Annotated[
        str,
        StringConstraints(min_length=1, max_length=4096),
    ]

    @field_validator("invariant", mode="before")
    @classmethod
    def _require_typed_python_invariant(
        cls, value: object, info: ValidationInfo
    ) -> object:
        if info.mode == "python" and not isinstance(value, FaultInvariantIdentity):
            raise ValueError(
                "invariant must be a FaultInvariantIdentity in Python input"
            )
        return value

    @field_validator("invariant_statement", mode="after")
    @classmethod
    def _require_unpadded_text(cls, value: str, info: ValidationInfo) -> str:
        if value != value.strip():
            raise ValueError(
                f"{info.field_name} must not have leading or trailing whitespace"
            )
        return value
