"""Pure, complete inspection of supplied assessments at an exact selected basis."""

import json
from typing import cast

from faultatlas.domain.assessment import AssessmentBasis, SuppliedAssessment

__all__ = ["inspect_assessment"]

_MAX_VIEW_BYTES = 8 * 1024 * 1024


def _quoted(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).replace(
        "\x7f", "\\u007f"
    )


def inspect_assessment(basis: AssessmentBasis, assessment: SuppliedAssessment) -> str:
    """Return the complete safe view, or reject wrong inputs/full-basis mismatch.

    No file, execution or empirical status is represented here. Root attribution
    describes supplied assembly, not source authorship or authentication.
    """
    if not isinstance(cast(object, basis), AssessmentBasis):
        raise ValueError("basis must be an AssessmentBasis")
    if not isinstance(cast(object, assessment), SuppliedAssessment):
        raise ValueError("assessment must be a SuppliedAssessment")
    requested = AssessmentBasis.model_validate(basis)
    value = SuppliedAssessment.model_validate(assessment)
    if value.basis != requested:
        raise ValueError("assessment basis does not match requested basis")

    source = value.basis.source.model_dump(mode="json")
    kind = "pattern" if "pattern" in source else "invariant"
    target = value.basis.target
    lines = [
        "Supplied assessment - structural inspection only",
        f"Source {kind}: {_quoted(source[kind])}",
        f"Source statement: {_quoted(source[kind + '_statement'])}",
        f"Target snapshot: {_quoted(target.snapshot.model_dump(mode='json'))}",
        "Host/visibility: caller-declared "
        f"{_quoted(target.declared_host)} / {_quoted(target.declared_visibility)}; "
        "not externally verified",
        "Path scope: "
        + (
            "not supplied; no whole-repository coverage inferred"
            if target.scope is None
            else _quoted(target.scope.model_dump(mode="json"))
            + "; exact declared paths only; no coverage inferred"
        ),
        "Context: "
        + (
            "not supplied"
            if value.basis.context_statement is None
            else _quoted(value.basis.context_statement)
        ),
        f"Assessment supplier: {_quoted(value.attribution.supplier)}",
        f"Rationale: {_quoted(value.attribution.rationale)}",
        "Root attribution covers assembly, context and condition inventory; "
        "source authorship and authentication are not established.",
    ]
    referred_conditions = {item.condition.key for item in value.opinions}
    if not value.basis.conditions:
        lines.append("Conditions: none supplied; no requirement success inferred")
    for condition in value.basis.conditions:
        lines.append(
            f"Condition {_quoted(condition.key)}: {_quoted(condition.statement)}"
        )
        if condition.key not in referred_conditions:
            lines.append("No opinion supplied")

    if value.basis.materials is None:
        if value.basis.material_omission is None:
            lines.append("Materials: not supplied")
        else:
            lines.extend(
                [
                    "Materials: explicitly omitted by the assessment assembler",
                    f"Omission reason: {_quoted(value.basis.material_omission)}",
                ]
            )
    elif not value.basis.materials:
        lines.append(
            "Materials: caller-declared empty inventory; no world-level absence inferred"
        )
    else:
        for material in value.basis.materials:
            lines.extend(
                [
                    f"Material {_quoted(material.key)}: {_quoted(material.description)}",
                    f"Supplier: {_quoted(material.attribution.supplier)}",
                    f"Rationale: {_quoted(material.attribution.rationale)}",
                    "Record reference: "
                    + (
                        "not supplied"
                        if material.record is None
                        else _quoted(material.record.model_dump(mode="json"))
                    ),
                    "Locator: "
                    + (
                        "not supplied"
                        if material.locator is None
                        else _quoted(material.locator)
                    ),
                    "References are supplied, not loaded or verified as support.",
                ]
            )
    if not value.opinions:
        lines.append("Opinions: none supplied")
    for opinion in value.opinions:
        lines.extend(
            [
                f"Opinion {_quoted(opinion.key)}: caller position={_quoted(opinion.position)}, "
                f"supplier={_quoted(opinion.attribution.supplier)}",
                f"Statement: {_quoted(opinion.statement)}",
                f"Rationale: {_quoted(opinion.attribution.rationale)}",
                f"Condition reference: {_quoted(opinion.condition.model_dump(mode='json'))}",
                f"Material keys: {_quoted(opinion.material_keys)}",
            ]
        )
    if not value.conflicts:
        lines.append("Conflicts: none supplied; no absence-of-conflict claim")
    for index, conflict in enumerate(value.conflicts, 1):
        lines.extend(
            [
                f"Conflict {index}: left={_quoted(conflict.left_opinion_key)}, "
                f"right={_quoted(conflict.right_opinion_key)}; caller declaration",
                f"Supplier: {_quoted(conflict.attribution.supplier)}",
                f"Rationale: {_quoted(conflict.attribution.rationale)}",
            ]
        )
    if value.overall_opinion is None:
        lines.append("Overall opinion: not supplied; none inferred")
    else:
        lines.extend(
            [
                f"Overall caller opinion: {_quoted(value.overall_opinion.statement)}",
                f"Supplier: {_quoted(value.overall_opinion.attribution.supplier)}",
                f"Rationale: {_quoted(value.overall_opinion.attribution.rationale)}",
            ]
        )
    lines.extend(
        [
            "Structural checks: passed; no applicability or repair certification",
            "End of complete view",
        ]
    )
    view = "\n".join(lines) + "\n"
    if len(view.encode("utf-8")) > _MAX_VIEW_BYTES:
        raise ValueError("P08 inspection output budget exceeded (8 MiB)")
    return view
