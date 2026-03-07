"""
Tests for app.services.artifact_classifier.

Pure unit tests — no database required.
"""
import pytest

from app.services.artifact_classifier import classify_artifact


class TestFilenameClassification:
    def test_fda_1572_by_filename(self):
        assert classify_artifact("fda_1572_site004.txt") == "FDA_1572"
        assert classify_artifact("form_1572.pdf") == "FDA_1572"

    def test_delegation_log_by_filename(self):
        assert classify_artifact("delegation_log_site004.txt") == "Delegation_Log"

    def test_irb_approval_by_filename(self):
        assert classify_artifact("irb_approval_site004.txt") == "IRB_Approval"

    def test_monitoring_visit_report_by_filename(self):
        assert classify_artifact("monitoring_report_site004.txt") == "Monitoring_Visit_Report"
        assert classify_artifact("mvr_site012.pdf") == "Monitoring_Visit_Report"

    def test_investigator_cv_by_filename(self):
        assert classify_artifact("investigator_cv_site021.txt") == "Investigator_CV"

    def test_protocol_by_filename(self):
        assert classify_artifact("protocol_abc001.txt") == "Protocol"

    def test_deviation_log_by_filename(self):
        assert classify_artifact("deviation_log_site012.txt") == "Deviation_Log"

    def test_site_activation_by_filename(self):
        assert classify_artifact("site_activation_report.txt") == "Site_Activation"

    def test_unknown_returns_other(self):
        assert classify_artifact("random_document_xyz.pdf") == "Other"


class TestTextClassification:
    def test_fda_1572_by_text(self):
        text = "This is Form FDA 1572, Statement of Investigator."
        assert classify_artifact("unknown.pdf", text) == "FDA_1572"

    def test_delegation_log_by_text(self):
        text = "Delegation of Authority Log — tasks delegated to sub-investigators."
        assert classify_artifact("doc.pdf", text) == "Delegation_Log"

    def test_protocol_by_text(self):
        text = "Study Protocol Version 2.1 — Clinical Trial Protocol for ABC-001."
        assert classify_artifact("study_doc.pdf", text) == "Protocol"

    def test_irb_by_text(self):
        text = "IRB Approval letter from the Institutional Review Board."
        assert classify_artifact("letter.pdf", text) == "IRB_Approval"

    def test_deviation_by_text(self):
        text = "Protocol Deviation Log — non-compliance events at site 012."
        assert classify_artifact("file.txt", text) == "Deviation_Log"

    def test_informed_consent_by_text(self):
        text = "Informed Consent Form — patient consent for study participation."
        assert classify_artifact("consent.pdf", text) == "Informed_Consent"


class TestFilenameAndTextCombined:
    def test_filename_match_plus_text_reinforces(self):
        # Both sources point to Protocol → should still be Protocol
        result = classify_artifact(
            "protocol_v2.txt",
            "This Study Protocol defines the clinical trial objectives."
        )
        assert result == "Protocol"

    def test_ambiguous_filename_resolved_by_text(self):
        # Filename is ambiguous; text clearly indicates IRB
        result = classify_artifact(
            "document.pdf",
            "IRB Approval granted by the ethics committee for this study."
        )
        assert result == "IRB_Approval"

    def test_filename_wins_with_no_text(self):
        result = classify_artifact("fda_1572_outdated.txt", "")
        assert result == "FDA_1572"
