import time
import os
import threading
import logging
from typing import Optional, List, Tuple
from app.cache import get_redis_client

logger = logging.getLogger("uvicorn.error")

# Configurable limits
LIMIT_RPM = int(os.getenv("GEMINI_LIMIT_RPM", 13))
LIMIT_RPD = int(os.getenv("GEMINI_LIMIT_RPD", 450))
LIMIT_TPM = int(os.getenv("GEMINI_LIMIT_TPM", 249000))

# In-memory histories (used if Redis is offline)
_local_request_history: List[float] = [] # timestamps for RPM/RPD
_local_token_history: List[Tuple[float, int]] = [] # (timestamp, tokens) for TPM
_lock = threading.Lock()

def check_and_update_rate_limits(estimated_tokens: int) -> bool:
    """Check if the estimated request/token count exceeds limits.
    
    If allowed, registers the request and returns True. Otherwise returns False.
    Uses Redis sliding windows if available; falls back to in-memory sliding windows.
    """
    now = time.time()
    client = get_redis_client()
    
    if client:
        try:
            # We use Redis transactions/pipelines to ensure atomic operations
            pipe = client.pipeline()
            
            # Keys
            rpm_key = "ratelimit:gemini:rpm"
            rpd_key = "ratelimit:gemini:rpd"
            tpm_key = "ratelimit:gemini:tpm"
            
            # Prune old entries
            pipe.zremrangebyscore(rpm_key, "-inf", now - 60)
            pipe.zremrangebyscore(rpd_key, "-inf", now - 86400)
            pipe.zremrangebyscore(tpm_key, "-inf", now - 60)
            
            # Get current counts
            pipe.zcard(rpm_key)
            pipe.zcard(rpd_key)
            pipe.zrangebyscore(tpm_key, now - 60, "+inf", withscores=True)
            
            # Execute pruning and query
            res = pipe.execute()
            
            current_rpm = res[3]
            current_rpd = res[4]
            tpm_entries = res[5] # list of tuples: (member_str, score)
            
            # Sum up current tokens
            current_tpm = 0
            for val_str, _ in tpm_entries:
                try:
                    # format is "timestamp:tokens"
                    _, tokens = val_str.split(":", 1)
                    current_tpm += int(tokens)
                except ValueError:
                    pass
            
            # Verify if limits are exceeded
            if current_rpm >= LIMIT_RPM:
                logger.warning(f"Pre-emptive rate limit hit: RPM limit ({LIMIT_RPM}) reached. Current: {current_rpm}")
                return False
                
            if current_rpd >= LIMIT_RPD:
                logger.warning(f"Pre-emptive rate limit hit: RPD limit ({LIMIT_RPD}) reached. Current: {current_rpd}")
                return False
                
            if current_tpm + estimated_tokens > LIMIT_TPM:
                logger.warning(f"Pre-emptive rate limit hit: TPM limit ({LIMIT_TPM}) reached. Current: {current_tpm}, Est: {estimated_tokens}")
                return False
                
            # Update history in Redis
            pipe = client.pipeline()
            pipe.zadd(rpm_key, {str(now): now})
            pipe.zadd(rpd_key, {str(now): now})
            # To make ZSET values unique, we include the timestamp and a unique suffix
            unique_member = f"{now}:{estimated_tokens}:{os.urandom(4).hex()}"
            pipe.zadd(tpm_key, {unique_member: now})
            
            # Set TTLs so keys clean up eventually
            pipe.expire(rpm_key, 120)
            pipe.expire(rpd_key, 90000)
            pipe.expire(tpm_key, 120)
            
            pipe.execute()
            return True
            
        except Exception as e:
            logger.warning(f"Error checking rate limits via Redis: {e}. Falling back to in-memory check.")
            # Failover to local in-memory rate limiter

    # Local in-memory sliding window rate limiter
    with _lock:
        # Prune old timestamps
        global _local_request_history, _local_token_history
        _local_request_history = [t for t in _local_request_history if t > now - 86400]
        _local_token_history = [item for item in _local_token_history if item[0] > now - 60]
        
        # Calculate counts
        rpm_count = sum(1 for t in _local_request_history if t > now - 60)
        rpd_count = len(_local_request_history)
        tpm_count = sum(tokens for t, tokens in _local_token_history)
        
        # Verify if limits are exceeded
        if rpm_count >= LIMIT_RPM:
            logger.warning(f"Local pre-emptive rate limit hit: RPM limit ({LIMIT_RPM}) reached. Current: {rpm_count}")
            return False
            
        if rpd_count >= LIMIT_RPD:
            logger.warning(f"Local pre-emptive rate limit hit: RPD limit ({LIMIT_RPD}) reached. Current: {rpd_count}")
            return False
            
        if tpm_count + estimated_tokens > LIMIT_TPM:
            logger.warning(f"Local pre-emptive rate limit hit: TPM limit ({LIMIT_TPM}) reached. Current: {tpm_count}, Est: {estimated_tokens}")
            return False
            
        # Log successful request
        _local_request_history.append(now)
        _local_token_history.append((now, estimated_tokens))
        return True
