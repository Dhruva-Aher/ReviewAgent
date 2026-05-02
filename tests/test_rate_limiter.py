import pytest
from fastapi import HTTPException
from unittest.mock import patch
from rate_limiter import check_rate_limit, _rate_limits

@pytest.fixture(autouse=True)
def reset_rate_limits():
    _rate_limits.clear()
    yield
    _rate_limits.clear()

def test_rate_limiter_first_10_allowed():
    for _ in range(10):
        check_rate_limit(1)

    assert len(_rate_limits[1]) == 10

def test_rate_limiter_11th_raises_429():
    for _ in range(10):
        check_rate_limit(1)

    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit(1)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers

def test_rate_limiter_window_expires():
    current_time = 1000

    with patch("time.time", return_value=current_time):
        for _ in range(10):
            check_rate_limit(1)

        with pytest.raises(HTTPException):
            check_rate_limit(1)

    # Advance time past window size (600s)
    current_time += 601

    with patch("time.time", return_value=current_time):
        check_rate_limit(1)
        assert len(_rate_limits[1]) == 1

def test_rate_limiter_isolation():
    for _ in range(10):
        check_rate_limit(1)

    # inst_2 should still be allowed
    check_rate_limit(2)
    assert len(_rate_limits[2]) == 1
