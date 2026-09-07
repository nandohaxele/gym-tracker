"""Pydantic 422 keeps the extra `details` key as an intentional exception."""

from tests.helpers import err


def test_request_validation_error_includes_details(client):
    resp = client.post("/api/auth/register", json={"email": "not-an-email", "password": "short"})
    body = err(resp, 422)
    assert set(body) >= {"success", "data", "error", "details"}
    assert isinstance(body["details"], list)
    assert body["details"]
