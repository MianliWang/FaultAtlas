"""Frozen independent document oracles and bounded public consumer checks."""

import ast
import builtins
import copy
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError
from test_supplied_assessment_review import review_wire as rich_review_wire

import faultatlas
import faultatlas.assessment_review_attribution as attribution_inspection
import faultatlas.assessment_review_document as document
import faultatlas.domain as domain_package
from faultatlas.domain.assessment_review import SuppliedAssessmentReview
from faultatlas.domain.assessment_review_attribution import (
    SuppliedAssessmentReviewAttribution,
)

# Exact pre-implementation companion bytes, bound to ACTIVATION-01. All identities
# and review statements in these fixtures are synthetic supplied declarations.
# No product encoder/renderer generated these expected bytes or views.
ORACLES: dict[str, bytes] = {
    "parallel.input.json": b'{\n  "format": "faultatlas-supplied-review",\n  "version": 1,\n  "review": {\n    "assessment": {\n      "attribution": {\n        "supplier": "Assessment assembler",\n        "rationale": "Synthetic assessment."\n      },\n      "basis": {\n        "source": {\n          "invariant": "00000000-0000-4000-8000-000000000002",\n          "invariant_statement": "An expression is evaluated once."\n        },\n        "target": {\n          "snapshot": {\n            "repository": {\n              "schema_version": 1,\n              "provider": "github",\n              "provider_repository_id": "1001"\n            },\n            "revision": {\n              "schema_version": 1,\n              "kind": "commit",\n              "algorithm": "sha1",\n              "full_digest": "1111111111111111111111111111111111111111"\n            }\n          },\n          "declared_host": "github.com",\n          "declared_visibility": "public",\n          "scope": null\n        },\n        "context_statement": null,\n        "conditions": [],\n        "materials": null,\n        "material_omission": null\n      },\n      "opinions": [],\n      "conflicts": [],\n      "overall_opinion": null\n    },\n    "scope": "Only the supplied statement was considered.",\n    "judgment": "No execution evidence was assessed.",\n    "attribution": {\n      "supplier": "Review relay",\n      "rationale": "Newly authored example judgment; no historical authorship is claimed."\n    }\n  },\n  "attributions": [\n    {\n      "review": {\n        "assessment": {\n          "attribution": {\n            "supplier": "Assessment assembler",\n            "rationale": "Synthetic assessment."\n          },\n          "basis": {\n            "source": {\n              "invariant": "00000000-0000-4000-8000-000000000002",\n              "invariant_statement": "An expression is evaluated once."\n            },\n            "target": {\n              "snapshot": {\n                "repository": {\n                  "schema_version": 1,\n                  "provider": "github",\n                  "provider_repository_id": "1001"\n                },\n                "revision": {\n                  "schema_version": 1,\n                  "kind": "commit",\n                  "algorithm": "sha1",\n                  "full_digest": "1111111111111111111111111111111111111111"\n                }\n              },\n              "declared_host": "github.com",\n              "declared_visibility": "public",\n              "scope": null\n            },\n            "context_statement": null,\n            "conditions": [],\n            "materials": null,\n            "material_omission": null\n          },\n          "opinions": [],\n          "conflicts": [],\n          "overall_opinion": null\n        },\n        "scope": "Only the supplied statement was considered.",\n        "judgment": "No execution evidence was assessed.",\n        "attribution": {\n          "supplier": "Review relay",\n          "rationale": "Newly authored example judgment; no historical authorship is claimed."\n        }\n      },\n      "reviewer": "Lin",\n      "source": {\n        "schema_version": 1,\n        "format_name": "attribution-example",\n        "format_version": "1",\n        "canonicalization": "json-sort-keys-compact-utf8-lf-v1",\n        "sha256": "ad9d501dcfe631958d3ea1798db9b01b01783d5c97a46984a06fd926d890f2dd",\n        "byte_length": 128\n      },\n      "attribution": {\n        "supplier": "Attribution clerk",\n        "rationale": "Fictional example: the supplied judgment is attributed to Lin."\n      }\n    },\n    {\n      "review": {\n        "assessment": {\n          "attribution": {\n            "supplier": "Assessment assembler",\n            "rationale": "Synthetic assessment."\n          },\n          "basis": {\n            "source": {\n              "invariant": "00000000-0000-4000-8000-000000000002",\n              "invariant_statement": "An expression is evaluated once."\n            },\n            "target": {\n              "snapshot": {\n                "repository": {\n                  "schema_version": 1,\n                  "provider": "github",\n                  "provider_repository_id": "1001"\n                },\n                "revision": {\n                  "schema_version": 1,\n                  "kind": "commit",\n                  "algorithm": "sha1",\n                  "full_digest": "1111111111111111111111111111111111111111"\n                }\n              },\n              "declared_host": "github.com",\n              "declared_visibility": "public",\n              "scope": null\n            },\n            "context_statement": null,\n            "conditions": [],\n            "materials": null,\n            "material_omission": null\n          },\n          "opinions": [],\n          "conflicts": [],\n          "overall_opinion": null\n        },\n        "scope": "Only the supplied statement was considered.",\n        "judgment": "No execution evidence was assessed.",\n        "attribution": {\n          "supplier": "Review relay",\n          "rationale": "Newly authored example judgment; no historical authorship is claimed."\n        }\n      },\n      "reviewer": null,\n      "source": null,\n      "attribution": {\n        "supplier": "Archive clerk",\n        "rationale": "No author of this supplied judgment is established; no source record is supplied."\n      }\n    },\n    {\n      "review": {\n        "assessment": {\n          "attribution": {\n            "supplier": "Assessment assembler",\n            "rationale": "Synthetic assessment."\n          },\n          "basis": {\n            "source": {\n              "invariant": "00000000-0000-4000-8000-000000000002",\n              "invariant_statement": "An expression is evaluated once."\n            },\n            "target": {\n              "snapshot": {\n                "repository": {\n                  "schema_version": 1,\n                  "provider": "github",\n                  "provider_repository_id": "1001"\n                },\n                "revision": {\n                  "schema_version": 1,\n                  "kind": "commit",\n                  "algorithm": "sha1",\n                  "full_digest": "1111111111111111111111111111111111111111"\n                }\n              },\n              "declared_host": "github.com",\n              "declared_visibility": "public",\n              "scope": null\n            },\n            "context_statement": null,\n            "conditions": [],\n            "materials": null,\n            "material_omission": null\n          },\n          "opinions": [],\n          "conflicts": [],\n          "overall_opinion": null\n        },\n        "scope": "Only the supplied statement was considered.",\n        "judgment": "No execution evidence was assessed.",\n        "attribution": {\n          "supplier": "Review relay",\n          "rationale": "Newly authored example judgment; no historical authorship is claimed."\n        }\n      },\n      "reviewer": "Mo",\n      "source": null,\n      "attribution": {\n        "supplier": "Second clerk",\n        "rationale": "Competing fictional attribution; no winner is inferred."\n      }\n    },\n    {\n      "review": {\n        "assessment": {\n          "attribution": {\n            "supplier": "Assessment assembler",\n            "rationale": "Synthetic assessment."\n          },\n          "basis": {\n            "source": {\n              "invariant": "00000000-0000-4000-8000-000000000002",\n              "invariant_statement": "An expression is evaluated once."\n            },\n            "target": {\n              "snapshot": {\n                "repository": {\n                  "schema_version": 1,\n                  "provider": "github",\n                  "provider_repository_id": "1001"\n                },\n                "revision": {\n                  "schema_version": 1,\n                  "kind": "commit",\n                  "algorithm": "sha1",\n                  "full_digest": "1111111111111111111111111111111111111111"\n                }\n              },\n              "declared_host": "github.com",\n              "declared_visibility": "public",\n              "scope": null\n            },\n            "context_statement": null,\n            "conditions": [],\n            "materials": null,\n            "material_omission": null\n          },\n          "opinions": [],\n          "conflicts": [],\n          "overall_opinion": null\n        },\n        "scope": "Only the supplied statement was considered.",\n        "judgment": "No execution evidence was assessed.",\n        "attribution": {\n          "supplier": "Review relay",\n          "rationale": "Newly authored example judgment; no historical authorship is claimed."\n        }\n      },\n      "reviewer": "Lin",\n      "source": {\n        "schema_version": 1,\n        "format_name": "attribution-example",\n        "format_version": "1",\n        "canonicalization": "json-sort-keys-compact-utf8-lf-v1",\n        "sha256": "ad9d501dcfe631958d3ea1798db9b01b01783d5c97a46984a06fd926d890f2dd",\n        "byte_length": 128\n      },\n      "attribution": {\n        "supplier": "Attribution clerk",\n        "rationale": "Fictional example: the supplied judgment is attributed to Lin."\n      }\n    }\n  ]\n}\n',
    "parallel.expected.json": b'{"attributions":[{"attribution":{"rationale":"Fictional example: the supplied judgment is attributed to Lin.","supplier":"Attribution clerk"},"review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":"Only the supplied statement was considered."},"reviewer":"Lin","source":{"byte_length":128,"canonicalization":"json-sort-keys-compact-utf8-lf-v1","format_name":"attribution-example","format_version":"1","schema_version":1,"sha256":"ad9d501dcfe631958d3ea1798db9b01b01783d5c97a46984a06fd926d890f2dd"}},{"attribution":{"rationale":"No author of this supplied judgment is established; no source record is supplied.","supplier":"Archive clerk"},"review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":"Only the supplied statement was considered."},"reviewer":null,"source":null},{"attribution":{"rationale":"Competing fictional attribution; no winner is inferred.","supplier":"Second clerk"},"review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":"Only the supplied statement was considered."},"reviewer":"Mo","source":null},{"attribution":{"rationale":"Fictional example: the supplied judgment is attributed to Lin.","supplier":"Attribution clerk"},"review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":"Only the supplied statement was considered."},"reviewer":"Lin","source":{"byte_length":128,"canonicalization":"json-sort-keys-compact-utf8-lf-v1","format_name":"attribution-example","format_version":"1","schema_version":1,"sha256":"ad9d501dcfe631958d3ea1798db9b01b01783d5c97a46984a06fd926d890f2dd"}}],"format":"faultatlas-supplied-review","review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":"Only the supplied statement was considered."},"version":1}\n',
    "parallel.expected-view.txt": b'Supplied review attributions - non-authoritative inspection\nComplete review value:\nSupplied assessment reviews - non-authoritative inspection\nComplete target assessment:\nSupplied assessment - structural inspection only\nSource invariant: "00000000-0000-4000-8000-000000000002"\nSource statement: "An expression is evaluated once."\nTarget snapshot: {"repository":{"schema_version":1,"provider":"github","provider_repository_id":"1001"},"revision":{"schema_version":1,"kind":"commit","algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111"}}\nHost/visibility: caller-declared "github.com" / "public"; not externally verified\nPath scope: not supplied; no whole-repository coverage inferred\nContext: not supplied\nAssessment supplier: "Assessment assembler"\nRationale: "Synthetic assessment."\nRoot attribution covers assembly, context and condition inventory; source authorship and authentication are not established.\nConditions: none supplied; no requirement success inferred\nMaterials: not supplied\nOpinions: none supplied\nConflicts: none supplied; no absence-of-conflict claim\nOverall opinion: not supplied; none inferred\nStructural checks: passed; no applicability or repair certification\nEnd of complete view\nSupplied review records: 1\nReview targets: all supplied records match the complete requested assessment value\nReview 1\nSupplied scope (coverage declaration only): "Only the supplied statement was considered."\nSupplied judgment: "No execution evidence was assessed."\nSupplied record supplier: "Review relay"\nSupplied rationale: "Newly authored example judgment; no historical authorship is claimed."\nScope is supplied prose; structural checks do not verify examination coverage.\nAttribution is supplied: the record supplier label need not name the reviewer; reviewer identity and independence are not established.\nMaterial names in review text are prose; no material selection, access or support is validated.\nA matching value does not establish freshness, withdrawal status or later-policy applicability.\nNo authentication, approval, score, winner, review lifecycle or persistence is inferred.\nEnd of complete review view\nAttribution declarations: 4\nAttribution targets: all declarations match the complete requested review value\nAttribution 1\nAttribution assertion supplier: "Attribution clerk"\nAttribution assertion rationale: "Fictional example: the supplied judgment is attributed to Lin."\nAttributed reviewer: "Lin"\nSource record association: {"schema_version":1,"format_name":"attribution-example","format_version":"1","canonicalization":"json-sort-keys-compact-utf8-lf-v1","sha256":"ad9d501dcfe631958d3ea1798db9b01b01783d5c97a46984a06fd926d890f2dd","byte_length":128}\nAttribution 2\nAttribution assertion supplier: "Archive clerk"\nAttribution assertion rationale: "No author of this supplied judgment is established; no source record is supplied."\nAttributed reviewer: explicitly unknown\nSource record association: none supplied; availability not asserted\nAttribution 3\nAttribution assertion supplier: "Second clerk"\nAttribution assertion rationale: "Competing fictional attribution; no winner is inferred."\nAttributed reviewer: "Mo"\nSource record association: none supplied; availability not asserted\nAttribution 4\nAttribution assertion supplier: "Attribution clerk"\nAttribution assertion rationale: "Fictional example: the supplied judgment is attributed to Lin."\nAttributed reviewer: "Lin"\nSource record association: {"schema_version":1,"format_name":"attribution-example","format_version":"1","canonicalization":"json-sort-keys-compact-utf8-lf-v1","sha256":"ad9d501dcfe631958d3ea1798db9b01b01783d5c97a46984a06fd926d890f2dd","byte_length":128}\nAttribution labels are supplied claims; account identity, authorship and independence are not verified.\nSource records are associated by declaration; bytes are not retrieved or verified as support.\nEquality identifies the supplied review value, not a particular repeated occurrence.\nNo availability status, approval, confidence or review lifecycle is inferred.\nEnd of complete review attribution view\n',
    "sparse-empty.input.json": b'{\n  "format": "faultatlas-supplied-review",\n  "version": 1,\n  "review": {\n    "assessment": {\n      "attribution": {\n        "supplier": "Assessment assembler",\n        "rationale": "Synthetic assessment."\n      },\n      "basis": {\n        "source": {\n          "invariant": "00000000-0000-4000-8000-000000000002",\n          "invariant_statement": "An expression is evaluated once."\n        },\n        "target": {\n          "snapshot": {\n            "repository": {\n              "provider": "github",\n              "provider_repository_id": "1001"\n            },\n            "revision": {\n              "kind": "commit",\n              "algorithm": "sha1",\n              "full_digest": "1111111111111111111111111111111111111111"\n            }\n          },\n          "declared_host": "github.com",\n          "declared_visibility": "public"\n        }\n      }\n    },\n    "scope": "Only the supplied statement was considered.",\n    "judgment": "No execution evidence was assessed.",\n    "attribution": {\n      "supplier": "Review relay",\n      "rationale": "Newly authored example judgment; no historical authorship is claimed."\n    }\n  },\n  "attributions": []\n}\n',
    "sparse-empty.expected.json": b'{"attributions":[],"format":"faultatlas-supplied-review","review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":"Only the supplied statement was considered."},"version":1}\n',
    "sparse-empty.expected-view.txt": b'Supplied review attributions - non-authoritative inspection\nComplete review value:\nSupplied assessment reviews - non-authoritative inspection\nComplete target assessment:\nSupplied assessment - structural inspection only\nSource invariant: "00000000-0000-4000-8000-000000000002"\nSource statement: "An expression is evaluated once."\nTarget snapshot: {"repository":{"schema_version":1,"provider":"github","provider_repository_id":"1001"},"revision":{"schema_version":1,"kind":"commit","algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111"}}\nHost/visibility: caller-declared "github.com" / "public"; not externally verified\nPath scope: not supplied; no whole-repository coverage inferred\nContext: not supplied\nAssessment supplier: "Assessment assembler"\nRationale: "Synthetic assessment."\nRoot attribution covers assembly, context and condition inventory; source authorship and authentication are not established.\nConditions: none supplied; no requirement success inferred\nMaterials: not supplied\nOpinions: none supplied\nConflicts: none supplied; no absence-of-conflict claim\nOverall opinion: not supplied; none inferred\nStructural checks: passed; no applicability or repair certification\nEnd of complete view\nSupplied review records: 1\nReview targets: all supplied records match the complete requested assessment value\nReview 1\nSupplied scope (coverage declaration only): "Only the supplied statement was considered."\nSupplied judgment: "No execution evidence was assessed."\nSupplied record supplier: "Review relay"\nSupplied rationale: "Newly authored example judgment; no historical authorship is claimed."\nScope is supplied prose; structural checks do not verify examination coverage.\nAttribution is supplied: the record supplier label need not name the reviewer; reviewer identity and independence are not established.\nMaterial names in review text are prose; no material selection, access or support is validated.\nA matching value does not establish freshness, withdrawal status or later-policy applicability.\nNo authentication, approval, score, winner, review lifecycle or persistence is inferred.\nEnd of complete review view\nAttribution declarations: 0\nAttributions: none supplied; no reviewer inferred\nAttribution labels are supplied claims; account identity, authorship and independence are not verified.\nSource records are associated by declaration; bytes are not retrieved or verified as support.\nEquality identifies the supplied review value, not a particular repeated occurrence.\nNo availability status, approval, confidence or review lifecycle is inferred.\nEnd of complete review attribution view\n',
    "valid-target-mismatch.input.json": b'{"attributions":[{"attribution":{"rationale":"Fictional example: the supplied judgment is attributed to Lin.","supplier":"Attribution clerk"},"review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":"Only the supplied statement was considered."},"reviewer":"Lin","source":{"byte_length":128,"canonicalization":"json-sort-keys-compact-utf8-lf-v1","format_name":"attribution-example","format_version":"1","schema_version":1,"sha256":"ad9d501dcfe631958d3ea1798db9b01b01783d5c97a46984a06fd926d890f2dd"}},{"attribution":{"rationale":"No author of this supplied judgment is established; no source record is supplied.","supplier":"Archive clerk"},"review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":"Only the supplied statement was considered."},"reviewer":null,"source":null},{"attribution":{"rationale":"Competing fictional attribution; no winner is inferred.","supplier":"Second clerk"},"review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":"Only the supplied statement was considered."},"reviewer":"Mo","source":null},{"attribution":{"rationale":"Fictional example: the supplied judgment is attributed to Lin.","supplier":"Attribution clerk"},"review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":"Only the supplied statement was considered."},"reviewer":"Lin","source":{"byte_length":128,"canonicalization":"json-sort-keys-compact-utf8-lf-v1","format_name":"attribution-example","format_version":"1","schema_version":1,"sha256":"ad9d501dcfe631958d3ea1798db9b01b01783d5c97a46984a06fd926d890f2dd"}}],"format":"faultatlas-supplied-review","review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"Changed supplied judgment; attribution targets still name the original.","scope":"Only the supplied statement was considered."},"version":1}\n',
    "unicode.input.json": b'{\n  "format": "faultatlas-supplied-review",\n  "version": 1,\n  "review": {\n    "assessment": {\n      "attribution": {\n        "supplier": "Assessment assembler",\n        "rationale": "Synthetic assessment."\n      },\n      "basis": {\n        "source": {\n          "invariant": "00000000-0000-4000-8000-000000000002",\n          "invariant_statement": "An expression is evaluated once."\n        },\n        "target": {\n          "snapshot": {\n            "repository": {\n              "schema_version": 1,\n              "provider": "github",\n              "provider_repository_id": "1001"\n            },\n            "revision": {\n              "schema_version": 1,\n              "kind": "commit",\n              "algorithm": "sha1",\n              "full_digest": "1111111111111111111111111111111111111111"\n            }\n          },\n          "declared_host": "github.com",\n          "declared_visibility": "public",\n          "scope": null\n        },\n        "context_statement": null,\n        "conditions": [],\n        "materials": null,\n        "material_omission": null\n      },\n      "opinions": [],\n      "conflicts": [],\n      "overall_opinion": null\n    },\n    "scope": " Escapes: \\n\\t\\u001b\\u007f\\u202e\\ud83d\\ude80 \\" \\\\ ",\n    "judgment": "No execution evidence was assessed.",\n    "attribution": {\n      "supplier": "Review relay",\n      "rationale": "Newly authored example judgment; no historical authorship is claimed."\n    }\n  },\n  "attributions": []\n}\n',
    "unicode.expected.json": b'{"attributions":[],"format":"faultatlas-supplied-review","review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":" Escapes: \\n\\t\\u001b\x7f\xe2\x80\xae\xf0\x9f\x9a\x80 \\" \\\\ "},"version":1}\n',
    "unicode.expected-view.txt": b'Supplied review attributions - non-authoritative inspection\nComplete review value:\nSupplied assessment reviews - non-authoritative inspection\nComplete target assessment:\nSupplied assessment - structural inspection only\nSource invariant: "00000000-0000-4000-8000-000000000002"\nSource statement: "An expression is evaluated once."\nTarget snapshot: {"repository":{"schema_version":1,"provider":"github","provider_repository_id":"1001"},"revision":{"schema_version":1,"kind":"commit","algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111"}}\nHost/visibility: caller-declared "github.com" / "public"; not externally verified\nPath scope: not supplied; no whole-repository coverage inferred\nContext: not supplied\nAssessment supplier: "Assessment assembler"\nRationale: "Synthetic assessment."\nRoot attribution covers assembly, context and condition inventory; source authorship and authentication are not established.\nConditions: none supplied; no requirement success inferred\nMaterials: not supplied\nOpinions: none supplied\nConflicts: none supplied; no absence-of-conflict claim\nOverall opinion: not supplied; none inferred\nStructural checks: passed; no applicability or repair certification\nEnd of complete view\nSupplied review records: 1\nReview targets: all supplied records match the complete requested assessment value\nReview 1\nSupplied scope (coverage declaration only): " Escapes: \\n\\t\\u001b\\u007f\\u202e\\ud83d\\ude80 \\" \\\\ "\nSupplied judgment: "No execution evidence was assessed."\nSupplied record supplier: "Review relay"\nSupplied rationale: "Newly authored example judgment; no historical authorship is claimed."\nScope is supplied prose; structural checks do not verify examination coverage.\nAttribution is supplied: the record supplier label need not name the reviewer; reviewer identity and independence are not established.\nMaterial names in review text are prose; no material selection, access or support is validated.\nA matching value does not establish freshness, withdrawal status or later-policy applicability.\nNo authentication, approval, score, winner, review lifecycle or persistence is inferred.\nEnd of complete review view\nAttribution declarations: 0\nAttributions: none supplied; no reviewer inferred\nAttribution labels are supplied claims; account identity, authorship and independence are not verified.\nSource records are associated by declaration; bytes are not retrieved or verified as support.\nEquality identifies the supplied review value, not a particular repeated occurrence.\nNo availability status, approval, confidence or review lifecycle is inferred.\nEnd of complete review attribution view\n',
    "duplicate-key.input.json": b'{"format":"faultatlas-supplied-review","version":1,"\\u0076ersion":1,"review":{},"attributions":[]}\n',
    "float.input.json": b'{"format":"faultatlas-supplied-review","version":1.0,"review":{},"attributions":[]}\n',
    "bool-version.input.json": b'{"attributions":[],"format":"faultatlas-supplied-review","review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":"Only the supplied statement was considered."},"version":true}\n',
    "bom.input.bin": b'\xef\xbb\xbf{"attributions":[],"format":"faultatlas-supplied-review","review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":"Only the supplied statement was considered."},"version":1}\n',
    "invalid-utf8.input.bin": b"\xff",
    "nine-attributions.input.json": b'{"attributions":[{},{},{},{},{},{},{},{},{}],"format":"faultatlas-supplied-review","review":{"assessment":{"attribution":{"rationale":"Synthetic assessment.","supplier":"Assessment assembler"},"basis":{"conditions":[],"context_statement":null,"material_omission":null,"materials":null,"source":{"invariant":"00000000-0000-4000-8000-000000000002","invariant_statement":"An expression is evaluated once."},"target":{"declared_host":"github.com","declared_visibility":"public","scope":null,"snapshot":{"repository":{"provider":"github","provider_repository_id":"1001","schema_version":1},"revision":{"algorithm":"sha1","full_digest":"1111111111111111111111111111111111111111","kind":"commit","schema_version":1}}}},"conflicts":[],"opinions":[],"overall_opinion":null},"attribution":{"rationale":"Newly authored example judgment; no historical authorship is claimed.","supplier":"Review relay"},"judgment":"No execution evidence was assessed.","scope":"Only the supplied statement was considered."},"version":1}\n',
}

