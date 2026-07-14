# URL Shortener API

A URL shortening service built with FastAPI. Submit a long URL and receive a short code. Accessing the short code redirects to the original URL.

## Features

- Generate unique 6-character short codes
- Custom alias support
- Duplicate URL detection
- Click tracking
- URL expiration
- In-memory storage

## Setup

```bash
pip install fastapi uvicorn pytest httpx
uvicorn app:app --reload
```

## API Documentation

### POST `/shorten` — Create Short URL

**Request Body:**
```json
{
    "url": "https://www.example.com/very/long/url",
    "custom_alias": "mylink",
    "expiration_minutes": 60
}
```
- `url` (required) — The long URL to shorten
- `custom_alias` (optional) — Custom code instead of random
- `expiration_minutes` (optional) — Minutes until the link expires

**Response (201):**
```json
{
    "code": "mylink",
    "short_url": "http://localhost:8000/mylink"
}
```

**Errors:**
- `400` — URL already exists or custom alias taken

---

### GET `/{code}` — Redirect to Original URL

Redirects (HTTP 307) to the original URL. Increments click counter.

**Example:**
```
GET http://localhost:8000/abcdef → Redirects to https://www.google.com
```

**Errors:**
- `404` — Short code not found
- `410` — Short URL has expired

---

### GET `/info/{code}` — Get URL Info

Returns metadata about a short URL without redirecting.

**Response (200):**
```json
{
    "code": "abcdef",
    "original_url": "https://www.google.com",
    "short_url": "http://localhost:8000/abcdef",
    "clicks": 5,
    "created_at": "2026-07-14T15:30:00",
    "expires_at": null
}
```

**Errors:**
- `404` — Short code not found

---

## Example Usage

### Create a short URL
```bash
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.github.com/akshit"}'
```

### Create with custom alias
```bash
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.python.org", "custom_alias": "python"}'
```

### Create with expiration (30 minutes)
```bash
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://temporary.link", "expiration_minutes": 30}'
```

### Use the short URL
```bash
curl -L http://localhost:8000/abcdef
# -L flag follows redirects
```

### Get URL info
```bash
curl http://localhost:8000/info/abcdef
```

## Running Tests

```bash
pytest test_app.py -v
```

## Interactive Docs

Visit `http://localhost:8000/docs` for Swagger UI.
