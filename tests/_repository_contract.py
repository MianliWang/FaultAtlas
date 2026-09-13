"""Manually authored current test expectations; historical contracts stay local."""

PRODUCTION_FILES = frozenset(
    {
        "src/faultatlas/__init__.py",
        "src/faultatlas/__main__.py",
        "src/faultatlas/cli.py",
        "src/faultatlas/domain/__init__.py",
        "src/faultatlas/domain/compatibility.py",
        "src/faultatlas/domain/evidence.py",
        "src/faultatlas/domain/fault.py",
        "src/faultatlas/domain/fault_evidence_link.py",
        "src/faultatlas/domain/fault_instance.py",
        "src/faultatlas/domain/fault_interpretation.py",
        "src/faultatlas/domain/fault_repair.py",
        "src/faultatlas/domain/fault_source_relationship.py",
        "src/faultatlas/domain/fault_test.py",
        "src/faultatlas/domain/history.py",
        "src/faultatlas/domain/history_evidence_link.py",
        "src/faultatlas/domain/identity.py",
        "src/faultatlas/domain/invariant.py",
        "src/faultatlas/domain/invariant_relationship.py",
        "src/faultatlas/domain/pattern.py",
        "src/faultatlas/domain/pattern_composition.py",
        "src/faultatlas/domain/pattern_exemplar.py",
        "src/faultatlas/domain/revision.py",
        "src/faultatlas/domain/snapshot.py",
        "src/faultatlas/domain/snapshot_evidence_link.py",
        "src/faultatlas/domain/source.py",
    }
)
PRODUCTION_MODULES = tuple(sorted(p.removeprefix("src/") for p in PRODUCTION_FILES))
PRODUCTION_MODULE_COUNT = len(PRODUCTION_FILES)

P07_SURFACE = (
    ("pattern", ("FaultPatternIdentity", "SuppliedFaultPattern")),
    ("pattern_exemplar", ("FaultPatternExemplarAssociation",)),
    ("invariant", ("FaultInvariantIdentity", "SuppliedFaultInvariant")),
    (
        "invariant_relationship",
        (
            "FaultPatternInvariantAssociation",
            "FaultInvariantExpectedPropertyAssociation",
        ),
    ),
    ("pattern_composition", ("FaultPatternComposition",)),
)
P07_PUBLISHED_MODULES = tuple(
    f"src/faultatlas/domain/{name}.py" for name, _ in P07_SURFACE
)
P07_PUBLISHED_SYMBOLS = tuple(
    symbol for _, symbols in P07_SURFACE for symbol in symbols
)
UUID_IDENTITIES = frozenset(
    {
        "FaultInstanceIdentity",
        "FaultReportIdentity",
        "FaultScenarioIdentity",
        "FaultOccurrenceIdentity",
        "FaultRepairCandidateIdentity",
        "FaultTestMaterialIdentity",
        "FaultTestRunIdentity",
        "FaultExplanationIdentity",
        "FaultHypothesisIdentity",
        "FaultExpectedPropertyIdentity",
        "FaultPatternIdentity",
        "FaultInvariantIdentity",
    }
)

ABSENT_P07_MODULES = (
    "src/faultatlas/domain/fault_pattern.py",
    "src/faultatlas/domain/fault_invariant.py",
    "src/faultatlas/domain/pattern_invariant.py",
)
ABSENT_P07_SYMBOLS = (
    "FaultPattern",
    "FaultInvariant",
    "PatternIdentity",
    "InvariantIdentity",
    "ReusableInvariant",
)