ORACLE_IDENTITIES = {
    "parallel.input.json": (
        9106,
        "dc731892a5cd55fdd8a9a25a0530fd680ce9f6f85851dda0499113efbc65b20d",
    ),
    "parallel.expected.json": (
        5702,
        "3d219ccf0d1ea66a3d24cb50e57174fc5f8bb08d434a10a1fbcbbde4db73602f",
    ),
    "parallel.expected-view.txt": (
        4080,
        "e8392b028ba29ec2d89fbae939f4bd6891bb2cf62f978f75e90798ada4ddf16f",
    ),
    "sparse-empty.input.json": (
        1159,
        "530004a194da8feb5e2ab63ddab8b0733cee5f908e2d5952bf1881bb6b37858f",
    ),
    "sparse-empty.expected.json": (
        982,
        "ddd10452c3f5f45220087e31069addbb8fe493e897d6bae02df4a1501013972f",
    ),
    "sparse-empty.expected-view.txt": (
        2627,
        "8297c6942ffd6e23f243fd3d2c8346e1df9dcf6062a2c43f2c1d8baedff18990",
    ),
    "valid-target-mismatch.input.json": (
        5738,
        "9feeef461c4f198f77c448feb893fc2bcd3c22db6e109e799024b14373648e7a",
    ),
    "unicode.input.json": (
        1461,
        "9e2988389cc319c59821e032d794f1724f1b848684df910ac75b5ac7c7ac4db7",
    ),
    "unicode.expected.json": (
        974,
        "c09bc530ebf1617e24323d6cbc7e268bcc88c163c47ec256427ec9aae6fecc08",
    ),
    "unicode.expected-view.txt": (
        2635,
        "2e6acbdae43ddaa236b50d0f9a0f51a422cc0433e7224710faf99bdaa61af5f3",
    ),
    "duplicate-key.input.json": (
        99,
        "bc9881bd8769c56fec46e441010452214300a065d68dcc9838be1cad86e61930",
    ),
    "float.input.json": (
        84,
        "2e14dc935691c5cdfc9b5971d24ec89fe6cf111379478881f38482747be069b2",
    ),
    "bool-version.input.json": (
        985,
        "7eba1337a7c90ff60b61edbfc732adcd020d870b181b61ead9fc628a10bfd545",
    ),
    "bom.input.bin": (
        985,
        "7785a782ddb227605dec4b6449651ddf304cc1eae19fa68ae7a31385a603b406",
    ),
    "invalid-utf8.input.bin": (
        1,
        "a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89",
    ),
    "nine-attributions.input.json": (
        1008,
        "aae980e28268645e7e68cb98d378da3f3399fa02c753e37deaac58052753344d",
    ),
}


