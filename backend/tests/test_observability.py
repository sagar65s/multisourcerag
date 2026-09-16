from app.core.observability import OperationalMetrics


def test_operational_metrics_are_bounded_and_content_free() -> None:
    metrics = OperationalMetrics()
    metrics.begin()
    metrics.finish("POST", "/api/v1/documents/{document_id}", 503, 125)
    snapshot = metrics.snapshot()
    assert snapshot["total_requests"] == 1
    assert snapshot["active_requests"] == 0
    assert snapshot["server_errors"] == 1
    assert snapshot["average_duration_ms"] == 125
    assert snapshot["routes"] == [{"method": "POST", "route": "/api/v1/documents/{document_id}", "requests": 1, "errors": 1, "average_duration_ms": 125}]
    forbidden = {"body", "query", "prompt", "content", "token", "user_id", "source_id"}
    assert forbidden.isdisjoint(snapshot)
    assert forbidden.isdisjoint(snapshot["routes"][0])


def test_operational_metrics_reject_unbounded_raw_paths() -> None:
    metrics = OperationalMetrics()
    metrics.begin()
    metrics.finish("TRACE", "private-source-id", 200, 5)
    route = metrics.snapshot()["routes"][0]
    assert route["method"] == "OTHER"
    assert route["route"] == "unmatched"
