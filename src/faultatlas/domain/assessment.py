"""Complete caller-supplied assessments with local full-value reference checks.

The basis fixes the supplied proposition, target declarations, context,
conditions and materials. Attribution names the supplier of a declaration,
not an authenticated reviewer or the author of a referenced proposition.
Opinions and explicit conflicts remain claims; no predicate, support or
applicability is evaluated. Missing material and missing opinions are allowed.

Keys are local labels, not identities or capabilities. Ordered tuples retain
repetition where permitted; repetition establishes no independent evidence.
Owning schemas validate typed Python children and reconstruct native JSON.
Resource limits apply to normalized values, not raw file bytes or peak memory.
There is no file protocol, I/O, discovery, allocation or history registry here.
"""

import json
import re
from functools import partial
from typing import Annotated, Self, cast

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    model_validator,
)

from faultatlas.domain.evidence import DurableEvidenceRecordReference
from faultatlas.domain.invariant import SuppliedFaultInvariant
from faultatlas.domain.pattern import SuppliedFaultPattern
from faultatlas.domain.snapshot import (
    RepositorySnapshotDeclaredPathScope,
    RepositorySnapshotIdentity,
)

__all__ = [
    "AssessmentAttribution",
    "AssessmentTarget",
    "AssessmentCondition",
    "AssessmentMaterial",
    "AssessmentBasis",
    "SuppliedConditionOpinion",
    "SuppliedAssessmentConflict",
    "SuppliedOverallOpinion",
    "SuppliedAssessment",
]

from typing import Literal


def _text(value: str) -> str:
    if not value.strip():
        raise ValueError("text must not be whitespace-only")
    value.encode("utf-8")
    return value


def _key(value: str) -> str:
    if re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", value) is None:
        raise ValueError("key must fully match [a-z][a-z0-9_-]{0,31}")
    return value


_Text = Annotated[
    str, StringConstraints(min_length=1, max_length=4096), AfterValidator(_text)
]
_Supplier = Annotated[
    str, StringConstraints(min_length=1, max_length=128), AfterValidator(_text)
]
_Key = Annotated[
    str, StringConstraints(min_length=1, max_length=32), AfterValidator(_key)
]


def _typed(
    value: object,
    info: ValidationInfo,
    *,
    expected: type[BaseModel] | tuple[type[BaseModel], ...],
) -> object:
    if info.mode == "python" and not isinstance(value, expected):
        raise ValueError(f"{info.field_name} requires its declared typed Python child")
    return value


def _check_domain_budget(value: object) -> None:
    """Count one normalized JSON-shaped value, including every occurrence."""
    nodes = records = characters = 0

    def visit(item: object, parent_depth: int) -> None:
        nonlocal nodes, records, characters
        nodes += 1
        if nodes > 8192:
            raise ValueError("P08 normalized node budget exceeded (8192)")
        if isinstance(item, str):
            characters += len(item)
            if characters > 131072:
                raise ValueError("P08 normalized string budget exceeded (131072)")
        elif isinstance(item, (dict, list)):
            depth = parent_depth + 1
            if depth > 32:
                raise ValueError("P08 normalized container depth exceeded (32)")
            if isinstance(item, dict):
                records += 1
                if records > 512:
                    raise ValueError("P08 normalized object budget exceeded (512)")
                for key, child in cast(dict[str, object], item).items():
                    visit(key, depth)
                    visit(child, depth)
            else:
                for child in cast(list[object], item):
                    visit(child, depth)

    visit(value, 0)


class _AssessmentRecord(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        revalidate_instances="always",
        validate_default=True,
    )


class AssessmentAttribution(_AssessmentRecord):
    """Supplied label and rationale for one declaration, without authentication."""

    supplier: _Supplier
    rationale: _Text


