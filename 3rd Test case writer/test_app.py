import pytest
from app import applydiscount


# ---- Normal Cases: VIP Customer ----

def test_vip_no_coupon():
    result = applydiscount(100, "vip", "")
    assert result == 85.0   # 15% off

def test_vip_save10_coupon():
    result = applydiscount(100, "vip", "SAVE10")
    assert result == 85.0   # max(15%, 10%) = 15%

def test_vip_save20_coupon():
    result = applydiscount(100, "vip", "SAVE20")
    assert result == 80.0   # max(15%, 20%) = 20%


# ---- Normal Cases: Regular Customer ----

def test_regular_no_coupon():
    result = applydiscount(100, "regular", "")
    assert result == 95.0   # 5% off

def test_regular_save10_coupon():
    result = applydiscount(100, "regular", "SAVE10")
    assert result == 90.0   # max(5%, 10%) = 10%

def test_regular_save20_coupon():
    result = applydiscount(100, "regular", "SAVE20")
    assert result == 80.0   # max(5%, 20%) = 20%


# ---- Normal Cases: Unknown Customer (no discount) ----

def test_unknown_no_coupon():
    result = applydiscount(100, "guest", "")
    assert result == 100.0  # 0% off

def test_unknown_save10_coupon():
    result = applydiscount(100, "guest", "SAVE10")
    assert result == 90.0   # max(0%, 10%) = 10%

def test_unknown_save20_coupon():
    result = applydiscount(100, "guest", "SAVE20")
    assert result == 80.0   # max(0%, 20%) = 20%


# ---- Error Cases ----

def test_negative_price():
    with pytest.raises(ValueError):
        applydiscount(-1, "vip", "")

def test_large_negative_price():
    with pytest.raises(ValueError):
        applydiscount(-100, "regular", "SAVE20")


# ---- Edge Cases: Price ----

def test_zero_price():
    result = applydiscount(0, "vip", "SAVE20")
    assert result == 0.0    # any discount on 0 = 0

def test_very_small_price():
    result = applydiscount(0.01, "vip", "")
    assert result == 0.01   # 0.01 * 0.85 = 0.0085 → rounds to 0.01

def test_large_price():
    result = applydiscount(9999.99, "regular", "SAVE20")
    assert result == 7999.99  # 9999.99 * 0.80


# ---- Edge Cases: Invalid Coupon ----

def test_invalid_coupon_code():
    result = applydiscount(100, "vip", "SAVE30")
    assert result == 85.0   # invalid coupon ignored, vip 15% applies

def test_lowercase_coupon():
    result = applydiscount(100, "regular", "save20")
    assert result == 95.0   # "save20" != "SAVE20", so only regular 5%


# ---- Edge Cases: Empty/None Customer ----

def test_empty_customer_type():
    result = applydiscount(100, "", "SAVE20")
    assert result == 80.0   # no customer discount, coupon 20% applies

def test_none_coupon():
    result = applydiscount(100, "vip", None)
    assert result == 85.0   # no coupon, vip 15% applies


# ---- Edge Cases: Rounding ----

def test_rounding_precision():
    result = applydiscount(33.33, "regular", "")
    assert result == 31.66  # 33.33 * 0.95 = 31.6635 → rounds to 31.66

def test_rounding_with_coupon():
    result = applydiscount(99.99, "vip", "SAVE10")
    assert result == 84.99  # 99.99 * 0.85 = 84.9915 → rounds to 84.99
