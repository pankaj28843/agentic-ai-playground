"""Tests for request-id middleware."""

from __future__ import annotations


def test_request_id_header_roundtrip(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "X-Request-Id" in response.headers

    response = client.get("/api/health", headers={"X-Request-Id": "req-123"})
    assert response.headers.get("X-Request-Id") == "req-123"
