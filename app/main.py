from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

from app.models.request import AnalyzeTicketRequest
from app.models.response import AnalyzeTicketResponse
from app.services.evidence_engine import ComplaintSignals, match_transaction, determine_verdict
from app.services.classifier import classify_case_type, determine_severity, determine_department, determine_human_review_required
from app.services.llm_provider import generate_texts
from app.services.safety_guardrails import apply_safety_guardrails

app = FastAPI(title="QueueStorm Investigator")
logger = logging.getLogger("uvicorn.error")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    
    ticket_id = None
    try:
        body = await request.json()
        if isinstance(body, dict):
            ticket_id = body.get("ticket_id")
    except Exception:
        pass
        
    error_msg = "Invalid request format"
    status_code = status.HTTP_400_BAD_REQUEST

    for error in errors:
        loc = error.get("loc", [])
        msg = error.get("msg", "")
        if "ticket_id" in loc and error.get("type") == "missing":
            error_msg = "Missing required field: ticket_id"
            status_code = status.HTTP_400_BAD_REQUEST
            break
        elif "complaint" in loc and error.get("type") == "missing":
            error_msg = "Missing required field: complaint"
            status_code = status.HTTP_400_BAD_REQUEST
            break
        elif "complaint" in loc and (error.get("type") == "string_too_short" or error.get("type") == "value_error"):
            error_msg = "Complaint text cannot be empty"
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            break
        elif error.get("type") == "json_invalid":
            error_msg = "Invalid request format"
            status_code = status.HTTP_400_BAD_REQUEST
            break
        else:
            # Generic error
            error_msg = f"Validation error at {loc}: {msg}"
    
    return JSONResponse(
        status_code=status_code,
        content={"error": error_msg, "ticket_id": ticket_id}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    ticket_id = None
    try:
        body = await request.json()
        if isinstance(body, dict):
            ticket_id = body.get("ticket_id")
    except Exception:
        pass
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal processing error", "ticket_id": ticket_id}
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/analyze-ticket", response_model=AnalyzeTicketResponse)
async def analyze_ticket(request: AnalyzeTicketRequest):
    if not request.complaint.strip():
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Complaint text cannot be empty", "ticket_id": request.ticket_id}
        )
    
    try:
        # Step 1: Extract complaint signals
        signals = ComplaintSignals(
            request.complaint,
            user_type=request.user_type.value if request.user_type else None
        )
        
        # Step 2: Match transaction
        matched_txn_id, confidence = match_transaction(signals, request.transaction_history)
        
        # Step 3: Determine evidence verdict
        verdict = determine_verdict(signals, matched_txn_id, request.transaction_history)
        
        # Step 4: Classify case
        case_type = classify_case_type(signals, verdict)
        severity = determine_severity(case_type, verdict, signals)
        department = determine_department(case_type, request.user_type)
        human_review = determine_human_review_required(case_type, verdict, severity)
        
        # Step 5: Generate texts using LLM
        from app.services.safety_guardrails import sanitize_complaint
        sanitized_complaint = sanitize_complaint(request.complaint)
        texts = generate_texts(
            sanitized_complaint,
            matched_txn_id,
            verdict,
            case_type,
            language=request.language.value if request.language else "en"
        )
        
        # Step 6: Apply safety guardrails
        safe_texts = apply_safety_guardrails(
            texts,
            user_type=request.user_type.value if request.user_type else "customer"
        )
        
        # Step 7: Build response
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
        
        return response
        
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal processing error", "ticket_id": request.ticket_id}
        )
