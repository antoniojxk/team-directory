import pytest
from fastapi.testclient import TestClient

PERSON = {"name": "Taylor Fox", "work_email": "TAYLOR@example.com", "department": "Engineering"}
EMPLOYMENT = {
    "job_title": "API Developer",
    "start_date": "2026-01-01",
    "end_date": None,
    "classification_id": 1,
    "status": "active",
}
TRAINING = {"requirement": "Workplace safety", "status": "pending"}


def test_directory_search_filters_and_pagination(
    client: TestClient, headers: dict[str, dict[str, str]]
) -> None:
    h = headers["viewer"]
    response = client.get("/api/people?q=AVERY", headers=h)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == 1
    assert client.get("/api/people?department=Engineering", headers=h).json()["total"] == 2
    assert (
        client.get("/api/people?status=on_leave&classification_id=2", headers=h).json()["total"]
        == 1
    )
    # Both employment filters must match the SAME employment, not two historical records.
    assert (
        client.get("/api/people?status=active&classification_id=2", headers=h).json()["total"] == 0
    )
    first = client.get("/api/people?page_size=2", headers=h).json()
    second = client.get("/api/people?page_size=2&page=2", headers=h).json()
    assert first["total"] == second["total"] == 3
    assert len(first["items"]) == 2 and len(second["items"]) == 1
    assert {p["id"] for p in first["items"]}.isdisjoint(p["id"] for p in second["items"])
    assert client.get("/api/people?q=%25", headers=h).json()["total"] == 0
    assert client.get("/api/people?page=100", headers=h).json()["items"] == []
    assert client.get("/api/departments", headers=h).json() == ["Design", "Engineering"]


def test_create_update_profile_and_related_crud(
    client: TestClient, headers: dict[str, dict[str, str]]
) -> None:
    h = headers["hr"]
    person = client.post("/api/people", headers=h, json={**PERSON, "private_notes": "secret"})
    assert person.status_code == 201
    assert person.json()["work_email"] == "taylor@example.com"
    assert "private_notes" not in person.json()
    base = f"/api/people/{person.json()['id']}"
    assert client.put(base, headers=h, json={**PERSON, "name": "Taylor Fox II"}).status_code == 200
    employment = client.post(
        base + "/employments", headers=h, json={**EMPLOYMENT, "salary": "81234.56"}
    )
    assert employment.status_code == 201
    assert "salary" not in employment.json()
    path = base + f"/employments/{employment.json()['id']}"
    assert client.put(path, headers=h, json={**EMPLOYMENT, "status": "on_leave"}).status_code == 200
    compliance = client.post(base + "/compliance", headers=h, json=TRAINING)
    assert compliance.status_code == 201
    training_path = base + f"/compliance/{compliance.json()['id']}"
    assert (
        client.put(
            training_path,
            headers=h,
            json={
                **TRAINING,
                "status": "completed",
                "completion_date": "2026-01-01",
                "expiry_date": "2027-01-01",
            },
        ).status_code
        == 200
    )
    profile = client.get(base, headers=headers["viewer"]).json()
    assert profile["name"] == "Taylor Fox II"
    assert profile["employments"][0]["status"] == "on_leave"
    assert profile["compliance_records"][0]["status"] == "completed"
    assert client.delete(training_path, headers=h).status_code == 204
    assert client.delete(path, headers=h).status_code == 204
    assert client.get(base, headers=h).json()["employments"] == []


def test_classification_crud_and_restrict_linked_delete(
    client: TestClient, headers: dict[str, dict[str, str]]
) -> None:
    h = headers["hr"]
    response = client.post("/api/classifications", headers=h, json={"name": " INTERN "})
    assert response.status_code == 201 and response.json()["name"] == "intern"
    path = f"/api/classifications/{response.json()['id']}"
    assert client.put(path, headers=h, json={"name": "apprentice"}).status_code == 200
    assert client.delete(path, headers=h).status_code == 204
    assert client.delete("/api/classifications/1", headers=h).status_code == 409
    assert (
        client.post("/api/classifications", headers=h, json={"name": "EMPLOYEE"}).status_code == 409
    )


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("post", "/api/people", PERSON),
        ("put", "/api/people/1", PERSON),
        ("post", "/api/classifications", {"name": "new"}),
        ("put", "/api/classifications/1", {"name": "new"}),
        ("delete", "/api/classifications/1", None),
        ("post", "/api/people/1/employments", {**EMPLOYMENT, "salary": "10"}),
        ("put", "/api/people/1/employments/1", EMPLOYMENT),
        ("delete", "/api/people/1/employments/1", None),
        ("post", "/api/people/1/compliance", TRAINING),
        ("put", "/api/people/1/compliance/1", TRAINING),
        ("delete", "/api/people/1/compliance/1", None),
        ("patch", "/api/people/1/confidential", {"private_notes": "changed"}),
        ("patch", "/api/people/1/employments/1/salary", {"salary": "1"}),
    ],
)
def test_viewer_cannot_mutate_directly(
    client: TestClient,
    headers: dict[str, dict[str, str]],
    method: str,
    path: str,
    body: dict[str, object] | None,
) -> None:
    response = client.request(method, path, headers=headers["viewer"], json=body)
    assert response.status_code == 403


