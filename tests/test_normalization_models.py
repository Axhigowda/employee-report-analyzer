from src.normalization.models import (
    Evidence,
    EvidenceType,
    EmployeeDataset,
)


def test_evidence_normalizes_claim():

    evidence = Evidence(
        employee="Binod",
        evidence_type=EvidenceType.METRIC,
        claim="  Saving:   22.72   Lakh ",
        source_file="test.xlsx",
    )

    assert evidence.normalized_claim() == (
        "saving: 22.72 lakh"
    )


def test_employee_dataset_rebuilds_evidence():

    dataset = EmployeeDataset(
        employee="Binod"
    )

    evidence = Evidence(
        employee="Binod",
        evidence_type=EvidenceType.METRIC,
        claim="Saving: 22.72 Lakh",
        source_file="test.xlsx",
    )

    from src.normalization.models import NormalizedDocument

    document = NormalizedDocument(
        employee="Binod",
        source_file="test.xlsx",
        source_type="xlsx",
        evidence=[evidence],
    )

    dataset.documents.append(document)

    dataset.rebuild_evidence()

    assert dataset.evidence_count == 1