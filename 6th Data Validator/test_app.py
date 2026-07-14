import pytest
from app import validate, validate_string, validate_number, validate_email, validate_url, validate_date


# ============================================================
# Tests for STRING validation
# ============================================================

class TestStringValidation:

    def test_valid_string(self):
        result = validate({"name": "Akshit"}, {"name": {"type": "string", "required": True}})
        assert result["valid"] is True

    def test_string_min_length_pass(self):
        result = validate({"name": "AB"}, {"name": {"type": "string", "min": 2}})
        assert result["valid"] is True

    def test_string_min_length_fail(self):
        result = validate({"name": "A"}, {"name": {"type": "string", "min": 2}})
        assert result["valid"] is False
        assert "at least 2 characters" in result["errors"][0]

    def test_string_max_length_pass(self):
        result = validate({"name": "Hello"}, {"name": {"type": "string", "max": 10}})
        assert result["valid"] is True

    def test_string_max_length_fail(self):
        result = validate({"name": "Hello World!!"}, {"name": {"type": "string", "max": 5}})
        assert result["valid"] is False
        assert "at most 5 characters" in result["errors"][0]

    def test_string_min_and_max(self):
        result = validate({"name": "Hi"}, {"name": {"type": "string", "min": 2, "max": 50}})
        assert result["valid"] is True

    def test_string_wrong_type(self):
        result = validate({"name": 123}, {"name": {"type": "string"}})
        assert result["valid"] is False
        assert "expected string" in result["errors"][0]

    def test_string_empty(self):
        result = validate({"name": ""}, {"name": {"type": "string", "min": 1}})
        assert result["valid"] is False

    def test_string_exact_min(self):
        result = validate({"name": "AB"}, {"name": {"type": "string", "min": 2}})
        assert result["valid"] is True

    def test_string_exact_max(self):
        result = validate({"name": "ABCDE"}, {"name": {"type": "string", "max": 5}})
        assert result["valid"] is True

    def test_string_with_spaces(self):
        result = validate({"name": "John Doe"}, {"name": {"type": "string", "min": 2, "max": 50}})
        assert result["valid"] is True


# ============================================================
# Tests for NUMBER validation
# ============================================================

class TestNumberValidation:

    def test_valid_integer(self):
        result = validate({"age": 25}, {"age": {"type": "number"}})
        assert result["valid"] is True

    def test_valid_float(self):
        result = validate({"price": 19.99}, {"price": {"type": "number"}})
        assert result["valid"] is True

    def test_number_min_pass(self):
        result = validate({"age": 18}, {"age": {"type": "number", "min": 18}})
        assert result["valid"] is True

    def test_number_min_fail(self):
        result = validate({"age": 15}, {"age": {"type": "number", "min": 18}})
        assert result["valid"] is False
        assert "at least 18" in result["errors"][0]

    def test_number_max_pass(self):
        result = validate({"age": 100}, {"age": {"type": "number", "max": 120}})
        assert result["valid"] is True

    def test_number_max_fail(self):
        result = validate({"age": 150}, {"age": {"type": "number", "max": 120}})
        assert result["valid"] is False
        assert "at most 120" in result["errors"][0]

    def test_number_min_and_max(self):
        result = validate({"age": 25}, {"age": {"type": "number", "min": 18, "max": 120}})
        assert result["valid"] is True

    def test_number_wrong_type_string(self):
        result = validate({"age": "twenty"}, {"age": {"type": "number"}})
        assert result["valid"] is False
        assert "expected number" in result["errors"][0]

    def test_number_boolean_rejected(self):
        """Booleans are technically ints in Python but should be rejected"""
        result = validate({"age": True}, {"age": {"type": "number"}})
        assert result["valid"] is False

    def test_number_zero(self):
        result = validate({"count": 0}, {"count": {"type": "number", "min": 0}})
        assert result["valid"] is True

    def test_number_negative(self):
        result = validate({"temp": -10}, {"temp": {"type": "number", "min": -20, "max": 50}})
        assert result["valid"] is True


# ============================================================
# Tests for EMAIL validation
# ============================================================

class TestEmailValidation:

    def test_valid_email(self):
        result = validate({"email": "user@example.com"}, {"email": {"type": "email"}})
        assert result["valid"] is True

    def test_valid_email_with_dots(self):
        result = validate({"email": "first.last@example.com"}, {"email": {"type": "email"}})
        assert result["valid"] is True

    def test_valid_email_with_plus(self):
        result = validate({"email": "user+tag@gmail.com"}, {"email": {"type": "email"}})
        assert result["valid"] is True

    def test_email_missing_at(self):
        result = validate({"email": "userexample.com"}, {"email": {"type": "email"}})
        assert result["valid"] is False
        assert "invalid email format" in result["errors"][0]

    def test_email_missing_domain(self):
        result = validate({"email": "user@"}, {"email": {"type": "email"}})
        assert result["valid"] is False

    def test_email_missing_tld(self):
        result = validate({"email": "user@example"}, {"email": {"type": "email"}})
        assert result["valid"] is False

    def test_email_double_at(self):
        result = validate({"email": "user@@example.com"}, {"email": {"type": "email"}})
        assert result["valid"] is False

    def test_email_empty_string(self):
        result = validate({"email": ""}, {"email": {"type": "email"}})
        assert result["valid"] is False

    def test_email_spaces(self):
        result = validate({"email": "user @example.com"}, {"email": {"type": "email"}})
        assert result["valid"] is False

    def test_email_wrong_type(self):
        result = validate({"email": 12345}, {"email": {"type": "email"}})
        assert result["valid"] is False
        assert "expected string" in result["errors"][0]

    def test_email_subdomain(self):
        result = validate({"email": "user@mail.example.com"}, {"email": {"type": "email"}})
        assert result["valid"] is True