@pytest.mark.parametrize(
    "path",
    [
        "/api/people?page=0",
        "/api/people?page_size=101",
        "/api/people?status=invalid",
        "/api/people?classification_id=-1",
        "/api/people/not-a-number",
        "/api/people/999999999999999",
    ],
)
def test_invalid_parameters(
    client: TestClient, headers: dict[str, dict[str, str]], path: str
) -> None:
    assert client.get(path, headers=headers["hr"]).status_code == 422


def test_missing_malformed_duplicate_and_mismatched_records(
    client: TestClient, headers: dict[str, dict[str, str]]
) -> None:
    h = headers["hr"]
    assert client.get("/api/people/999", headers=h).status_code == 404
    assert client.put("/api/people/999", headers=h, json=PERSON).status_code == 404
    assert client.post("/api/people/999/compliance", headers=h, json=TRAINING).status_code == 404
    assert client.put("/api/people/2/employments/1", headers=h, json=EMPLOYMENT).status_code == 404
    assert client.put("/api/people/2/compliance/1", headers=h, json=TRAINING).status_code == 404
    assert (
        client.post(
            "/api/people/1/employments",
            headers=h,
            json={**EMPLOYMENT, "classification_id": 999, "salary": "10"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/people", headers=h, json={**PERSON, "work_email": "AVERY@example.com"}
        ).status_code
        == 409
    )
    invalid = client.post(
        "/api/people",
        headers=h,
        json={
            **PERSON,
            "name": " ",
            "work_email": "PRIVATE_INVALID_EMAIL",
            "private_notes": "PRIVATE_SENTINEL",
        },
    )
    assert invalid.status_code == 422
    assert "PRIVATE_" not in invalid.text
    malformed = client.post(
        "/api/people",
        headers={**h, "Content-Type": "application/json"},
        content='{"private_notes": "PRIVATE_SENTINEL"',
    )
    assert malformed.status_code == 422 and "PRIVATE_SENTINEL" not in malformed.text


@pytest.mark.parametrize(
    "data",
    [
        {**EMPLOYMENT, "salary": "-1"},
        {**EMPLOYMENT, "salary": "1.001"},
        {**EMPLOYMENT, "salary": "NaN"},
        {**EMPLOYMENT, "salary": "100", "classification_id": 9223372036854775808},
        {**EMPLOYMENT, "salary": "100", "end_date": "2020-01-01"},
    ],
)
def test_employment_validation(
    client: TestClient, headers: dict[str, dict[str, str]], data: dict[str, object]
) -> None:
    assert (
        client.post("/api/people/1/employments", headers=headers["hr"], json=data).status_code
        == 422
    )


@pytest.mark.parametrize(
    "data",
    [
        {**TRAINING, "status": "completed"},
        {**TRAINING, "completion_date": "2026-01-01"},
        {**TRAINING, "expiry_date": "2026-01-01"},
        {
            **TRAINING,
            "status": "completed",
            "completion_date": "2026-01-01",
            "expiry_date": "2025-01-01",
        },
    ],
)
def test_compliance_validation(
    client: TestClient, headers: dict[str, dict[str, str]], data: dict[str, object]
) -> None:
    assert (
        client.post("/api/people/1/compliance", headers=headers["hr"], json=data).status_code == 422
    )


def test_health_openapi_and_unknown_routes(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    assert spec["paths"]["/api/people/{person_id}/confidential"]["get"]["security"] == [
        {"OAuth2PasswordBearer": ["confidential:read"]}
    ]
    for path in ["/api/typo", "/api", "/assets/missing.js", "/.env", "/docs/typo"]:
        response = client.get(path)
        assert response.status_code == 404
        assert response.headers["content-type"] == "application/json"
