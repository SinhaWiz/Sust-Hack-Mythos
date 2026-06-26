from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

from app.models.request import AnalyzeTicketRequest
from app.models.response import (
    AnalyzeTicketResponse, EvidenceVerdictEnum, CaseTypeEnum,
    SeverityEnum, DepartmentEnum
)

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
        # Handle whitespace-only complaints
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Complaint text cannot be empty", "ticket_id": request.ticket_id}
        )
        
    # Dummy response to verify schema and routing for Phase 1
    response = AnalyzeTicketResponse(
        ticket_id=request.ticket_id,
        relevant_transaction_id="TXN-DUMMY",
        evidence_verdict=EvidenceVerdictEnum.consistent,
        case_type=CaseTypeEnum.other,
        severity=SeverityEnum.low,
        department=DepartmentEnum.customer_support,
        agent_summary="Dummy summary for testing phase 1.",
        recommended_next_action="Review case.",
        customer_reply="We have noted your concern. Please do not share your PIN or OTP with anyone.",
        human_review_required=False,
    )
    return response
