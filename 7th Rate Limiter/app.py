# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse
from rate_limiter import RateLimiter


app = FastAPI(
    title="Rate Limiter API",
    description="API with rate limiting middleware. Limits requests per IP address within a configurable time window.",
    version="1.0.0"
)

# ---- Configure Rate Limiter ----
# 10 requests per 60 seconds (easy to test)
limiter = RateLimiter(max_requests=10, window_seconds=60)


# ---- Rate Limiting Middleware ----

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Intercepts every request and checks rate limits by IP"""
    # Get client IP
    ip = request.client.host

    # Check if allowed
    result = limiter.is_allowed(ip)

    if not result["allowed"]:
        # 429 Too Many Requests
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."}
        )
    else:
        # Process the request normally
        response = await call_next(request)

    # Add rate limit headers to EVERY response
    response.headers["X-RateLimit-Limit"] = str(result["limit"])
    response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
    response.headers["X-RateLimit-Reset"] = str(result["reset"])

    return response


# ---- Example Routes ----

@app.get("/")
def home():
    return {"message": "Welcome! This API is rate limited."}


@app.get("/data")
def get_data():
    return {"data": [1, 2, 3, 4, 5], "status": "success"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/limit-info")
def limit_info():
    """Show current rate limiter configuration"""
    return {
        "max_requests": limiter.max_requests,
        "window_seconds": limiter.window_seconds,
        "tracked_clients": len(limiter.clients),
    }
