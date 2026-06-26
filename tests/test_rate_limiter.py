import pytest
from app.services import rate_limiter
from app.services.rate_limiter import check_and_update_rate_limits

@pytest.fixture(autouse=True)
def mock_redis_offline(monkeypatch):
    # Guarantee that Redis connection is bypassed immediately without ping delays
    monkeypatch.setattr(rate_limiter, "get_redis_client", lambda: None)
    # Reset local histories
    rate_limiter._local_request_history.clear()
    rate_limiter._local_token_history.clear()

def test_sliding_window_rpm_limit(monkeypatch):
    # Temporarily set limit to 3 requests per minute for fast testing
    monkeypatch.setattr(rate_limiter, "LIMIT_RPM", 3)
    
    # Send 3 requests (should pass)
    assert check_and_update_rate_limits(estimated_tokens=10) is True
    assert check_and_update_rate_limits(estimated_tokens=10) is True
    assert check_and_update_rate_limits(estimated_tokens=10) is True
    
    # The 4th request must be rate limited (RPM limit reached)
    assert check_and_update_rate_limits(estimated_tokens=10) is False

def test_sliding_window_tpm_limit(monkeypatch):
    # Set limits: TPM = 100
    monkeypatch.setattr(rate_limiter, "LIMIT_TPM", 100)
    monkeypatch.setattr(rate_limiter, "LIMIT_RPM", 10)
    
    # Send 80 tokens (should pass)
    assert check_and_update_rate_limits(estimated_tokens=80) is True
    
    # Send another 30 tokens (should fail, total 110 > 100 limit)
    assert check_and_update_rate_limits(estimated_tokens=30) is False
    
    # Send another 20 tokens (should pass, total 100 <= 100 limit)
    assert check_and_update_rate_limits(estimated_tokens=20) is True

def test_sliding_window_rpd_limit(monkeypatch):
    # Set RPD = 2
    monkeypatch.setattr(rate_limiter, "LIMIT_RPD", 2)
    monkeypatch.setattr(rate_limiter, "LIMIT_RPM", 10)
    monkeypatch.setattr(rate_limiter, "LIMIT_TPM", 1000)
    
    # Send 2 requests (should pass)
    assert check_and_update_rate_limits(estimated_tokens=10) is True
    assert check_and_update_rate_limits(estimated_tokens=10) is True
    
    # The 3rd request should fail (RPD limit reached)
    assert check_and_update_rate_limits(estimated_tokens=10) is False

