"""Bounded canonical bytes for one supplied review and its attribution records."""

import json
from typing import NoReturn, cast

from faultatlas.assessment_review_attribution import (
    inspect_assessment_review_attributions,
)
from faultatlas.domain.assessment_review import SuppliedAssessmentReview
from faultatlas.domain.assessment_review_attribution import (
    SuppliedAssessmentReviewAttribution,
)

__all__ = [
    "encode_assessment_review_document",
    "decode_assessment_review_document",
    "inspect_assessment_review_document",
]

_FORMAT = "faultatlas-supplied-review"
_MAX_BYTES = 16 * 1024 * 1024
_MAX_NODES = 74036
_MAX_OBJECTS = 4651
_MAX_CHARACTERS = 1331268
_MAX_DEPTH = 36


def _fail(code: str) -> NoReturn:
    raise ValueError("P09 review document: " + code)


def _depth(text: str) -> None:
    depth = 0
    quoted = escaped = False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            if depth > _MAX_DEPTH:
                _fail("RESOURCE_LIMIT")
        elif character in "]}":
            depth -= 1
            if depth < 0:
                _fail("INVALID_JSON")


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("INVALID_JSON")
        result[key] = value
    return result


def _integer(token: str) -> int:
    if len(token) > 20:
        _fail("INVALID_JSON")
    value = int(token)
    if not -(2**63) <= value < 2**63:
        _fail("INVALID_JSON")
    return value


def _forbidden_number(token: str) -> NoReturn:
    _fail("INVALID_JSON")


def _tree(value: object) -> None:
    nodes = objects = characters = 0

    def visit(item: object, parent_depth: int) -> None:
        nonlocal nodes, objects, characters
        nodes += 1
        if nodes > _MAX_NODES:
            _fail("RESOURCE_LIMIT")
        if isinstance(item, str):
            try:
                item.encode("utf-8")
            except UnicodeEncodeError:
                _fail("INVALID_ENCODING")
            characters += len(item)
            if characters > _MAX_CHARACTERS:
                _fail("RESOURCE_LIMIT")
        elif isinstance(item, (dict, list)):
            depth = parent_depth + 1
            if depth > _MAX_DEPTH:
                _fail("RESOURCE_LIMIT")
            if isinstance(item, dict):
                objects += 1
                if objects > _MAX_OBJECTS:
                    _fail("RESOURCE_LIMIT")
                for key, child in cast(dict[str, object], item).items():
                    visit(key, depth)
                    visit(child, depth)
            else:
                for child in cast(list[object], item):
                    visit(child, depth)
        elif item is None or type(item) is bool:
            pass
        elif type(item) is int:
            if not -(2**63) <= item < 2**63:
                _fail("INVALID_JSON")
        else:
            _fail("INVALID_JSON")

    visit(value, 0)


def _canonical(
    review: SuppliedAssessmentReview,
    attributions: tuple[SuppliedAssessmentReviewAttribution, ...],
) -> bytes:
    value = {
        "format": _FORMAT,
        "version": 1,
        "review": review.model_dump(mode="json"),
        "attributions": [item.model_dump(mode="json") for item in attributions],
    }
    _tree(value)
    encoded = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    if len(encoded) > _MAX_BYTES:
        _fail("RESOURCE_LIMIT")
    return encoded


def _read(
    data: bytes,
) -> tuple[
    SuppliedAssessmentReview, tuple[SuppliedAssessmentReviewAttribution, ...], str
]:
    if type(cast(object, data)) is not bytes:
        _fail("BYTES_REQUIRED")
    if len(data) > _MAX_BYTES:
        _fail("RESOURCE_LIMIT")
    if data.startswith(b"\xef\xbb\xbf"):
        _fail("INVALID_ENCODING")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        _fail("INVALID_ENCODING")
    _depth(text)
    try:
        value: object = json.loads(
            text,
            object_pairs_hook=_object,
            parse_int=_integer,
            parse_float=_forbidden_number,
            parse_constant=_forbidden_number,
        )
    except json.JSONDecodeError:
        _fail("INVALID_JSON")
    _tree(value)
    if not isinstance(value, dict):
        _fail("INVALID_SHAPE")
    document = cast(dict[str, object], value)
    if set(document) != {
        "format",
        "version",
        "review",
        "attributions",
    }:
        _fail("INVALID_SHAPE")
    if document["format"] != _FORMAT:
        _fail("UNSUPPORTED_FORMAT")
    if type(document["version"]) is not int or document["version"] != 1:
        _fail("UNSUPPORTED_VERSION")
    if not isinstance(document["review"], dict) or not isinstance(
        document["attributions"], list
    ):
        _fail("INVALID_SHAPE")
    supplied = cast(list[object], document["attributions"])
    if len(supplied) > 8:
        raise ValueError(
            "attributions must contain at most 8 supplied attribution declarations"
        )
    review = SuppliedAssessmentReview.model_validate_json(
        json.dumps(document["review"], allow_nan=False)
    )
    assertions: list[SuppliedAssessmentReviewAttribution] = []
    for index, item in enumerate(supplied):
        assertion = SuppliedAssessmentReviewAttribution.model_validate_json(
            json.dumps(item, allow_nan=False)
        )
        if assertion.review != review:
            raise ValueError(
                f"attribution at index {index} target does not match requested review"
            )
        assertions.append(assertion)
    attributions = tuple(assertions)
    view = inspect_assessment_review_attributions(review, attributions)
    _canonical(review, attributions)
    return review, attributions, view


def encode_assessment_review_document(
    review: SuppliedAssessmentReview,
    attributions: tuple[SuppliedAssessmentReviewAttribution, ...],
) -> bytes:
    """Return canonical bytes after the public supplied-value checks."""
    inspect_assessment_review_attributions(review, attributions)
    requested = SuppliedAssessmentReview.model_validate(review)
    validated = tuple(
        SuppliedAssessmentReviewAttribution.model_validate(item)
        for item in attributions
    )
    return _canonical(requested, validated)


def decode_assessment_review_document(
    data: bytes,
) -> tuple[SuppliedAssessmentReview, tuple[SuppliedAssessmentReviewAttribution, ...]]:
    """Reconstruct a complete typed pair with canonical representability."""
    review, attributions, _ = _read(data)
    return review, attributions


def inspect_assessment_review_document(data: bytes) -> str:
    """Return the unchanged complete S02 view of one admitted document."""
    return _read(data)[2]
