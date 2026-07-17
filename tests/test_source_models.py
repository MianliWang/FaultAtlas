from datetime import UTC, datetime, timedelta, timezone
from hashlib import sha256

import pytest
from pydantic import ValidationError

from faultatlas.domain.source import ArtifactSnapshot, SourceLocator

SYNTHETIC_PAYLOAD = '{"title":"Synthetic issue"}'
SYNTHETIC_DIGEST = sha256(SYNTHETIC_PAYLOAD.encode("utf-8")).hexdigest()
RETRIEVED_AT = datetime(2026, 7, 17, 12, 34, 56, tzinfo=UTC)


def _locator_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "provider": "github",
        "repository": "owner/repository",
        "object_kind": "issue",
        "object_id": "17",
    }
    data.update(overrides)
    return data


def _snapshot_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "source": SourceLocator.model_validate(_locator_data()),
        "retrieved_at": RETRIEVED_AT,
        "payload_text": SYNTHETIC_PAYLOAD,
        "digest": SYNTHETIC_DIGEST,
        "truncated": False,
        "redacted": False,
        "missing_context": (),
    }
    data.update(overrides)
    return data


def _snapshot(**overrides: object) -> ArtifactSnapshot:
    return ArtifactSnapshot.model_validate(_snapshot_data(**overrides))


def test_valid_locator_normalizes_repository_identity() -> None:
    mixed_case = SourceLocator.model_validate(
        _locator_data(repository="Owner/Repository")
    )
    lowercase = SourceLocator.model_validate(_locator_data())

    assert mixed_case.repository == "owner/repository"
    assert mixed_case == lowercase


@pytest.mark.parametrize(
    "repository",
    [" owner/repository", "owner/repository ", "\towner/repository"],
)
def test_locator_rejects_repository_padding(repository: str) -> None:
    with pytest.raises(ValidationError) as error:
        SourceLocator.model_validate(_locator_data(repository=repository))

    assert error.value.errors()[0]["loc"] == ("repository",)


def test_locator_rejects_non_ascii_repository() -> None:
    with pytest.raises(ValidationError) as error:
        SourceLocator.model_validate(_locator_data(repository="ownér/repository"))

    assert error.value.errors()[0]["loc"] == ("repository",)


@pytest.mark.parametrize(
    "repository",
    ["owner", "owner/repository/extra", "/repository", "owner/"],
)
def test_locator_rejects_malformed_repository_structure(repository: str) -> None:
    with pytest.raises(ValidationError) as error:
        SourceLocator.model_validate(_locator_data(repository=repository))

    assert error.value.errors()[0]["type"] in {
        "string_pattern_mismatch",
        "string_too_short",
    }


@pytest.mark.parametrize(
    "repository",
    [
        "-owner/repository",
        "owner-/repository",
        "owner/repo sitory",
        f"{'o' * 40}/repository",
        f"owner/{'r' * 101}",
    ],
)
def test_locator_rejects_repository_grammar_and_bounds(repository: str) -> None:
    with pytest.raises(ValidationError):
        SourceLocator.model_validate(_locator_data(repository=repository))


@pytest.mark.parametrize(
    ("field", "value"),
    [("provider", "gitlab"), ("object_kind", "pull_request")],
)
def test_locator_rejects_unsupported_identity_vocabulary(
    field: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError) as error:
        SourceLocator.model_validate(_locator_data(**{field: value}))

    assert error.value.errors()[0]["type"] == "literal_error"
    assert error.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize(
    "object_id",
    ["0", "01", "-1", "+1", " 1", "1 ", "1.0", "issue-1", "1" * 21, 1],
)
def test_locator_rejects_invalid_or_coerced_object_id(object_id: object) -> None:
    with pytest.raises(ValidationError) as error:
        SourceLocator.model_validate(_locator_data(object_id=object_id))

    assert error.value.errors()[0]["loc"] == ("object_id",)


def test_locator_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError) as error:
        SourceLocator.model_validate(
            _locator_data(canonical_url="https://example.test")
        )

    assert error.value.errors()[0]["type"] == "extra_forbidden"
    assert error.value.errors()[0]["loc"] == ("canonical_url",)


