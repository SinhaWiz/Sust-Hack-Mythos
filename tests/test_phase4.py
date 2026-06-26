import pytest
from unittest.mock import patch, MagicMock
from app.services.llm_provider import generate_texts
from app.models.response import EvidenceVerdictEnum, CaseTypeEnum

def test_generate_texts_no_api_key():
    """Verify fallback templates are used when GEMINI_API_KEY is not set."""
    with patch("app.services.llm_provider.GEMINI_API_KEY", ""):
        res = generate_texts(
            complaint="Help me",
            matched_txn_id="TXN-123",
            verdict=EvidenceVerdictEnum.consistent,
            case_type=CaseTypeEnum.wrong_transfer,
            language="en"
        )
        assert res["agent_summary"] is not None
        assert res["recommended_next_action"] is not None
        assert res["customer_reply"] is not None
        assert "dispute team" in res["customer_reply"]

@patch("google.generativeai.GenerativeModel")
def test_generate_texts_success_flow(mock_model_class):
    """Test successful Gemini integration flow and JSON parsing."""
    # Setup mock response
    mock_model = MagicMock()
    mock_model_class.return_value = mock_model
    
    mock_response = MagicMock()
    mock_response.text = '{"agent_summary": "Summary text", "recommended_next_action": "Action text", "customer_reply": "Reply text"}'
    mock_model.generate_content.return_value = mock_response
    
    with patch("app.services.llm_provider.GEMINI_API_KEY", "dummy_key"):
        res = generate_texts(
            complaint="Help me",
            matched_txn_id="TXN-123",
            verdict=EvidenceVerdictEnum.consistent,
            case_type=CaseTypeEnum.wrong_transfer,
            language="en",
            user_type="customer",
            transaction_history=[]
        )
        
        # Verify result format
        assert res["agent_summary"] == "Summary text"
        assert res["recommended_next_action"] == "Action text"
        assert res["customer_reply"] == "Reply text"
        
        # Verify model was created with correct name
        mock_model_class.assert_called_once()
        name_called = mock_model_class.call_args[1].get("model_name") or mock_model_class.call_args[0][0]
        assert name_called == 'gemini-3.1-flash-lite'

@patch("google.generativeai.GenerativeModel")
def test_generate_texts_invalid_json_fallback(mock_model_class):
    """Test fallback when LLM response is not valid JSON."""
    mock_model = MagicMock()
    mock_model_class.return_value = mock_model
    
    mock_response = MagicMock()
    mock_response.text = "invalid json text"
    mock_model.generate_content.return_value = mock_response
    
    with patch("app.services.llm_provider.GEMINI_API_KEY", "dummy_key"):
        res = generate_texts(
            complaint="Help me",
            matched_txn_id="TXN-123",
            verdict=EvidenceVerdictEnum.consistent,
            case_type=CaseTypeEnum.wrong_transfer,
            language="en"
        )
        # Should fallback safely
        assert "dispute team" in res["customer_reply"]

@patch("google.generativeai.GenerativeModel")
def test_generate_texts_missing_fields_fallback(mock_model_class):
    """Test fallback when LLM response is missing required fields."""
    mock_model = MagicMock()
    mock_model_class.return_value = mock_model
    
    mock_response = MagicMock()
    # Missing customer_reply
    mock_response.text = '{"agent_summary": "Summary", "recommended_next_action": "Action"}'
    mock_model.generate_content.return_value = mock_response
    
    with patch("app.services.llm_provider.GEMINI_API_KEY", "dummy_key"):
        res = generate_texts(
            complaint="Help me",
            matched_txn_id="TXN-123",
            verdict=EvidenceVerdictEnum.consistent,
            case_type=CaseTypeEnum.wrong_transfer,
            language="en"
        )
        # Should fallback safely
        assert "dispute team" in res["customer_reply"]