def _wire(name: str = "parallel") -> dict[str, Any]:
    return json.loads(ORACLES[name + ".expected.json"])


def _raw(wire: Any) -> bytes:
    return json.dumps(wire, ensure_ascii=True, separators=(",", ":")).encode()


def _pair(
    wire: dict[str, Any] | None = None,
) -> tuple[SuppliedAssessmentReview, tuple[SuppliedAssessmentReviewAttribution, ...]]:
    value = _wire() if wire is None else wire
    return (
        SuppliedAssessmentReview.model_validate_json(_raw(value["review"])),
        tuple(
            SuppliedAssessmentReviewAttribution.model_validate_json(_raw(item))
            for item in value["attributions"]
        ),
    )


def _metrics(value: Any) -> tuple[int, int, int, int]:
    # An independent iterative count of authored JSON, never a production walker.
    stack = [(value, 0)]
    nodes = objects = characters = deepest = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if isinstance(item, dict):
            objects += 1
            deepest = max(deepest, depth + 1)
            stack.extend(
                (x, depth + 1)
                for pair in cast(dict[str, Any], item).items()
                for x in pair
            )
        elif isinstance(item, list):
            deepest = max(deepest, depth + 1)
            stack.extend((x, depth + 1) for x in cast(list[Any], item))
        elif isinstance(item, str):
            characters += len(item)
    return nodes, objects, characters, deepest