def test_valid_snapshot_preserves_explicit_complete_state() -> None:
    snapshot = _snapshot()

    assert snapshot.source == SourceLocator.model_validate(_locator_data())
    assert snapshot.retrieved_at == RETRIEVED_AT
    assert snapshot.payload_text == SYNTHETIC_PAYLOAD
    assert snapshot.digest == SYNTHETIC_DIGEST
    assert snapshot.truncated is False
    assert snapshot.redacted is False
    assert snapshot.missing_context == ()


@pytest.mark.parametrize("field", ["truncated", "redacted", "missing_context"])
def test_snapshot_requires_explicit_limitation_facts(field: str) -> None:
    data = _snapshot_data()
    del data[field]

    with pytest.raises(ValidationError) as error:
        ArtifactSnapshot.model_validate(data)

    assert error.value.errors()[0]["type"] == "missing"
    assert error.value.errors()[0]["loc"] == (field,)


def test_snapshot_rejects_naive_datetime() -> None:
    naive = RETRIEVED_AT.replace(tzinfo=None)

    with pytest.raises(ValidationError) as error:
        _snapshot(retrieved_at=naive)

    assert error.value.errors()[0]["type"] == "timezone_aware"
    assert error.value.errors()[0]["loc"] == ("retrieved_at",)


def test_snapshot_rejects_nonzero_utc_offset() -> None:
    non_utc = RETRIEVED_AT.astimezone(timezone(timedelta(hours=1)))

    with pytest.raises(ValidationError) as error:
        _snapshot(retrieved_at=non_utc)

    assert error.value.errors()[0]["type"] == "value_error"
    assert error.value.errors()[0]["loc"] == ("retrieved_at",)


def test_snapshot_normalizes_zero_offset_and_serializes_rfc3339() -> None:
    zero_offset = timezone(timedelta(0), name="zero-offset")
    retrieved_at = datetime(2026, 7, 17, 12, 34, 56, 123456, tzinfo=zero_offset)
    snapshot = _snapshot(retrieved_at=retrieved_at)

    assert snapshot.retrieved_at.tzinfo is UTC
    assert snapshot.retrieved_at.microsecond == 123456
    assert snapshot.model_dump(mode="json")["retrieved_at"] == (
        "2026-07-17T12:34:56.123456Z"
    )


@pytest.mark.parametrize(
    "digest",
    ["0" * 63, "0" * 65, "A" * 64, "g" * 64],
)
def test_snapshot_rejects_malformed_digest(digest: str) -> None:
    with pytest.raises(ValidationError) as error:
        _snapshot(digest=digest)

    assert error.value.errors()[0]["loc"] == ("digest",)


def test_snapshot_rejects_digest_mismatch() -> None:
    with pytest.raises(ValidationError) as error:
        _snapshot(digest="0" * 64)

    assert error.value.errors()[0]["type"] == "value_error"
    assert error.value.errors()[0]["loc"] == ()


def test_snapshot_rejects_payload_that_cannot_encode_as_utf8() -> None:
    with pytest.raises(ValidationError) as error:
        _snapshot(payload_text="\ud800", digest="0" * 64)

    assert error.value.errors()[0]["type"] == "value_error"
    assert error.value.errors()[0]["loc"] == ("payload_text",)


def test_snapshot_accepts_payload_at_encoded_byte_limit() -> None:
    payload = "é" * 524_288

    snapshot = _snapshot(
        payload_text=payload,
        digest=sha256(payload.encode("utf-8")).hexdigest(),
    )

    assert len(snapshot.payload_text.encode("utf-8")) == 1_048_576


def test_snapshot_rejects_payload_above_encoded_byte_limit() -> None:
    payload = ("é" * 524_288) + "a"

    with pytest.raises(ValidationError) as error:
        _snapshot(
            payload_text=payload,
            digest=sha256(payload.encode("utf-8")).hexdigest(),
        )

    assert error.value.errors()[0]["type"] == "value_error"
    assert error.value.errors()[0]["loc"] == ("payload_text",)


