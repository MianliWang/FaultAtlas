"""Association between one repository-snapshot fact and one evidence record.

This module owns the single cross-domain relation between the published
repository-snapshot value layer and the published durable evidence-record
reference. Neither side changes: the snapshot layer stays evidence-neutral and
the evidence layer stays unchanged, so the association lives here rather than
in either domain module.

The claim is exactly one level deep. A link records that its caller associated
one supplied published snapshot fact with one supplied durable evidence-record
reference, and nothing else. It does not claim that the referenced record was
read, parsed, or inspected, that the record contains, corroborates, derives,
verifies, or proves the fact, or that the fact is correct or authoritative. No
support role, strength, status, confidence, review state, or verification
outcome is recorded, and every association carries the same weak, uniform
meaning.

The fact position accepts exactly one supplied root-tree binding or one
supplied path binding, each of which corresponds to a retained normalized
observation. A binding collection, a declared path scope, and a scope-coverage
witness are excluded: their aggregate order, declared paths, and deterministic
relation are supplied by callers rather than declared by any retained record,
so associating a record with them would manufacture provenance.

The referenced record is identified as a whole. There is no JSON pointer,
semantic path, field locator, byte span, request, artifact, or envelope that
would locate a fact inside the record, and byte offsets are not a substitute
for one. Each link carries exactly one record; associating one fact with two
records is two independent link values, and no ordering, duplicate, or bound
semantics over multiple associations exists here.

The target fact is embedded by value, so no durable snapshot bytes, record
digest, registry, identifier, or persistence is required. The module performs
no I/O: it resolves nothing, reads nothing, and never inspects the record it
references. Repository membership, path existence, root-tree reachability,
snapshot completeness, absence, confidence, review, and durable serialization
all remain outside it.
"""

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from faultatlas.domain.evidence import DurableEvidenceRecordReference
from faultatlas.domain.snapshot import (
    RepositorySnapshotPathBinding,
    RepositorySnapshotRootTreeBinding,
)

__all__ = [
    "RepositorySnapshotFactEvidenceLink",
]


class RepositorySnapshotFactEvidenceLink(BaseModel):
    """Supplied association from one snapshot fact to one durable record."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        validate_default=True,
    )

    fact: RepositorySnapshotRootTreeBinding | RepositorySnapshotPathBinding
    evidence_record: DurableEvidenceRecordReference

    @field_validator("fact", mode="before")
    @classmethod
    def _require_typed_python_fact(
        cls,
        value: object,
        info: ValidationInfo,
    ) -> object:
        if info.mode == "python" and not isinstance(
            value,
            (RepositorySnapshotRootTreeBinding, RepositorySnapshotPathBinding),
        ):
            raise ValueError(
                "fact must be a RepositorySnapshotRootTreeBinding or "
                "RepositorySnapshotPathBinding in Python input"
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
