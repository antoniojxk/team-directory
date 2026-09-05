from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import AuditEvent


@pytest.mark.parametrize("role", ["viewer", "hr"])
def test_public_responses_never_include_confidential_fields(
    client: TestClient, headers: dict[str, dict[str, str]], role: str
) -> None:
    for path in ["/api/people", "/api/people/1", "/api/classifications"]:
        response = client.get(path, headers=headers[role])
        assert response.status_code == 200
        for secret in ["private_notes", "salary", "CONFIDENTIAL_NOTE_SENTINEL", "91234.56"]:
            assert secret not in response.text
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AuditEvent)) == 0


def test_success_and_denied_access_are_persisted_and_history_protected(
    client: TestClient, headers: dict[str, dict[str, str]]
) -> None:
    denied = client.get("/api/people/1/confidential", headers=headers["viewer"])
    assert denied.status_code == 403
    assert "CONFIDENTIAL_NOTE_SENTINEL" not in denied.text
    revealed = client.get("/api/people/1/confidential", headers=headers["hr"])
    assert revealed.status_code == 200
    assert revealed.json()["private_notes"] == "CONFIDENTIAL_NOTE_SENTINEL"
    assert revealed.json()["employments"][0]["salary"] == "91234.56"
    assert revealed.headers["cache-control"] == "no-store"
    # A different DB session proves persistence, rather than an uncommitted flush.
    with SessionLocal() as db:
        events = db.scalars(select(AuditEvent).order_by(AuditEvent.id)).all()
        assert [e.outcome for e in events] == ["denied", "success"]
        assert [e.actor_id for e in events] == [1, 2]
        assert all(e.target_person_id == 1 and e.timestamp.tzinfo for e in events)
    assert client.get("/api/audit").status_code == 401
    assert client.get("/api/audit", headers=headers["viewer"]).status_code == 403
    audit = client.get("/api/audit?page_size=1", headers=headers["hr"])
    assert audit.json()["total"] == 2
    assert len(audit.json()["items"]) == 1
    assert audit.json()["items"][0]["outcome"] == "success"
    assert "CONFIDENTIAL_NOTE_SENTINEL" not in audit.text and "91234.56" not in audit.text
    assert client.get("/api/audit?person_id=2", headers=headers["hr"]).json()["total"] == 0


def test_attempts_against_missing_people_are_audited(
    client: TestClient, headers: dict[str, dict[str, str]]
) -> None:
    assert client.get("/api/people/999/confidential", headers=headers["viewer"]).status_code == 403
    assert client.get("/api/people/999/confidential", headers=headers["hr"]).status_code == 404
    events = client.get("/api/audit", headers=headers["hr"]).json()["items"]
    assert [e["outcome"] for e in events] == ["not_found", "denied"]
    assert all(e["target_person_id"] is None and e["requested_person_id"] == 999 for e in events)


@pytest.mark.parametrize("role", ["hr", "viewer"])
def test_audit_failure_fails_closed(
    client: TestClient, headers: dict[str, dict[str, str]], role: str
) -> None:
    with patch("sqlalchemy.orm.Session.commit", side_effect=SQLAlchemyError("PRIVATE_DB_ERROR")):
        response = client.get("/api/people/1/confidential", headers=headers[role])
    assert response.status_code == 503
    for value in ["CONFIDENTIAL_NOTE_SENTINEL", "91234.56", "PRIVATE_DB_ERROR"]:
        assert value not in response.text
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AuditEvent)) == 0


def test_confidential_writes_return_no_values_and_public_edits_preserve_secrets(
    client: TestClient, headers: dict[str, dict[str, str]]
) -> None:
    h = headers["hr"]
    response = client.patch(
        "/api/people/1/confidential", headers=h, json={"private_notes": "UPDATED_PRIVATE_NOTE"}
    )
    assert response.status_code == 204 and not response.content
    assert (
        client.patch(
            "/api/people/1/employments/1/salary", headers=h, json={"salary": "95000.25"}
        ).status_code
        == 204
    )
    assert (
        client.put(
            "/api/people/1",
            headers=h,
            json={
                "name": "Avery Chen",
                "department": "Engineering",
                "work_email": "avery@example.com",
            },
        ).status_code
        == 200
    )
    response = client.get("/api/people/1/confidential", headers=h)
    assert response.json()["private_notes"] == "UPDATED_PRIVATE_NOTE"
    assert response.json()["employments"][0]["salary"] == "95000.25"