def test_all_frozen_oracle_bytes_retain_their_original_identities() -> None:
    assert len(ORACLES) == len(ORACLE_IDENTITIES) == 16
    for name, (length, digest) in ORACLE_IDENTITIES.items():
        assert len(ORACLES[name]) == length
        assert hashlib.sha256(ORACLES[name]).hexdigest() == digest


@pytest.mark.parametrize("name", ("parallel", "sparse-empty", "unicode"))
def test_complete_frozen_value_bytes_and_view_round_trips(name: str) -> None:
    raw = ORACLES[name + ".input.json"]
    before = bytes(raw)
    wire = _wire(name)
    pair = document.decode_assessment_review_document(raw)
    assert type(pair) is tuple and type(pair[1]) is tuple
    assert type(pair[0]) is SuppliedAssessmentReview
    assert all(type(item) is SuppliedAssessmentReviewAttribution for item in pair[1])
    assert pair[0].model_dump(mode="json") == wire["review"]
    assert [a.model_dump(mode="json") for a in pair[1]] == wire["attributions"]
    assert pair == _pair(wire)
    assert (
        document.encode_assessment_review_document(*pair)
        == ORACLES[name + ".expected.json"]
    )
    assert (
        document.decode_assessment_review_document(ORACLES[name + ".expected.json"])
        == pair
    )
    assert (
        document.inspect_assessment_review_document(raw).encode()
        == ORACLES[name + ".expected-view.txt"]
    )
    assert raw == before
    created = SuppliedAssessmentReview(
        assessment=pair[0].assessment,
        scope=pair[0].scope,
        judgment=pair[0].judgment,
        attribution=pair[0].attribution,
    )
    assert (
        document.encode_assessment_review_document(created, pair[1])
        == ORACLES[name + ".expected.json"]
    )


