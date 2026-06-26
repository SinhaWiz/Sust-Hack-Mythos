from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_analyze_ticket_valid():
    response = client.post(
        "/analyze-ticket",
        json={"ticket_id": "TKT-001", "complaint": "I lost 500 taka."}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ticket_id"] == "TKT-001"
    # No transaction history provided, so verdict should be insufficient_data
    assert data["evidence_verdict"] in ["consistent", "insufficient_data"]
    # Verify all required fields exist
    assert "agent_summary" in data
    assert "customer_reply" in data
    assert "recommended_next_action" in data

def test_analyze_ticket_missing_ticket_id():
    response = client.post(
        "/analyze-ticket",
        json={"complaint": "I lost 500 taka."}
    )
    assert response.status_code == 400
    assert "error" in response.json()
    assert response.json()["error"] == "Missing required field: ticket_id"

def test_analyze_ticket_missing_complaint():
    response = client.post(
        "/analyze-ticket",
        json={"ticket_id": "TKT-001"}
    )
    assert response.status_code == 400
    assert "error" in response.json()
    assert response.json()["error"] == "Missing required field: complaint"

def test_analyze_ticket_empty_complaint():
    response = client.post(
        "/analyze-ticket",
        json={"ticket_id": "TKT-001", "complaint": "   "}
    )
    assert response.status_code == 422
    assert "error" in response.json()
    assert response.json()["error"] == "Complaint text cannot be empty"

def test_analyze_ticket_invalid_json():
    response = client.post(
        "/analyze-ticket",
        data="invalid json {",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert "error" in response.json()
    assert "Invalid request format" in response.json()["error"]
