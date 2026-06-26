from typing import Dict, Any, Optional
from app.models.request import AnalyzeTicketRequest
from app.models.response import AnalyzeTicketResponse
from app.services.evidence_engine import ComplaintSignals, match_transaction, determine_verdict
from app.services.classifier import classify_case_type, determine_severity, determine_department, determine_human_review_required
from app.services.llm_provider import generate_texts
from app.services.safety_guardrails import sanitize_complaint, apply_safety_guardrails
from app.services.language import detect_language

def run_analysis_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the core ticket analysis pipeline synchronously."""
    # Step 1: Parse request data into Pydantic model
    request = AnalyzeTicketRequest(**payload)
    
    if not request.complaint.strip():
        raise ValueError("Complaint text cannot be empty")
        
    # Step 2: Extract complaint signals
    signals = ComplaintSignals(
        request.complaint,
        user_type=request.user_type.value if request.user_type else None
    )
    
    # Step 3: Match transaction
    matched_txn_id, confidence = match_transaction(signals, request.transaction_history)
    
    # Step 4: Determine evidence verdict
    verdict = determine_verdict(signals, matched_txn_id, request.transaction_history)
    
    # Step 5: Classify case
    case_type = classify_case_type(signals, verdict)
    severity = determine_severity(case_type, verdict, signals)
    department = determine_department(case_type, request.user_type)
    human_review = determine_human_review_required(case_type, verdict, severity)
    
    # Step 6: Generate texts using LLM
    sanitized_comp = sanitize_complaint(request.complaint)
    detected_lang = request.language.value if request.language else detect_language(request.complaint)
    
    texts = generate_texts(
        sanitized_comp,
        matched_txn_id,
        verdict,
        case_type,
        language=detected_lang,
        user_type=request.user_type.value if request.user_type else "customer",
        transaction_history=request.transaction_history
    )
    
    # Step 7: Apply safety guardrails
    safe_texts = apply_safety_guardrails(
        texts,
        user_type=request.user_type.value if request.user_type else "customer"
    )
    
    # Step 8: Build and serialize response
    response = AnalyzeTicketResponse(
        ticket_id=request.ticket_id,
        relevant_transaction_id=matched_txn_id,
        evidence_verdict=verdict,
        case_type=case_type,
        severity=severity,
        department=department,
        agent_summary=safe_texts["agent_summary"],
        recommended_next_action=safe_texts["recommended_next_action"],
        customer_reply=safe_texts["customer_reply"],
        human_review_required=human_review,
        confidence=confidence if confidence > 0 else None
    )
    
    return response.model_dump()
