import pytest
from app.services.language import detect_language
from app.services.llm_provider import _fallback_templates
from app.models.response import EvidenceVerdictEnum, CaseTypeEnum
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_detect_language():
    # Pure Bangla
    assert detect_language("আমি টাকা পাঠাতে পারছি না") == "bn"
    
    # Pure English
    assert detect_language("I can't send money, it failed") == "en"
    
    # Mixed (Bangla Unicode + Latin chars)
    # Bangla chars: আমি (3), করেছি (3). Latin: transfer (8). Total = 14. Bangla = 6. Ratio = 0.428 (between 0.2 and 0.6)
    assert detect_language("আমি transfer করেছি") == "mixed"
    
    # No alphabet characters (default to English)
    assert detect_language("12345 !!!") == "en"
    
    # Empty string
    assert detect_language("") == "en"

def test_fallback_templates_all_cases():
    # Test all 8 case types for en and bn in fallback templates
    verdict = EvidenceVerdictEnum.consistent
    
    for case_type in CaseTypeEnum:
        # Test English templates
        res_en = _fallback_templates(
            complaint="test",
            matched_txn_id="TXN-123",
            verdict=verdict,
            case_type=case_type,
            language="en"
        )
        assert "agent_summary" in res_en
        assert "recommended_next_action" in res_en
        assert "customer_reply" in res_en
        assert "PIN" in res_en["customer_reply"] or "OTP" in res_en["customer_reply"] or case_type == CaseTypeEnum.merchant_settlement_delay
        
        # Test Bangla templates
        res_bn = _fallback_templates(
            complaint="পরীক্ষা",
            matched_txn_id="TXN-123",
            verdict=verdict,
            case_type=case_type,
            language="bn"
        )
        assert "agent_summary" in res_bn
        assert "recommended_next_action" in res_bn
        assert "customer_reply" in res_bn
        # Check that customer reply contains Bangla letters (using Unicode range check)
        assert any('\u0980' <= c <= '\u09FF' for c in res_bn["customer_reply"])

def test_integration_auto_detect_bangla():
    # Call analyze-ticket without language field, with a Bangla complaint
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "TKT-P5-001",
            "complaint": "আমি ভুল নাম্বারে ৫০০০ টাকা পাঠিয়েছি, দয়া করে ফেরত দিন",
            "user_type": "customer",
            "transaction_history": []
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ticket_id"] == "TKT-P5-001"
    assert data["case_type"] == "wrong_transfer"
    assert data["evidence_verdict"] == "insufficient_data"
    # Even if LLM fails and falls back to template, it should be in Bangla since language is detected as bn
    assert len(data["customer_reply"]) > 0
    # Customer reply should have the OTP/PIN safety warning (English fallback adds it, Bangla fallback template already has it)
    assert any(w in data["customer_reply"].lower() or w in data["customer_reply"] for w in ["pin", "otp", "পিন", "ওটিপি"])

def test_integration_auto_detect_mixed():
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "TKT-P5-002",
            "complaint": "আমার payment failed হয়েছে and balance কেটে নিয়েছে",
            "user_type": "customer",
            "transaction_history": []
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ticket_id"] == "TKT-P5-002"
    assert data["case_type"] == "payment_failed"
    assert len(data["customer_reply"]) > 0