def test_duplicate_competing_unknown_and_reference_values_survive() -> None:
    review, assertions = document.decode_assessment_review_document(
        ORACLES["parallel.input.json"]
    )
    assert assertions[0] == assertions[3]
    assert [a.reviewer for a in assertions] == ["Lin", None, "Mo", "Lin"]
    assert review.attribution.supplier == "Review relay"
    assert assertions[0].attribution.supplier == "Attribution clerk"
    reversed_pair = review, tuple(reversed(assertions))
    encoded = document.encode_assessment_review_document(*reversed_pair)
    assert document.decode_assessment_review_document(encoded) == reversed_pair
    assert json.loads(encoded)["attributions"] == list(
        reversed(_wire()["attributions"])
    )
    changed = _wire()
    changed["attributions"][1]["reviewer"] = "unknown"
    changed["attributions"][0]["source"]["sha256"] = "b" * 64
    changed["attributions"][0]["source"]["format_version"] = "2"
    pair = document.decode_assessment_review_document(_raw(changed))
    assert pair[1][1].reviewer == "unknown" and pair[1][1].source is None
    assert pair[0].assessment.basis.materials is None
    assert pair[1][0].source is not None
    assert (
        pair[1][0].source.model_dump(mode="json")
        == changed["attributions"][0]["source"]
    )
    view = document.inspect_assessment_review_document(_raw(changed))
    assert "bytes are not retrieved or verified as support" in view
    assert 'Attributed reviewer: "unknown"' in view


@pytest.mark.parametrize(
    "name,message",
    (
        (
            "valid-target-mismatch.input.json",
            "attribution at index 0 target does not match requested review",
        ),
        ("duplicate-key.input.json", "P09 review document: INVALID_JSON"),
        ("float.input.json", "P09 review document: INVALID_JSON"),
        ("bool-version.input.json", "P09 review document: UNSUPPORTED_VERSION"),
        ("bom.input.bin", "P09 review document: INVALID_ENCODING"),
        ("invalid-utf8.input.bin", "P09 review document: INVALID_ENCODING"),
        (
            "nine-attributions.input.json",
            "attributions must contain at most 8 supplied attribution declarations",
        ),
    ),
)
@pytest.mark.parametrize("operation", ("decode", "inspect"))
def test_exact_frozen_refusal_oracles(name: str, message: str, operation: str) -> None:
    if name == "valid-target-mismatch.input.json":
        wire = json.loads(ORACLES[name])
        review, assertions = _pair(wire)
        assert review != assertions[0].review
        assert review.assessment == assertions[0].review.assessment
    function = getattr(document, operation + "_assessment_review_document")
    with pytest.raises(ValueError, match="^" + re.escape(message) + "$"):
        function(ORACLES[name])


@pytest.mark.parametrize("raw", (b"", b" ", b"{}{}", b"{} trailing", b"[}", b"]"))
def test_invalid_single_document_syntax_has_fixed_diagnostic(raw: bytes) -> None:
    with pytest.raises(ValueError, match="^P09 review document: INVALID_JSON$"):
        document.decode_assessment_review_document(raw)


@pytest.mark.parametrize(
    "token",
    (
        "1.0",
        "1e0",
        "NaN",
        "Infinity",
        "-Infinity",
        str(2**63),
        str(-(2**63) - 1),
        "1" * 21,
    ),
)
def test_numeric_grammar_is_global_and_precedes_shape(token: str) -> None:
    raw = ('{"otherwise_unknown":' + token + "}").encode()
    with pytest.raises(ValueError, match="^P09 review document: INVALID_JSON$"):
        document.decode_assessment_review_document(raw)


@pytest.mark.parametrize("token", (str(-(2**63)), str(2**63 - 1), "-0", "true", "null"))
def test_admitted_scalar_grammar_can_reach_shape_refusal(token: str) -> None:
    with pytest.raises(ValueError, match="^P09 review document: INVALID_SHAPE$"):
        document.decode_assessment_review_document(token.encode())


