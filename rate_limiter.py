import time
from collections import deque
from fastapi import HTTPException

# Store deque of timestamps per installation_id
_rate_limits = {}

def check_rate_limit(installation_id: int):
    if not installation_id:
        return
    now = time.time()
    window = 600 # 10 minutes
    limit = 10
    
    if installation_id not in _rate_limits:
        _rate_limits[installation_id] = deque()
        
    timestamps = _rate_limits[installation_id]
    
    # Prune timestamps older than the window before counting
    while timestamps and timestamps[0] < now - window:
        timestamps.popleft()
        
    if len(timestamps) >= limit:
        oldest = timestamps[0]
        # Retry-After must equal remaining seconds in the window for the oldest timestamp
        retry_after = int((oldest + window) - now)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": str(max(1, retry_after))}
        )
        
    timestamps.append(now)