# ============================================================
# Tests for URL validation
# ============================================================

class TestURLValidation:

    def test_valid_http_url(self):
        result = validate({"site": "http://example.com"}, {"site": {"type": "url"}})
        assert result["valid"] is True

    def test_valid_https_url(self):
        result = validate({"site": "https://example.com"}, {"site": {"type": "url"}})
        assert result["valid"] is True

    def test_url_with_path(self):
        result = validate({"site": "https://example.com/page"}, {"site": {"type": "url"}})
        assert result["valid"] is True

    def test_url_missing_protocol(self):
        result = validate({"site": "example.com"}, {"site": {"type": "url"}})
        assert result["valid"] is False
        assert "invalid URL format" in result["errors"][0]

    def test_url_ftp_rejected(self):
        result = validate({"site": "ftp://example.com"}, {"site": {"type": "url"}})
        assert result["valid"] is False

    def test_url_just_protocol(self):
        result = validate({"site": "https://"}, {"site": {"type": "url"}})
        assert result["valid"] is False

    def test_url_empty_string(self):
        result = validate({"site": ""}, {"site": {"type": "url"}})
        assert result["valid"] is False

    def test_url_plain_text(self):
        result = validate({"site": "not a url"}, {"site": {"type": "url"}})
        assert result["valid"] is False

    def test_url_wrong_type(self):
        result = validate({"site": 12345}, {"site": {"type": "url"}})
        assert result["valid"] is False
        assert "expected string" in result["errors"][0]

    def test_url_with_subdomain(self):
        result = validate({"site": "https://www.example.com"}, {"site": {"type": "url"}})
        assert result["valid"] is True

    def test_url_with_deep_path(self):
        result = validate({"site": "https://example.com/a/b/c"}, {"site": {"type": "url"}})
        assert result["valid"] is True


# ============================================================
# Tests for DATE validation
# ============================================================

class TestDateValidation:

    def test_valid_date(self):
        result = validate({"dob": "2004-01-15"}, {"dob": {"type": "date"}})
        assert result["valid"] is True

    def test_date_wrong_format_dmy(self):
        result = validate({"dob": "15-01-2004"}, {"dob": {"type": "date"}})
        assert result["valid"] is False
        assert "invalid date format" in result["errors"][0]

    def test_date_wrong_format_slash(self):
        result = validate({"dob": "2004/01/15"}, {"dob": {"type": "date"}})
        assert result["valid"] is False

    def test_date_invalid_month(self):
        result = validate({"dob": "2004-13-01"}, {"dob": {"type": "date"}})
        assert result["valid"] is False

    def test_date_invalid_day(self):
        result = validate({"dob": "2004-01-32"}, {"dob": {"type": "date"}})
        assert result["valid"] is False

    def test_date_empty_string(self):
        result = validate({"dob": ""}, {"dob": {"type": "date"}})
        assert result["valid"] is False

    def test_date_plain_text(self):
        result = validate({"dob": "January 15"}, {"dob": {"type": "date"}})
        assert result["valid"] is False

    def test_date_wrong_type(self):
        result = validate({"dob": 20040115}, {"dob": {"type": "date"}})
        assert result["valid"] is False
        assert "expected string" in result["errors"][0]

    def test_date_leap_year_valid(self):
        result = validate({"dob": "2024-02-29"}, {"dob": {"type": "date"}})
        assert result["valid"] is True

    def test_date_leap_year_invalid(self):
        result = validate({"dob": "2023-02-29"}, {"dob": {"type": "date"}})
        assert result["valid"] is False

    def test_date_first_day(self):
        result = validate({"dob": "2026-01-01"}, {"dob": {"type": "date"}})
        assert result["valid"] is True


# ============================================================
# Tests for REQUIRED / OPTIONAL fields
# ============================================================

class TestRequiredOptional:

    def test_required_field_missing(self):
        result = validate({}, {"name": {"type": "string", "required": True}})
        assert result["valid"] is False
        assert "required" in result["errors"][0]

    def test_optional_field_missing(self):
        result = validate({}, {"website": {"type": "url", "required": False}})
        assert result["valid"] is True
        assert result["errors"] == []

    def test_required_field_none_value(self):
        result = validate({"name": None}, {"name": {"type": "string", "required": True}})
        assert result["valid"] is False

    def test_multiple_required_missing(self):
        schema = {
            "name": {"type": "string", "required": True},
            "email": {"type": "email", "required": True},
        }
        result = validate({}, schema)
        assert result["valid"] is False
        assert len(result["errors"]) == 2


# ============================================================
# Tests for FULL SCHEMA validation
# ============================================================

class TestFullSchema:

    def test_all_valid(self):
        schema = {
            "name": {"type": "string", "required": True, "min": 2, "max": 50},
            "email": {"type": "email", "required": True},
            "age": {"type": "number", "min": 18, "max": 120},
            "website": {"type": "url", "required": False},
            "birthday": {"type": "date", "required": False},
        }
        data = {
            "name": "Akshit",
            "email": "akshit@gmail.com",
            "age": 22,
            "website": "https://akshit.dev",
            "birthday": "2004-01-15",
        }
        result = validate(data, schema)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_multiple_errors(self):
        schema = {
            "name": {"type": "string", "required": True, "min": 2},
            "email": {"type": "email", "required": True},
            "age": {"type": "number", "min": 18},
        }
        data = {"name": "A", "email": "bad", "age": 10}
        result = validate(data, schema)
        assert result["valid"] is False
        assert len(result["errors"]) == 3

    def test_unknown_type(self):
        result = validate({"field": "value"}, {"field": {"type": "phone"}})
        assert result["valid"] is False
        assert "unknown type" in result["errors"][0]
