# pyrefly: ignore [missing-import]
import string
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
# pyrefly: ignore [missing-import]
from fastapi.responses import RedirectResponse
import random


app = FastAPI(
    title="URL Shortener API",
    description="A URL shortening service. Submit a long URL and receive a short code. Accessing the short code redirects to the original URL.",
    version="1.0.0"
)


# ---- Pydantic Models ----

class URLCreate(BaseModel):
    url: str
    custom_alias: Optional[str] = None          # custom alias option
    expiration_minutes: Optional[int] = None    # expiration time in minutes


# ---- In-Memory Storage ----
# Each entry stores metadata: original url, clicks, created_at, expires_at

url_collection = {
    "abcdef": {
        "url": "https://www.google.com",
        "clicks": 0,
        "created_at": datetime.now().isoformat(),
        "expires_at": None
    },
    "efghef": {
        "url": "https://www.facebook.com",
        "clicks": 0,
        "created_at": datetime.now().isoformat(),
        "expires_at": None
    },
    "ijklef": {
        "url": "https://www.youtube.com",
        "clicks": 0,
        "created_at": datetime.now().isoformat(),
        "expires_at": None
    },
}


# ---- Helper: Generate unique 6-char code ----

def generate_code():
    code = ""
    for i in range(6):
        code += random.choice(string.ascii_lowercase)

    while code in url_collection:
        code = ""
        for i in range(6):
            code += random.choice(string.ascii_lowercase)
    return code


# ---- POST /shorten - Create short URL ----

@app.post("/shorten", status_code=201)
def create_url(url_create: URLCreate):
    # Check for duplicate URL
    for key, value in url_collection.items():
        if value["url"] == url_create.url:
            raise HTTPException(status_code=400, detail=f"URL already exists with code: {key}")

    # Handle custom alias
    if url_create.custom_alias:
        if url_create.custom_alias in url_collection:
            raise HTTPException(status_code=400, detail="Custom alias already taken")
        code = url_create.custom_alias
    else:
        code = generate_code()

    # Handle expiration
    expires_at = None
    if url_create.expiration_minutes:
        expires_at = (datetime.now() + timedelta(minutes=url_create.expiration_minutes)).isoformat()

    # Store URL with metadata
    url_collection[code] = {
        "url": url_create.url,
        "clicks": 0,
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at
    }

    return {"code": code, "short_url": f"http://localhost:8000/{code}"}


# ---- GET /{code} - Redirect to original URL ----

@app.get("/{code}")
def redirect_url(code: str):
    if code not in url_collection:
        raise HTTPException(status_code=404, detail="Short code not found")

    entry = url_collection[code]

    # Check if expired
    if entry["expires_at"]:
        if datetime.now() > datetime.fromisoformat(entry["expires_at"]):
            del url_collection[code]
            raise HTTPException(status_code=410, detail="This short URL has expired")

    # Track click
    entry["clicks"] += 1

    return RedirectResponse(entry["url"])


# ---- GET /info/{code} - Get URL info ----

@app.get("/info/{code}")
def get_url_info(code: str):
    if code not in url_collection:
        raise HTTPException(status_code=404, detail="Short code not found")

    entry = url_collection[code]

    return {
        "code": code,
        "original_url": entry["url"],
        "short_url": f"http://localhost:8000/{code}",
        "clicks": entry["clicks"],
        "created_at": entry["created_at"],
        "expires_at": entry["expires_at"]
    }