@pytest.mark.parametrize("value", (None, True, 1, [], {}, "wrong"))
@pytest.mark.parametrize("key", ("format", "version"))
def test_exact_format_and_version_types(key: str, value: Any) -> None:
    wire = _wire("sparse-empty")
    wire[key] = value
    if key == "version" and type(value) is int and value == 1:
        assert document.decode_assessment_review_document(_raw(wire)) == _pair(wire)
    else:
        with pytest.raises(
            ValueError, match=f"^P09 review document: UNSUPPORTED_{key.upper()}$"
        ):
            document.decode_assessment_review_document(_raw(wire))


@pytest.mark.parametrize("key", ("format", "version", "review", "attributions"))
def test_envelope_fields_are_required(key: str) -> None:
    wire = _wire()
    del wire[key]
    with pytest.raises(ValueError, match="^P09 review document: INVALID_SHAPE$"):
        document.decode_assessment_review_document(_raw(wire))


@pytest.mark.parametrize("value", (None, "bad", 1, []))
def test_review_must_be_an_object(value: Any) -> None:
    wire = _wire()
    wire["review"] = value
    with pytest.raises(ValueError, match="^P09 review document: INVALID_SHAPE$"):
        document.decode_assessment_review_document(_raw(wire))


@pytest.mark.parametrize("value", (None, "bad", 1, {}))
def test_assertions_must_be_an_array(value: Any) -> None:
    wire = _wire()
    wire["attributions"] = value
    with pytest.raises(ValueError, match="^P09 review document: INVALID_SHAPE$"):
        document.decode_assessment_review_document(_raw(wire))


def test_extra_envelope_and_child_fields_retain_different_errors() -> None:
    wire = _wire()
    with pytest.raises(ValueError, match="^P09 review document: INVALID_SHAPE$"):
        document.decode_assessment_review_document(_raw(wire | {"status": "approved"}))
    wire["review"]["status"] = "approved"
    with pytest.raises(ValidationError) as failure:
        document.decode_assessment_review_document(_raw(wire))
    assert failure.value.errors()[0]["loc"] == ("status",)
    assert failure.value.errors()[0]["type"] == "extra_forbidden"


def test_exact_bytes_type_never_converts_or_consumes_inputs() -> None:
    class BytesChild(bytes):
        pass

    class Unconvertible:
        def __bytes__(self) -> bytes:
            raise AssertionError("must not convert")

        def __iter__(self) -> Any:
            raise AssertionError("must not iterate")

    for value in (
        None,
        "{}",
        bytearray(b"{}"),
        memoryview(b"{}"),
        BytesChild(b"{}"),
        Unconvertible(),
    ):
        for function in (
            document.decode_assessment_review_document,
            document.inspect_assessment_review_document,
        ):
            with pytest.raises(
                ValueError, match="^P09 review document: BYTES_REQUIRED$"
            ):
                function(cast(Any, value))


def test_python_encoder_retains_s02_argument_and_owner_failures() -> None:
    review, assertions = _pair()

    class TupleChild(tuple[SuppliedAssessmentReviewAttribution, ...]):
        pass

    def untouched() -> Any:
        raise AssertionError("must not consume")
        yield assertions[0]

    bad_inputs: tuple[Any, ...] = ([], TupleChild(assertions), untouched(), None)
    for value in bad_inputs:
        with pytest.raises(ValueError, match="^attributions must be a tuple$"):
            document.encode_assessment_review_document(review, value)
    with pytest.raises(ValueError, match="^review must be a SuppliedAssessmentReview$"):
        document.encode_assessment_review_document(cast(Any, {}), ())
    invalid_review = review.model_copy(update={"scope": ""})
    with pytest.raises(
        ValueError,
        match="^attributions must contain at most 8 supplied attribution declarations$",
    ):
        document.encode_assessment_review_document(invalid_review, assertions[:1] * 9)
    with pytest.raises(
        ValueError,
        match="^attribution at index 1 must be a SuppliedAssessmentReviewAttribution$",
    ):
        document.encode_assessment_review_document(
            review, (assertions[0], cast(Any, {}))
        )
    with pytest.raises(ValidationError) as failure:
        document.encode_assessment_review_document(invalid_review, ())
    assert failure.value.errors()[0]["loc"] == ("scope",)
    with pytest.raises(ValidationError) as failure:
        document.encode_assessment_review_document(
            review, (assertions[0].model_copy(update={"review": invalid_review}),)
        )
    assert failure.value.errors()[0]["loc"] == ("review", "scope")
    source = assertions[0].source
    assert source is not None
    with pytest.raises(ValidationError) as failure:
        document.encode_assessment_review_document(
            review,
            (
                assertions[0].model_copy(
                    update={"source": source.model_copy(update={"sha256": "bad"})}
                ),
            ),
        )
    assert failure.value.errors()[0]["loc"][0] == "source"


@pytest.mark.parametrize("field", ("reviewer", "source"))
def test_nullable_assertion_fields_are_still_required(field: str) -> None:
    wire = _wire()
    del wire["attributions"][1][field]
    with pytest.raises(ValidationError) as failure:
        document.decode_assessment_review_document(_raw(wire))
    assert failure.value.errors()[0]["loc"] == (field,)
    assert failure.value.errors()[0]["type"] == "missing"


@pytest.mark.parametrize(
    "change",
    ("judgment", "opinion", "opinion_order", "nested_attribution", "review_supplier"),
)
def test_independently_valid_whole_target_mismatches(change: str) -> None:
    original = rich_review_wire()
    changed = copy.deepcopy(original)
    if change == "judgment":
        changed["judgment"] = "Different supplied judgment."
    elif change == "opinion":
        changed["assessment"]["opinions"][0]["statement"] = "Different opinion."
    elif change == "opinion_order":
        changed["assessment"]["opinions"].reverse()
    elif change == "nested_attribution":
        changed["assessment"]["opinions"][0]["attribution"]["rationale"] = (
            "Different rationale."
        )
    else:
        changed["attribution"]["supplier"] = "Different review supplier"
    old_review = SuppliedAssessmentReview.model_validate_json(_raw(original))
    requested = SuppliedAssessmentReview.model_validate_json(_raw(changed))
    assert requested != old_review
    assert requested.assessment.basis == old_review.assessment.basis
    assertion = _wire()["attributions"][0]
    assertion["review"] = original
    typed = SuppliedAssessmentReviewAttribution.model_validate_json(_raw(assertion))
    assert typed.review == old_review
    wire: dict[str, Any] = {
        "format": "faultatlas-supplied-review",
        "version": 1,
        "review": changed,
        "attributions": [assertion],
    }
    with pytest.raises(
        ValueError,
        match="^attribution at index 0 target does not match requested review$",
    ):
        document.decode_assessment_review_document(_raw(wire))
    with pytest.raises(
        ValueError,
        match="^attribution at index 0 target does not match requested review$",
    ):
        document.encode_assessment_review_document(requested, (typed,))
    wire["attributions"][0]["review"] = changed
    pair = document.decode_assessment_review_document(_raw(wire))
    assert (
        document.decode_assessment_review_document(
            document.encode_assessment_review_document(*pair)
        )
        == pair
    )


