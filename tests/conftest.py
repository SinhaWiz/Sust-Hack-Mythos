import pytest
from redis import Redis
import aio_pika

@pytest.fixture(autouse=True)
def mock_network_dependencies_offline(monkeypatch):
    """Globally mock Redis.ping and aio_pika.connect_robust to fail instantly,
    preventing socket connect timeouts and DNS lookup delays during pytest execution.
    """
    def mock_redis_ping(*args, **kwargs):
        raise ConnectionError("Mocked Redis connection failure for testing")
        
    async def mock_pika_connect(*args, **kwargs):
        raise ConnectionError("Mocked RabbitMQ connection failure for testing")
        
    monkeypatch.setattr(Redis, "ping", mock_redis_ping)
    monkeypatch.setattr(aio_pika, "connect_robust", mock_pika_connect)
