import pytest
from app import check_password


# ---- Weak Password Tests ----

def test_empty_password():
    points, feedback = check_password("")
    assert points <= 2

def test_short_password():
    points, feedback = check_password("hi")
    assert points <= 2

def test_only_spaces():
    points, feedback = check_password("     ")
    assert points <= 2

def test_common_password():
    points, feedback = check_password("password")
    assert "This is a commonly used password!" in feedback

def test_common_password_qwerty():
    points, feedback = check_password("qwerty")
    assert "This is a commonly used password!" in feedback


# ---- Feedback Tests ----

def test_missing_uppercase_feedback():
    points, feedback = check_password("alllowercase")
    assert "Missing uppercase letters" in feedback

def test_missing_lowercase_feedback():
    points, feedback = check_password("ALLUPPERCASE")
    assert "Missing lowercase letters" in feedback

def test_missing_digits_feedback():
    points, feedback = check_password("NoDigitsHere!")
    assert "Missing numbers" in feedback

def test_missing_special_chars_feedback():
    points, feedback = check_password("NoSpecial123")
    assert "Missing special characters (!@#$%...)" in feedback

def test_too_short_feedback():
    points, feedback = check_password("Ab1!")
    assert "Too short (minimum 8 characters)" in feedback


# ---- Fair Password Tests ----

def test_only_lowercase_long():
    points, feedback = check_password("abcdefgh")
    assert 3 <= points <= 4

def test_only_numbers_long():
    points, feedback = check_password("12345678")
    assert points <= 4


# ---- Good Password Tests ----

def test_mixed_no_special():
    points, feedback = check_password("Akshit2005")
    assert 5 <= points <= 6

def test_lowercase_digits_special():
    points, feedback = check_password("hello@123")
    assert points >= 4


# ---- Strong Password Tests ----

def test_strong_password():
    points, feedback = check_password("Akshit@2005#3")
    assert points >= 7

def test_strong_long_password():
    points, feedback = check_password("MyP@ssw0rd!2026")
    assert points >= 7

def test_strong_no_feedback():
    points, feedback = check_password("Str0ng!Pass#")
    assert len(feedback) == 0


# ---- Edge Cases ----

def test_exactly_8_chars():
    points, feedback = check_password("Abcd!1gh")
    assert "Too short (minimum 8 characters)" not in feedback

def test_exactly_12_chars_bonus():
    points1, _ = check_password("Abcd!1g")       # 7 chars
    points2, _ = check_password("Abcd!1ghijkl")  # 12 chars
    assert points2 > points1

def test_common_password_case_insensitive():
    points, feedback = check_password("PASSWORD")
    assert "This is a commonly used password!" in feedback

def test_single_char():
    points, feedback = check_password("a")
    assert points <= 2

def test_all_special_chars():
    points, feedback = check_password("!@#$%^&*()")
    assert "Missing uppercase letters" in feedback
    assert "Missing lowercase letters" in feedback
    assert "Missing numbers" in feedback