def test_global_admission_then_owner_and_mismatch_order() -> None:
    wire = json.loads(ORACLES["valid-target-mismatch.input.json"])
    _pair(wire)  # Independently valid requested review and every original assertion.
    wire["attributions"][1]["reviewer"] = []  # Parsed, but invalid for its owner.
    with pytest.raises(
        ValueError,
        match="^attribution at index 0 target does not match requested review$",
    ):
        document.decode_assessment_review_document(_raw(wire))
    wire["attributions"][0]["review"]["scope"] = ""
    with pytest.raises(ValidationError) as failure:
        document.decode_assessment_review_document(_raw(wire))
    assert failure.value.errors()[0]["loc"] == ("review", "scope")
    global_bad = json.loads(ORACLES["valid-target-mismatch.input.json"])
    for value, message in (
        (float("nan"), "INVALID_JSON"),
        ("\ud800", "INVALID_ENCODING"),
    ):
        global_bad["attributions"][1]["reviewer"] = value
        with pytest.raises(ValueError, match=f"^P09 review document: {message}$"):
            document.decode_assessment_review_document(_raw(global_bad))
    raw = ORACLES["valid-target-mismatch.input.json"]
    for bad in (
        raw + b"x",
        raw.replace(b'"reviewer":"Lin"', b'"reviewer":"Lin","reviewer":"Mo"', 1),
    ):
        assert bad != raw
        with pytest.raises(ValueError, match="^P09 review document: INVALID_JSON$"):
            document.decode_assessment_review_document(bad)


def test_nested_decoded_duplicate_keys_and_lone_surrogate_keys() -> None:
    raw = ORACLES["parallel.expected.json"]
    bad = raw.replace(
        b'"supplier":"Attribution clerk"',
        b'"supplier":"Attribution clerk","\\u0073upplier":"other"',
        1,
    )
    assert bad != raw
    with pytest.raises(ValueError, match="^P09 review document: INVALID_JSON$"):
        document.decode_assessment_review_document(bad)
    with pytest.raises(ValueError, match="^P09 review document: INVALID_ENCODING$"):
        document.decode_assessment_review_document(b'{"\\ud800":null}')


def test_physical_raw_byte_cap_and_string_aware_depth() -> None:
    raw = ORACLES["sparse-empty.input.json"]
    at_limit = raw + b" " * (16777216 - len(raw))
    assert len(at_limit) == 16777216
    assert (
        document.encode_assessment_review_document(
            *document.decode_assessment_review_document(at_limit)
        )
        == ORACLES["sparse-empty.expected.json"]
    )
    with pytest.raises(ValueError, match="^P09 review document: RESOURCE_LIMIT$"):
        document.decode_assessment_review_document(at_limit + b" ")
    wire = _wire("sparse-empty")
    wire["review"]["scope"] = '[{"\\' * 500 + '"}]' * 500
    pair = document.decode_assessment_review_document(_raw(wire))
    assert pair[0].scope == wire["review"]["scope"]
    with pytest.raises(ValueError, match="^P09 review document: INVALID_SHAPE$"):
        document.decode_assessment_review_document(b"[" * 36 + b"]" * 36)
    with pytest.raises(ValueError, match="^P09 review document: RESOURCE_LIMIT$"):
        document.decode_assessment_review_document(b"[" * 37 + b"]" * 37)


@pytest.mark.parametrize("counter", ("nodes", "objects", "characters"))
def test_physical_raw_tree_limits_precede_schema(counter: str) -> None:
    # These are actual raw-tree limits, intentionally not valid domain examples.
    if counter == "nodes":
        exact: Any = [None] * 74035
        over: Any = exact + [None]
        assert _metrics(exact)[0] == 74036
    elif counter == "objects":
        exact = [{} for _ in range(4651)]
        over = exact + [{}]
        assert _metrics(exact)[1] == 4651
    else:
        exact = {"k": "x" * 1331267}
        over = {"k": "x" * 1331268}
        assert _metrics(exact)[2] == 1331268
    with pytest.raises(ValueError, match="^P09 review document: INVALID_SHAPE$"):
        document.decode_assessment_review_document(_raw(exact))
    with pytest.raises(ValueError, match="^P09 review document: RESOURCE_LIMIT$"):
        document.decode_assessment_review_document(_raw(over))


def test_actual_maximum_fields_and_eight_complete_assertions() -> None:
    wire = _wire()
    review = wire["review"]
    for field in ("scope", "judgment"):
        review[field] = "🚀" * 4096
    review["attribution"] = {"supplier": "🚀" * 128, "rationale": "🚀" * 4096}
    assertion = wire["attributions"][0]
    assertion["review"] = copy.deepcopy(review)
    assertion["reviewer"] = "🚀" * 128
    assertion["attribution"] = {"supplier": "🚀" * 128, "rationale": "🚀" * 4096}
    assertion["source"] = {
        "schema_version": 1,
        "format_name": "f" * 160,
        "format_version": "1" * 64,
        "canonicalization": "c" * 160,
        "sha256": "a" * 64,
        "byte_length": 2**63 - 1,
    }
    wire["attributions"] = [copy.deepcopy(assertion) for _ in range(8)]
    pair = document.decode_assessment_review_document(_raw(wire))
    encoded = document.encode_assessment_review_document(*pair)
    assert json.loads(encoded) == wire
    assert document.decode_assessment_review_document(encoded) == pair
    assert len(encoded) < 9764473 < 16777216
    assert (
        len(document.inspect_assessment_review_document(encoded).encode())
        < 8972288
        < 9437184
    )
    assert all(a == pair[1][0] for a in pair[1]) and len(pair[1]) == 8
    assert all(a <= b for a, b in zip(_metrics(wire), (74036, 4651, 1331268, 36)))
    wire["attributions"][0]["reviewer"] += "🚀"
    with pytest.raises(ValidationError) as failure:
        document.decode_assessment_review_document(_raw(wire))
    assert failure.value.errors()[0]["loc"] == ("reviewer",)


@pytest.mark.parametrize("constant,metric", (("_MAX_NODES", 0), ("_MAX_CHARACTERS", 2)))
def test_normalized_defaults_cannot_escape_injected_tree_guard(
    monkeypatch: pytest.MonkeyPatch, constant: str, metric: int
) -> None:
    raw = json.loads(ORACLES["sparse-empty.input.json"])
    normalized = _wire("sparse-empty")
    assert _metrics(raw)[metric] < _metrics(normalized)[metric]
    # Guard injection, not a claim that this small example reaches a physical cap.
    monkeypatch.setattr(document, constant, _metrics(raw)[metric])
    with pytest.raises(ValueError, match="^P09 review document: RESOURCE_LIMIT$"):
        document.decode_assessment_review_document(_raw(raw))


def test_canonical_size_guard_applies_to_encode_decode_and_inspect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _raw(json.loads(ORACLES["sparse-empty.input.json"]))
    expected = ORACLES["sparse-empty.expected.json"]
    pair = _pair(_wire("sparse-empty"))
    assert len(raw) < len(expected) - 1
    # Explicit output-guard injection; raw intake still fits.
    monkeypatch.setattr(document, "_MAX_BYTES", len(expected) - 1)
    operations = (
        lambda: document.encode_assessment_review_document(*pair),
        lambda: document.decode_assessment_review_document(raw),
        lambda: document.inspect_assessment_review_document(raw),
    )
    for operation in operations:
        with pytest.raises(ValueError, match="^P09 review document: RESOURCE_LIMIT$"):
            operation()


