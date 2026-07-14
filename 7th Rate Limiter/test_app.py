import time
import pytest
from rate_limiter import RateLimiter

# ============================================================
# Tests for RateLimiter core logic
# ============================================================

class TestRateLimiterBasic:

    def test_first_request_allowed(self):
        """First request should always be allowed"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        result = limiter.is_allowed("192.168.1.1")
        assert result["allowed"] is True

    def test_remaining_decreases(self):
        """Remaining count should decrease with each request"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        r1 = limiter.is_allowed("192.168.1.1")
        assert r1["remaining"] == 4
        r2 = limiter.is_allowed("192.168.1.1")
        assert r2["remaining"] == 3

    def test_limit_reached(self):
        """Should block after max_requests"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        limiter.is_allowed("192.168.1.1")  # 1
        limiter.is_allowed("192.168.1.1")  # 2
        limiter.is_allowed("192.168.1.1")  # 3
        result = limiter.is_allowed("192.168.1.1")  # 4 → blocked
        assert result["allowed"] is False
        assert result["remaining"] == 0

    def test_different_ips_tracked_separately(self):
        """Each IP should have its own counter"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("10.0.0.1")
        limiter.is_allowed("10.0.0.1")
        # IP 1 is now at limit
        result_ip1 = limiter.is_allowed("10.0.0.1")
        assert result_ip1["allowed"] is False

        # IP 2 should still be allowed
        result_ip2 = limiter.is_allowed("10.0.0.2")
        assert result_ip2["allowed"] is True

    def test_limit_header_value(self):
        """Limit value should match max_requests"""
        limiter = RateLimiter(max_requests=50, window_seconds=60)
        result = limiter.is_allowed("192.168.1.1")
        assert result["limit"] == 50


# ============================================================
# Tests for window reset
# ============================================================

class TestWindowReset:

    def test_window_resets_after_expiry(self):
        """Counter should reset after window expires"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        limiter.is_allowed("192.168.1.1")
        limiter.is_allowed("192.168.1.1")
        # Now at limit
        result = limiter.is_allowed("192.168.1.1")
        assert result["allowed"] is False

        # Wait for window to expire
        time.sleep(1.1)
        result = limiter.is_allowed("192.168.1.1")
        assert result["allowed"] is True
        assert result["remaining"] == 1

    def test_reset_timestamp_is_correct(self):
        """Reset timestamp should be window_start + window_seconds"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        result = limiter.is_allowed("192.168.1.1")
        now = int(time.time())
        # Reset should be approximately now + 60
        assert result["reset"] >= now + 59
        assert result["reset"] <= now + 61

    def test_count_resets_to_zero_after_window(self):
        """After window expires, count should be back to 0"""
        limiter = RateLimiter(max_requests=5, window_seconds=1)
        for _ in range(5):
            limiter.is_allowed("192.168.1.1")

        time.sleep(1.1)
        client = limiter._get_client("192.168.1.1")
        assert client["count"] == 0


# ============================================================
# Tests for memory management
# ============================================================

class TestMemoryManagement:

    def test_cleanup_removes_expired(self):
        """Cleanup should remove expired client entries"""
        limiter = RateLimiter(max_requests=10, window_seconds=1)
        limiter.is_allowed("192.168.1.1")
        limiter.is_allowed("192.168.1.2")
        assert len(limiter.clients) == 2

        time.sleep(1.1)
        limiter.cleanup()
        assert len(limiter.clients) == 0

    def test_cleanup_keeps_active(self):
        """Cleanup should keep clients with active windows"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        limiter.is_allowed("192.168.1.1")
        limiter.cleanup()
        assert len(limiter.clients) == 1

    def test_new_ip_creates_entry(self):
        """New IP should create a tracking entry"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        assert len(limiter.clients) == 0
        limiter.is_allowed("10.0.0.1")
        assert "10.0.0.1" in limiter.clients


# ============================================================
# Tests for edge cases
# ============================================================

class TestEdgeCases:

    def test_max_requests_one(self):
        """Should work with max_requests=1"""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        r1 = limiter.is_allowed("192.168.1.1")
        assert r1["allowed"] is True
        assert r1["remaining"] == 0
        r2 = limiter.is_allowed("192.168.1.1")
        assert r2["allowed"] is False

    def test_remaining_never_negative(self):
        """Remaining should never go below 0"""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        limiter.is_allowed("192.168.1.1")
        result = limiter.is_allowed("192.168.1.1")
        assert result["remaining"] == 0

    def test_many_ips(self):
        """Should handle many different IPs"""
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        for i in range(50):
            result = limiter.is_allowed(f"10.0.0.{i}")
            assert result["allowed"] is True
        assert len(limiter.clients) == 50

    def test_blocked_stays_blocked(self):
        """Once blocked, subsequent requests stay blocked"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("192.168.1.1")
        limiter.is_allowed("192.168.1.1")
        # All further requests should be blocked
        for _ in range(5):
            result = limiter.is_allowed("192.168.1.1")
            assert result["allowed"] is False


# ============================================================
# Tests for FastAPI middleware integration
# ============================================================

class TestMiddlewareIntegration:

    @pytest.fixture
    def client(self):
        """Create a fresh test client with a new rate limiter"""
        from app import app, limiter
        # pyrefly: ignore [missing-import]
        from fastapi.testclient import TestClient
        # Reset limiter for each test
        limiter.clients.clear()
        limiter.max_requests = 5
        limiter.window_seconds = 60
        return TestClient(app)

    def test_headers_present(self, client):
        """Rate limit headers should be on every response"""
        response = client.get("/")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_headers_values_correct(self, client):
        """Header values should reflect current state"""
        response = client.get("/")
        assert response.headers["X-RateLimit-Limit"] == "5"
        assert response.headers["X-RateLimit-Remaining"] == "4"

    def test_429_when_exceeded(self, client):
        """Should return 429 when rate limit is exceeded"""
        for _ in range(5):
            client.get("/")
        response = client.get("/")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]

    def test_429_still_has_headers(self, client):
        """429 response should still include rate limit headers"""
        for _ in range(5):
            client.get("/")
        response = client.get("/")
        assert response.status_code == 429
        assert response.headers["X-RateLimit-Remaining"] == "0"

    def test_different_routes_share_limit(self, client):
        """Rate limit applies across all routes for same IP"""
        client.get("/")
        client.get("/data")
        client.get("/health")
        response = client.get("/")
        assert response.headers["X-RateLimit-Remaining"] == "1"
