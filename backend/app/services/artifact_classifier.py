"""
Rule-based artifact type classifier.
Maps filename patterns and text keywords to TMF artifact types.
"""
import re
from typing import Optional

ARTIFACT_TYPES = [
    "FDA_1572",
    "Delegation_Log",
    "IRB_Approval",
    "Monitoring_Visit_Report",
    "SAE_Follow_Up",
    "Investigator_CV",
    "Protocol",
    "Deviation_Log",
    "Informed_Consent",
    "Site_Activation",
    "Other",
]

# (pattern, artifact_type, weight)
_FILENAME_RULES: list[tuple[str, str]] = [
    (r"1572", "FDA_1572"),
    (r"fda.?1572|form.?1572", "FDA_1572"),
    (r"delegation", "Delegation_Log"),
    (r"irb|ethics.?approv|institutional.?review", "IRB_Approval"),
    (r"monitoring.?visit|visit.?report|mvr", "Monitoring_Visit_Report"),
    (r"sae.?follow|serious.?adverse", "SAE_Follow_Up"),
    (r"cv|curriculum.?vitae|investigator.?cv", "Investigator_CV"),
    (r"protocol", "Protocol"),
    (r"deviation", "Deviation_Log"),
    (r"consent|icf|informed.?consent", "Informed_Consent"),
    (r"activation|site.?open", "Site_Activation"),
]

_TEXT_RULES: list[tuple[str, str]] = [
    (r"form fda 1572|statement of investigator|fda form 1572", "FDA_1572"),
    (r"delegation of authority|delegated responsibilities|task delegation", "Delegation_Log"),
    (r"irb approval|ethics committee approval|institutional review board", "IRB_Approval"),
    (r"monitoring visit report|site visit report|clinical monitoring", "Monitoring_Visit_Report"),
    (r"serious adverse event|sae follow.?up|adverse event follow", "SAE_Follow_Up"),
    (r"curriculum vitae|investigator qualification|principal investigator cv", "Investigator_CV"),
    (r"study protocol|clinical trial protocol|protocol amendment|protocol version", "Protocol"),
    (r"protocol deviation|deviation log|deviation report|non-compliance", "Deviation_Log"),
    (r"informed consent|consent form|patient consent", "Informed_Consent"),
    (r"site activation|site initiation|site open", "Site_Activation"),
]


def classify_artifact(filename: str, text: str = "") -> str:
    """Return best-match artifact type for given filename and text excerpt."""
    name_lower = filename.lower()
    text_lower = text.lower()[:2000]  # only inspect first 2000 chars

    scores: dict[str, int] = {}

    for pattern, artifact_type in _FILENAME_RULES:
        if re.search(pattern, name_lower):
            scores[artifact_type] = scores.get(artifact_type, 0) + 2

    for pattern, artifact_type in _TEXT_RULES:
        if re.search(pattern, text_lower):
            scores[artifact_type] = scores.get(artifact_type, 0) + 3

    if not scores:
        return "Other"

    return max(scores, key=lambda k: scores[k])
