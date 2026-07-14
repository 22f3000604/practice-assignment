import time


class RateLimiter:
    """
    Rate limiter that tracks requests per IP address within a time window.

    Args:
        max_requests: Maximum requests allowed per window (default: 100)
        window_seconds: Time window duration in seconds (default: 60)
    """

    def __init__(self, max_requests=100, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Storage: {ip: {"count": int, "window_start": float}}
        self.clients = {}

    def _get_client(self, ip):
        """Get or create a tracking entry for an IP address"""
        now = time.time()

        if ip not in self.clients:
            # First request from this IP
            self.clients[ip] = {
                "count": 0,
                "window_start": now,
            }

        client = self.clients[ip]

        # Check if the window has expired → reset
        if now - client["window_start"] >= self.window_seconds:
            client["count"] = 0
            client["window_start"] = now

        return client

    def is_allowed(self, ip):
        """
        Check if a request from this IP is allowed.

        Returns:
            dict with keys:
                - allowed (bool): whether the request is permitted
                - limit (int): max requests per window
                - remaining (int): requests remaining in current window
                - reset (int): unix timestamp when window resets
        """
        client = self._get_client(ip)
        reset_time = int(client["window_start"] + self.window_seconds)
        remaining = max(0, self.max_requests - client["count"])

        if client["count"] >= self.max_requests:
            return {
                "allowed": False,
                "limit": self.max_requests,
                "remaining": 0,
                "reset": reset_time,
            }

        # Increment count
        client["count"] += 1
        remaining = max(0, self.max_requests - client["count"])

        return {
            "allowed": True,
            "limit": self.max_requests,
            "remaining": remaining,
            "reset": reset_time,
        }

    def cleanup(self):
        """Remove expired entries to free memory"""
        now = time.time()
        expired_ips = [
            ip for ip, data in self.clients.items()
            if now - data["window_start"] >= self.window_seconds
        ]
        for ip in expired_ips:
            del self.clients[ip]
