from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from app.models.request import AnalyzeTicketRequest
from app.models.response import AnalyzeTicketResponse
from app.services.analyzer import run_analysis_pipeline
from app.cache import get_cached_ticket, set_cached_ticket
from app.broker import TicketAnalysisRPCClient

logger = logging.getLogger("uvicorn.error")

rpc_client = TicketAnalysisRPCClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Establish connection to RabbitMQ RPC client on startup
    await rpc_client.connect()
    yield
    # Close connection on shutdown
    await rpc_client.close()

app = FastAPI(title="QueueStorm Investigator", lifespan=lifespan)

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

@app.post("/analyze-ticket")
async def analyze_ticket(request: AnalyzeTicketRequest):
    if not request.complaint.strip():
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Complaint text cannot be empty", "ticket_id": request.ticket_id}
        )
    
    try:
        # Step 1: Check Redis Cache
        try:
            cached_data = get_cached_ticket(request.ticket_id)
            if cached_data:
                return AnalyzeTicketResponse(**cached_data)
        except Exception as cache_err:
            logger.warning(f"Failed to query cache: {cache_err}")

        # Step 2: Attempt RabbitMQ RPC processing
        response_data = None
        import os
        if "PYTEST_CURRENT_TEST" not in os.environ and rpc_client.connection and not rpc_client.connection.is_closed:
            try:
                payload = request.model_dump(mode="json")
                response_data = await rpc_client.call(payload, timeout=12.0)
                logger.info(f"Processed ticket_id: {request.ticket_id} via RabbitMQ RPC.")
            except Exception as rpc_err:
                logger.warning(f"RabbitMQ RPC failed ({type(rpc_err).__name__}). Falling back to in-process pipeline.")
        
        if response_data is None:
            # Step 3: Fall back to in-process execution
            payload = request.model_dump(mode="json")
            response_data = run_analysis_pipeline(payload)

        # Step 4: Write to Redis Cache
        try:
            set_cached_ticket(request.ticket_id, response_data)
        except Exception as cache_err:
            logger.warning(f"Failed to update cache: {cache_err}")

        # Step 5: Format response
        if "error" in response_data:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": response_data["error"], "ticket_id": request.ticket_id}
            )

        return AnalyzeTicketResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal processing error", "ticket_id": request.ticket_id}
        )