def test_models_reject_assignment_mutation() -> None:
    locator = SourceLocator.model_validate(_locator_data())
    snapshot = _snapshot()

    with pytest.raises(ValidationError) as locator_error:
        setattr(locator, "repository", "other/repository")
    with pytest.raises(ValidationError) as snapshot_error:
        setattr(snapshot, "redacted", True)

    assert locator_error.value.errors()[0]["type"] == "frozen_instance"
    assert snapshot_error.value.errors()[0]["type"] == "frozen_instance"


def test_snapshot_semantically_revalidates_constructed_locator() -> None:
    invalid_locator = SourceLocator.model_construct(
        provider="github",
        repository="owner/repository",
        object_kind="issue",
        object_id="0",
    )

    with pytest.raises(ValidationError) as error:
        _snapshot(source=invalid_locator)

    assert error.value.errors()[0]["type"] == "string_pattern_mismatch"
    assert error.value.errors()[0]["loc"] == ("source", "object_id")


def test_snapshot_rejects_python_list_for_missing_context() -> None:
    with pytest.raises(ValidationError) as error:
        _snapshot(missing_context=["comments unavailable"])

    assert error.value.errors()[0]["type"] == "tuple_type"
    assert error.value.errors()[0]["loc"] == ("missing_context",)


def test_retrieval_metadata_is_independent_from_source_identity() -> None:
    first = _snapshot()
    later_payload = '{"title":"Updated synthetic issue"}'
    second = _snapshot(
        source=first.source,
        retrieved_at=RETRIEVED_AT + timedelta(minutes=5),
        payload_text=later_payload,
        digest=sha256(later_payload.encode("utf-8")).hexdigest(),
    )

    assert first.source == second.source
    assert first != second


@pytest.mark.parametrize(
    ("truncated", "redacted", "missing_context"),
    [
        (True, False, ()),
        (False, True, ()),
        (False, False, ("comments unavailable",)),
    ],
)
def test_snapshot_preserves_known_limitations(
    truncated: bool,
    redacted: bool,
    missing_context: tuple[str, ...],
) -> None:
    snapshot = _snapshot(
        truncated=truncated,
        redacted=redacted,
        missing_context=missing_context,
    )

    assert snapshot.truncated is truncated
    assert snapshot.redacted is redacted
    assert snapshot.missing_context == missing_context


def test_snapshot_preserves_unknown_limitation_state() -> None:
    snapshot = _snapshot(truncated=None, redacted=None, missing_context=None)

    assert snapshot.truncated is None
    assert snapshot.redacted is None
    assert snapshot.missing_context is None


@pytest.mark.parametrize(
    "missing_context",
    [
        ("duplicate", "duplicate"),
        (" padded",),
        ("padded ",),
        ("line\nbreak",),
        ("x" * 201,),
        tuple(str(index) for index in range(17)),
        (1,),
    ],
)
def test_snapshot_rejects_invalid_missing_context(
    missing_context: object,
) -> None:
    with pytest.raises(ValidationError) as error:
        _snapshot(missing_context=missing_context)

    assert error.value.errors()[0]["loc"][:1] == ("missing_context",)


def test_snapshot_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError) as error:
        ArtifactSnapshot.model_validate(_snapshot_data(snapshot_id="generated"))

    assert error.value.errors()[0]["type"] == "extra_forbidden"
    assert error.value.errors()[0]["loc"] == ("snapshot_id",)


def test_equal_models_have_equal_semantic_json_dumps() -> None:
    first = _snapshot()
    second = ArtifactSnapshot.model_validate(_snapshot_data())

    assert first == second
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_repeated_serialization_is_deterministic() -> None:
    snapshot = _snapshot()

    assert snapshot.model_dump_json() == snapshot.model_dump_json()


def test_json_round_trip_reconstructs_equal_model() -> None:
    snapshot = _snapshot(missing_context=("comments unavailable",))

    reconstructed = ArtifactSnapshot.model_validate_json(snapshot.model_dump_json())

    assert reconstructed == snapshot


def test_semantic_dump_includes_schema_defaults() -> None:
    semantic_dump = _snapshot().model_dump(mode="json")

    assert semantic_dump["schema_version"] == 1
    assert semantic_dump["media_type"] == "application/json"
    assert semantic_dump["digest_algorithm"] == "sha256"
    assert semantic_dump["truncated"] is False
    assert semantic_dump["redacted"] is False
    assert semantic_dump["missing_context"] == []