@pytest.mark.parametrize("operation", ("encode", "decode", "inspect"))
def test_one_public_s02_invocation_and_original_failure(
    monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    pair = _pair()
    original = document.inspect_assessment_review_attributions
    calls: list[Any] = []

    def counted(
        review: SuppliedAssessmentReview,
        attributions: tuple[SuppliedAssessmentReviewAttribution, ...],
    ) -> str:
        calls.append((review, attributions))
        return original(review, attributions)

    monkeypatch.setattr(document, "inspect_assessment_review_attributions", counted)
    function = getattr(document, operation + "_assessment_review_document")
    args = pair if operation == "encode" else (ORACLES["parallel.input.json"],)
    function(*args)
    assert calls == [pair]
    calls.clear()
    monkeypatch.setattr(
        attribution_inspection,
        "_MAX_VIEW_BYTES",
        len(ORACLES["parallel.expected-view.txt"]) - 1,
    )
    with pytest.raises(
        ValueError,
        match=r"^P09 review attribution inspection output budget exceeded \(9 MiB\)$",
    ):
        function(*args)
    assert calls == [pair]


def test_revalidation_keeps_declared_owner_values_for_subclasses() -> None:
    class Child(SuppliedAssessmentReview):
        pass

    class AssertionChild(SuppliedAssessmentReviewAttribution):
        pass

    review, assertions = _pair()
    child = Child.model_validate(
        {k: getattr(review, k) for k in SuppliedAssessmentReview.model_fields}
    )
    assertion = assertions[0]
    assertion_child = AssertionChild.model_validate(
        {
            k: getattr(assertion, k)
            for k in SuppliedAssessmentReviewAttribution.model_fields
        }
    )
    encoded = document.encode_assessment_review_document(child, (assertion_child,))
    result = document.decode_assessment_review_document(encoded)
    assert type(result[0]) is SuppliedAssessmentReview
    assert type(result[1][0]) is SuppliedAssessmentReviewAttribution
    assert result == (review, (assertion,))


def test_purity_and_exact_source_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    pair = _pair()
    raw = ORACLES["parallel.input.json"]
    expected = ORACLES["parallel.expected.json"]

    def denied(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("unexpected effect in pure byte operations")

    with monkeypatch.context() as blocked:
        for owner, name in (
            (builtins, "open"),
            (Path, "open"),
            (socket, "socket"),
            (subprocess, "Popen"),
            (time, "time"),
            (uuid, "uuid4"),
            (os, "getenv"),
        ):
            blocked.setattr(owner, name, denied)
        assert document.encode_assessment_review_document(*pair) == expected
        assert document.decode_assessment_review_document(raw) == pair
        assert (
            document.inspect_assessment_review_document(raw).encode()
            == ORACLES["parallel.expected-view.txt"]
        )
    assert document.__all__ == [
        "encode_assessment_review_document",
        "decode_assessment_review_document",
        "inspect_assessment_review_document",
    ]
    for package in (faultatlas, domain_package):
        assert all(not hasattr(package, name) for name in document.__all__)
    source = (
        Path(__file__).resolve().parents[1]
        / "src/faultatlas/assessment_review_document.py"
    )
    tree = ast.parse(source.read_bytes())
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    assert imports == {
        "json",
        "typing",
        "faultatlas.assessment_review_attribution",
        "faultatlas.domain.assessment_review",
        "faultatlas.domain.assessment_review_attribution",
    }
    assert not any(isinstance(n, ast.ClassDef) for n in ast.walk(tree))


def test_installed_document_consumer_reopens_in_a_second_process(
    offline_distributions: tuple[Path, Path], tmp_path: Path
) -> None:
    installed = tmp_path / "installed"
    env = os.environ | {"UV_OFFLINE": "1", "UV_CACHE_DIR": str(tmp_path / "cache")}
    result = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--offline",
            "--no-deps",
            "--target",
            str(installed),
            str(offline_distributions[0]),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for name, value in ORACLES.items():
        (tmp_path / name).write_bytes(value)
    probe = r"""
import json,pathlib,sys
installed=pathlib.Path(sys.argv[1]).resolve()
root=pathlib.Path(sys.argv[2])
stage=sys.argv[3]
sys.path.insert(0,str(installed))
from faultatlas.assessment_review_document import encode_assessment_review_document,decode_assessment_review_document,inspect_assessment_review_document
from faultatlas.domain.assessment_review import SuppliedAssessmentReview
from faultatlas.domain.assessment_review_attribution import SuppliedAssessmentReviewAttribution
for case in ('parallel','sparse-empty','unicode'):
    expected=(root/(case+'.expected.json')).read_bytes()
    wire=json.loads(expected)
    raw=(root/(case+('.input.json' if stage=='produce' else '.saved.json'))).read_bytes()
    pair=decode_assessment_review_document(raw)
    assert type(pair[0]) is SuppliedAssessmentReview and type(pair[1]) is tuple
    assert all(type(a) is SuppliedAssessmentReviewAttribution for a in pair[1])
    assert pair[0].model_dump(mode='json')==wire['review']
    assert [a.model_dump(mode='json') for a in pair[1]]==wire['attributions']
    assert inspect_assessment_review_document(raw).encode()==(root/(case+'.expected-view.txt')).read_bytes()
    encoded=encode_assessment_review_document(*pair)
    assert encoded==expected
    assert decode_assessment_review_document(encoded)==pair
    if stage=='produce':
        with (root/(case+'.saved.json')).open('xb') as destination:
            assert destination.write(encoded)==len(encoded)
bad=(root/'valid-target-mismatch.input.json').read_bytes()
wire=json.loads(bad)
requested=SuppliedAssessmentReview.model_validate_json(json.dumps(wire['review']))
assertion=SuppliedAssessmentReviewAttribution.model_validate_json(json.dumps(wire['attributions'][0]))
assert requested!=assertion.review
try:
    decode_assessment_review_document(bad)
except ValueError as error:
    assert str(error)=='attribution at index 0 target does not match requested review'
else:
    raise AssertionError('valid target mismatch must fail')
for name,module in tuple(sys.modules.items()):
    if name=='faultatlas' or name.startswith('faultatlas.'):
        assert pathlib.Path(module.__file__).resolve().is_relative_to(installed),name
print(stage+' installed complete document PASS')
"""
    for stage in ("produce", "reopen"):
        result = subprocess.run(
            [sys.executable, "-I", "-c", probe, str(installed), str(tmp_path), stage],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stdout.strip() == stage + " installed complete document PASS"
    for case in ("parallel", "sparse-empty", "unicode"):
        assert (tmp_path / (case + ".saved.json")).read_bytes() == ORACLES[
            case + ".expected.json"
        ]
