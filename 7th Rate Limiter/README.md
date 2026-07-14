# Rate Limiter

A rate limiting middleware for FastAPI that limits API requests per time window. Tracks requests by IP address and returns proper rate limit headers.

## Features

- **Configurable limits**: set max requests and window duration
- **Per-IP tracking**: each IP gets its own counter
- **Rate limit headers**: X-RateLimit-Limit, Remaining, Reset on every response
- **Auto window reset**: counters reset when window expires
- **Memory cleanup**: remove expired entries to save memory
- **429 responses**: proper Too Many Requests error when exceeded

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pytest httpx
uvicorn app:app --reload
```

## How It Works

```
Request comes in
    │
    ▼
Middleware intercepts → Gets client IP
    │
    ▼
Rate limiter checks:
    ├─ Has window expired? → Reset counter
    ├─ Under limit? → Allow, increment count, add headers
    └─ Over limit? → Return 429 with headers
```

## Files

| File | Purpose |
|------|---------|
| `rate_limiter.py` | Core `RateLimiter` class — standalone, no FastAPI dependency |
| `app.py` | FastAPI app with middleware that uses `RateLimiter` |
| `test_app.py` | 22 tests covering core logic + middleware integration |

## Configuration

In `app.py`, adjust the limiter settings:
```python
limiter = RateLimiter(max_requests=10, window_seconds=60)
```

## Response Headers

Every response includes these headers:

| Header | Example | Description |
|--------|---------|-------------|
| `X-RateLimit-Limit` | `10` | Max requests allowed per window |
| `X-RateLimit-Remaining` | `7` | Requests remaining in current window |
| `X-RateLimit-Reset` | `1752498000` | Unix timestamp when window resets |

## API Routes

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Welcome message |
| GET | `/data` | Sample data endpoint |
| GET | `/health` | Health check |
| GET | `/limit-info` | Current rate limiter config |

## Example Usage

```bash
# Normal request (check headers)
curl -i http://localhost:8000/

# Response headers will show:
# X-RateLimit-Limit: 10
# X-RateLimit-Remaining: 9
# X-RateLimit-Reset: 1752498060

# Hit the limit (10 rapid requests)
for i in $(seq 1 11); do
  echo "Request $i:"
  curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8000/
done
# Request 11 → Status: 429
```

## Running Tests

```bash
pytest test_app.py -v
```

## Architecture

The rate limiter is split into two parts for clean separation:

1. **`RateLimiter` class** (pure Python, no framework dependency)
   - Can be reused with Flask, Django, or any other framework
   - Handles all the counting and window logic

2. **FastAPI middleware** (in `app.py`)
   - Thin wrapper that extracts IP and calls `RateLimiter`
   - Adds headers to responses
