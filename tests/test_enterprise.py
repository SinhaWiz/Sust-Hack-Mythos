# pyrefly: ignore [missing-import]
import pytest
from app.services.analyzer import run_analysis_pipeline
from app.cache import get_redis_client, get_cached_ticket, set_cached_ticket
from app.broker import TicketAnalysisRPCClient
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_run_analysis_pipeline_direct():
    # Test that running the pipeline directly works
    payload = {
        "ticket_id": "TKT-ENT-001",
        "complaint": "I accidentally transferred 5000 taka to wrong number",
        "user_type": "customer",
        "transaction_history": []
    }
    res = run_analysis_pipeline(payload)
    assert res["ticket_id"] == "TKT-ENT-001"
    assert res["case_type"] == "wrong_transfer"
    assert res["evidence_verdict"] == "insufficient_data"
    assert "PIN" in res["customer_reply"] or "OTP" in res["customer_reply"]

def test_redis_graceful_failure_when_down(monkeypatch):
    # Mock redis client connection failure by patching ping to raise ConnectionError
    from redis import Redis
    def mock_ping(*args, **kwargs):
        raise ConnectionError("Connection refused")
    monkeypatch.setattr(Redis, "ping", mock_ping)
    
    # Verify client connection returns None
    from app import cache
    cache._redis_client = None  # Reset client
    client_res = get_redis_client()
    assert client_res is None
    
    # Verify get/set return None and do not throw exception
    assert get_cached_ticket("test") is None
    set_cached_ticket("test", {"result": "ok"})
    cache._redis_client = None  # Clean up

def test_broker_graceful_failure_when_down(monkeypatch):
    # Mock RabbitMQ connection failure by patching connect_robust
    import aio_pika
    async def mock_connect(*args, **kwargs):
        raise ConnectionError("Connection refused")
    monkeypatch.setattr(aio_pika, "connect_robust", mock_connect)
    
    rpc = TicketAnalysisRPCClient()
    # verify connect fails gracefully
    async def run_connect():
        await rpc.connect()
        assert rpc.connection is None
    import asyncio
    asyncio.run(run_connect())

def test_end_to_end_gateway_fallback():
    # Test that the gateway endpoint works even when RabbitMQ and Redis are down
    # By default, since they are down locally (or if we run this outside docker compose),
    # the endpoint should transparently fall back to in-process execution and return HTTP 200.
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "TKT-ENT-002",
            "complaint": "Someone called me asking for my OTP",
            "user_type": "customer",
            "transaction_history": []
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ticket_id"] == "TKT-ENT-002"
    assert data["case_type"] == "phishing_or_social_engineering"
    assert data["severity"] == "critical"
