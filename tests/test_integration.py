"""Integration tests for full end-to-end flow."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_end_to_end_wrong_transfer():
    """Test complete flow for wrong transfer case."""
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "TKT-E2E-001",
            "complaint": "I accidentally sent 5000 taka to wrong number +8801712345678",
            "language": "en",
            "user_type": "customer",
            "transaction_history": [
                {
                    "transaction_id": "TXN-999",
                    "timestamp": "2026-06-26T14:00:00Z",
                    "type": "transfer",
                    "amount": 5000.0,
                    "counterparty": "+8801712345678",
                    "status": "completed"
                }
            ]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required fields
    assert data["ticket_id"] == "TKT-E2E-001"
    assert data["relevant_transaction_id"] == "TXN-999"
    assert data["evidence_verdict"] == "consistent"
    assert data["case_type"] == "wrong_transfer"
    assert data["severity"] == "high"
    assert data["department"] == "dispute_resolution"
    assert data["human_review_required"] == True
    
    # Verify text fields exist and are safe
    assert len(data["agent_summary"]) > 0
    assert len(data["recommended_next_action"]) > 0
    assert len(data["customer_reply"]) > 0
    
    # Verify safety: customer reply should contain PIN/OTP warning
    assert "pin" in data["customer_reply"].lower() or "otp" in data["customer_reply"].lower()
    
    # Should NOT promise refunds
    assert "we will refund" not in data["customer_reply"].lower()
    assert "refund has been" not in data["customer_reply"].lower()

def test_end_to_end_phishing():
    """Test phishing detection and critical severity."""
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "TKT-E2E-002",
            "complaint": "Someone called me asking for my OTP and PIN",
            "language": "en",
            "user_type": "customer",
            "transaction_history": []
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["case_type"] == "phishing_or_social_engineering"
    assert data["severity"] == "critical"
    assert data["department"] == "fraud_risk"
    assert data["human_review_required"] == True
    assert data["evidence_verdict"] == "insufficient_data"
    
    # Safety warning should be strong
    assert "pin" in data["customer_reply"].lower() or "otp" in data["customer_reply"].lower()

def test_end_to_end_bangla():
    """Test Bangla language support."""
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "TKT-E2E-003",
            "complaint": "আমি ভুল নাম্বারে ১০০০ টাকা পাঠিয়েছি",
            "language": "bn",
            "user_type": "customer",
            "transaction_history": []
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["case_type"] == "wrong_transfer"
    assert data["evidence_verdict"] == "insufficient_data"
    # Should respond in Bangla or include safety message
    assert len(data["customer_reply"]) > 0