class AssessmentTarget(_AssessmentRecord):
    """Fixed supplied Git target with unverified host/public declarations."""

    snapshot: Annotated[
        RepositorySnapshotIdentity,
        BeforeValidator(partial(_typed, expected=RepositorySnapshotIdentity)),
    ]
    declared_host: Literal["github.com"]
    declared_visibility: Literal["public"]
    scope: (
        Annotated[
            RepositorySnapshotDeclaredPathScope,
            BeforeValidator(
                partial(_typed, expected=RepositorySnapshotDeclaredPathScope)
            ),
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def _target_binding(self) -> Self:
        if self.snapshot.repository.provider.root != "github":
            raise ValueError("assessment target provider must be github")
        if self.scope is not None and self.scope.snapshot != self.snapshot:
            raise ValueError("assessment scope snapshot must match target snapshot")
        return self


class AssessmentCondition(_AssessmentRecord):
    """One locally named opaque condition supplied by the assembler."""

    key: _Key
    statement: _Text


class AssessmentMaterial(_AssessmentRecord):
    """An attributed inline description with optional, never-resolved references."""

    key: _Key
    description: _Text
    attribution: Annotated[
        AssessmentAttribution,
        BeforeValidator(partial(_typed, expected=AssessmentAttribution)),
    ]
    record: (
        Annotated[
            DurableEvidenceRecordReference,
            BeforeValidator(partial(_typed, expected=DurableEvidenceRecordReference)),
        ]
        | None
    ) = None
    locator: _Text | None = None


class AssessmentBasis(_AssessmentRecord):
    """The complete input scope of an assessment, without a truth judgment."""

    source: Annotated[
        SuppliedFaultPattern | SuppliedFaultInvariant,
        BeforeValidator(
            partial(_typed, expected=(SuppliedFaultPattern, SuppliedFaultInvariant))
        ),
    ]
    target: Annotated[
        AssessmentTarget, BeforeValidator(partial(_typed, expected=AssessmentTarget))
    ]
    context_statement: _Text | None = None
    conditions: Annotated[
        tuple[
            Annotated[
                AssessmentCondition,
                BeforeValidator(partial(_typed, expected=AssessmentCondition)),
            ],
            ...,
        ],
        Field(max_length=64),
    ] = ()
    materials: (
        Annotated[
            tuple[
                Annotated[
                    AssessmentMaterial,
                    BeforeValidator(partial(_typed, expected=AssessmentMaterial)),
                ],
                ...,
            ],
            Field(max_length=128),
        ]
        | None
    ) = None
    material_omission: _Text | None = None

    @model_validator(mode="after")
    def _basis_integrity(self) -> Self:
        if len({item.key for item in self.conditions}) != len(self.conditions):
            raise ValueError("basis condition keys must be unique")
        if self.materials is not None:
            if self.material_omission is not None:
                raise ValueError("material inventory cannot coexist with omission")
            if len({item.key for item in self.materials}) != len(self.materials):
                raise ValueError("basis material keys must be unique")
        _check_domain_budget(self.model_dump(mode="json"))
        return self


class SuppliedConditionOpinion(_AssessmentRecord):
    """One supplier's opinion about an exact condition, not an evaluated result."""

    key: _Key
    condition: Annotated[
        AssessmentCondition,
        BeforeValidator(partial(_typed, expected=AssessmentCondition)),
    ]
    position: Literal["stated", "unknown", "unsupported", "not_applicable"]
    statement: _Text
    attribution: Annotated[
        AssessmentAttribution,
        BeforeValidator(partial(_typed, expected=AssessmentAttribution)),
    ]
    material_keys: Annotated[tuple[_Key, ...], Field(max_length=128)] = ()

    @model_validator(mode="after")
    def _unique_material_keys(self) -> Self:
        if len(set(self.material_keys)) != len(self.material_keys):
            raise ValueError("opinion material keys must be unique")
        return self


class SuppliedAssessmentConflict(_AssessmentRecord):
    """An attributed declaration of conflict between two local opinions."""

    left_opinion_key: _Key
    right_opinion_key: _Key
    attribution: Annotated[
        AssessmentAttribution,
        BeforeValidator(partial(_typed, expected=AssessmentAttribution)),
    ]

    @model_validator(mode="after")
    def _distinct_opinions(self) -> Self:
        if self.left_opinion_key == self.right_opinion_key:
            raise ValueError("conflict must reference two distinct opinion keys")
        return self


class SuppliedOverallOpinion(_AssessmentRecord):
    """An explicit overall caller opinion; no aggregate inference is performed."""

    statement: _Text
    attribution: Annotated[
        AssessmentAttribution,
        BeforeValidator(partial(_typed, expected=AssessmentAttribution)),
    ]


def _basis_child(value: object, info: ValidationInfo) -> object:
    # A before-guard materializes JSON arrays. Let their owner reconstruct them.
    if info.mode == "json" and isinstance(value, dict):
        return AssessmentBasis.model_validate_json(json.dumps(value, allow_nan=False))
    return _typed(value, info, expected=AssessmentBasis)


def _opinion_child(value: object, info: ValidationInfo) -> object:
    if info.mode == "json" and isinstance(value, dict):
        return SuppliedConditionOpinion.model_validate_json(
            json.dumps(value, allow_nan=False)
        )
    return _typed(value, info, expected=SuppliedConditionOpinion)


class SuppliedAssessment(_AssessmentRecord):
    """A complete supplied assessment bound to one complete basis."""

    attribution: Annotated[
        AssessmentAttribution,
        BeforeValidator(partial(_typed, expected=AssessmentAttribution)),
    ]
    basis: Annotated[AssessmentBasis, BeforeValidator(_basis_child)]
    opinions: Annotated[
        tuple[
            Annotated[
                SuppliedConditionOpinion,
                BeforeValidator(_opinion_child),
            ],
            ...,
        ],
        Field(max_length=128),
    ] = ()
    conflicts: Annotated[
        tuple[
            Annotated[
                SuppliedAssessmentConflict,
                BeforeValidator(partial(_typed, expected=SuppliedAssessmentConflict)),
            ],
            ...,
        ],
        Field(max_length=64),
    ] = ()
    overall_opinion: (
        Annotated[
            SuppliedOverallOpinion,
            BeforeValidator(partial(_typed, expected=SuppliedOverallOpinion)),
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def _assessment_integrity(self) -> Self:
        conditions = {item.key: item for item in self.basis.conditions}
        material_keys = {item.key for item in self.basis.materials or ()}
        opinion_keys: set[str] = set()
        for opinion in self.opinions:
            if opinion.key in opinion_keys:
                raise ValueError("assessment opinion keys must be unique")
            opinion_keys.add(opinion.key)
            if conditions.get(opinion.condition.key) != opinion.condition:
                raise ValueError("opinion condition is not a full-value basis member")
            if any(key not in material_keys for key in opinion.material_keys):
                raise ValueError("opinion references an absent material key")
        for conflict in self.conflicts:
            if (
                conflict.left_opinion_key not in opinion_keys
                or conflict.right_opinion_key not in opinion_keys
            ):
                raise ValueError("conflict references an absent opinion key")
        _check_domain_budget(self.model_dump(mode="json"))
        return self
