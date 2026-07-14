# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
from app import app, url_collection


client = TestClient(app)


# ---- Helper: Reset storage before each test ----

@pytest.fixture(autouse=True)
def reset_storage():
    """Clear and reset url_collection before each test"""
    url_collection.clear()
    url_collection["testcd"] = {
        "url": "https://www.google.com",
        "clicks": 0,
        "created_at": "2026-07-14T12:00:00",
        "expires_at": None
    }
    yield
    # cleanup after test
    url_collection.clear()


# ---- Tests for POST /shorten ----

class TestShortenURL:

    def test_shorten_new_url(self):
        """Should create a short code for a new URL"""
        response = client.post("/shorten", json={"url": "https://www.github.com"})
        assert response.status_code == 201
        data = response.json()
        assert "code" in data
        assert "short_url" in data
        assert len(data["code"]) == 6

    def test_shorten_duplicate_url(self):
        """Should reject a URL that already exists"""
        response = client.post("/shorten", json={"url": "https://www.google.com"})
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_shorten_with_custom_alias(self):
        """Should accept a custom alias"""
        response = client.post("/shorten", json={
            "url": "https://www.python.org",
            "custom_alias": "python"
        })
        assert response.status_code == 201
        assert response.json()["code"] == "python"

    def test_shorten_duplicate_custom_alias(self):
        """Should reject if custom alias is already taken"""
        response = client.post("/shorten", json={
            "url": "https://www.reddit.com",
            "custom_alias": "testcd"  # already exists in fixture
        })
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"]

    def test_shorten_with_expiration(self):
        """Should set expiration time when provided"""
        response = client.post("/shorten", json={
            "url": "https://www.twitter.com",
            "expiration_minutes": 30
        })
        assert response.status_code == 201
        code = response.json()["code"]
        assert url_collection[code]["expires_at"] is not None


# ---- Tests for GET /{code} (Redirect) ----

class TestRedirect:

    def test_redirect_valid_code(self):
        """Should redirect to original URL"""
        response = client.get("/testcd", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "https://www.google.com"

    def test_redirect_invalid_code(self):
        """Should return 404 for unknown code"""
        response = client.get("/xxxxxx", follow_redirects=False)
        assert response.status_code == 404

    def test_redirect_tracks_clicks(self):
        """Should increment click count on redirect"""
        assert url_collection["testcd"]["clicks"] == 0
        client.get("/testcd", follow_redirects=False)
        assert url_collection["testcd"]["clicks"] == 1
        client.get("/testcd", follow_redirects=False)
        assert url_collection["testcd"]["clicks"] == 2

    def test_redirect_expired_url(self):
        """Should return 410 for expired URLs"""
        url_collection["expire"] = {
            "url": "https://www.expired.com",
            "clicks": 0,
            "created_at": "2026-07-14T12:00:00",
            "expires_at": "2020-01-01T00:00:00"  # already expired
        }
        response = client.get("/expire", follow_redirects=False)
        assert response.status_code == 410
        assert "expire" not in url_collection  # should be deleted


# ---- Tests for GET /info/{code} ----

class TestURLInfo:

    def test_info_valid_code(self):
        """Should return URL info"""
        response = client.get("/info/testcd")
        assert response.status_code == 200
        data = response.json()
        assert data["original_url"] == "https://www.google.com"
        assert data["code"] == "testcd"
        assert data["clicks"] == 0
        assert "created_at" in data

    def test_info_invalid_code(self):
        """Should return 404 for unknown code"""
        response = client.get("/info/xxxxxx")
        assert response.status_code == 404

    def test_info_shows_click_count(self):
        """Should reflect updated click count"""
        client.get("/testcd", follow_redirects=False)
        client.get("/testcd", follow_redirects=False)
        response = client.get("/info/testcd")
        assert response.json()["clicks"] == 2
