from app.services.verification_service import detect_conflicts, remove_invalid_citations, verify_answer_evidence


def test_invalid_citations_are_removed() -> None:
    result = remove_invalid_citations("Supported [S1]. Invented [S99].", {"S1", "S2"})
    assert "[S1]" in result
    assert "[S99]" not in result


def test_detects_opposing_polarity_in_overlapping_claims() -> None:
    sources = [
        {"id": "S1", "passage": "The official study found the treatment improved recovery rates for adult patients."},
        {"id": "S2", "passage": "The official study found the treatment did not improve recovery rates for adult patients."},
    ]
    conflicts = detect_conflicts(sources)
    assert conflicts
    assert conflicts[0]["source_a"] == "S1"


def test_answer_verification_rejects_unknown_citations_and_limits_unsupported_claims() -> None:
    result = verify_answer_evidence("The documented result improved recovery for adults [S1]. This unrelated factual claim has no supporting citation.", [{"id": "S1", "passage": "The result improved recovery for adults."}])
    assert result.status == "supported"
    assert result.unsupported_claims == 1
    invalid = verify_answer_evidence("A fabricated source says otherwise [S99].", [{"id": "S1", "passage": "Evidence."}])
    assert invalid.invalid_sources == ("S99",)
    assert "[S99]" not in invalid.text


def test_answer_verification_reports_conflicting_evidence() -> None:
    sources = [{"id":"S1","passage":"The official study found treatment improved recovery rates for adult patients."},{"id":"S2","passage":"The official study found treatment did not improve recovery rates for adult patients."}]
    result = verify_answer_evidence("The studies disagree about improved recovery [S1] [S2].", sources)
    assert result.status == "conflicting_evidence"


def test_current_claim_without_date_or_authority_is_limited() -> None:
    result = verify_answer_evidence("The current release is available now [S1].", [{"id":"S1","passage":"The release is available."}], freshness_required=True)
    assert result.status == "limited_evidence"
