import json
import os
# pyrefly: ignore [missing-import]
import pytest
from datetime import datetime
from app.models.request import AnalyzeTicketRequest, TransactionHistoryItem
from app.services.evidence_engine import ComplaintSignals, match_transaction, determine_verdict
from app.services.classifier import classify_case_type, determine_severity, determine_department, determine_human_review_required

def test_all_10_sample_cases():
    sample_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "start_doc", "SUST_Preli_Sample_Cases.json")
    with open(sample_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for case in data["cases"]:
        input_data = case["input"]
        expected = case["expected_output"]
        
        req = AnalyzeTicketRequest(**input_data)
        signals = ComplaintSignals(req.complaint, user_type=req.user_type.value if req.user_type else None)
        
        matched_id, score = match_transaction(signals, req.transaction_history)
        assert matched_id == expected["relevant_transaction_id"], f"Failed relevant_transaction_id for {case['id']}"
        
        verdict = determine_verdict(signals, matched_id, req.transaction_history)
        assert verdict.value == expected["evidence_verdict"], f"Failed evidence_verdict for {case['id']}"
        
        case_type = classify_case_type(signals, verdict)
        assert case_type.value == expected["case_type"], f"Failed case_type for {case['id']}"
        
        severity = determine_severity(case_type, verdict, signals)
        assert severity.value == expected["severity"], f"Failed severity for {case['id']}"
        
        dept = determine_department(case_type, req.user_type)
        assert dept.value == expected["department"], f"Failed department for {case['id']}"
        
        human_review = determine_human_review_required(case_type, verdict, severity)
        assert human_review == expected["human_review_required"], f"Failed human_review_required for {case['id']}"
