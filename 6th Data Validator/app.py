import re
from datetime import datetime


# ---- Type Validators ----

def validate_string(field, value, rules):
    """Validate a string field against rules (min/max length)"""
    errors = []

    if not isinstance(value, str):
        errors.append(f"{field}: expected string, got {type(value).__name__}")
        return errors

    if "min" in rules and len(value) < rules["min"]:
        errors.append(f"{field}: must be at least {rules['min']} characters")

    if "max" in rules and len(value) > rules["max"]:
        errors.append(f"{field}: must be at most {rules['max']} characters")

    return errors


def validate_number(field, value, rules):
    """Validate a number field against rules (min/max value)"""
    errors = []

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        errors.append(f"{field}: expected number, got {type(value).__name__}")
        return errors

    if "min" in rules and value < rules["min"]:
        errors.append(f"{field}: must be at least {rules['min']}")

    if "max" in rules and value > rules["max"]:
        errors.append(f"{field}: must be at most {rules['max']}")

    return errors


def validate_email(field, value, rules):
    """Validate email format using regex"""
    errors = []

    if not isinstance(value, str):
        errors.append(f"{field}: expected string for email, got {type(value).__name__}")
        return errors

    # Basic email pattern: something@something.something
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, value):
        errors.append(f"{field}: invalid email format")

    return errors


def validate_url(field, value, rules):
    """Validate URL format"""
    errors = []

    if not isinstance(value, str):
        errors.append(f"{field}: expected string for URL, got {type(value).__name__}")
        return errors

    # URL must start with http:// or https://
    url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    if not re.match(url_pattern, value):
        errors.append(f"{field}: invalid URL format")

    return errors


def validate_date(field, value, rules):
    """Validate ISO date format (YYYY-MM-DD)"""
    errors = []

    if not isinstance(value, str):
        errors.append(f"{field}: expected string for date, got {type(value).__name__}")
        return errors

    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        errors.append(f"{field}: invalid date format, expected YYYY-MM-DD")

    return errors


# ---- Validator Mapping ----

VALIDATORS = {
    "string": validate_string,
    "number": validate_number,
    "email": validate_email,
    "url": validate_url,
    "date": validate_date,
}


# ---- Main Validate Function ----

def validate(data, schema):
    """
    Validate data against a schema.

    Args:
        data: dict of field names to values
        schema: dict of field names to rules

    Returns:
        dict with 'valid' (bool) and 'errors' (list of strings)
    """
    errors = []

    for field, rules in schema.items():
        is_required = rules.get("required", False)
        field_type = rules.get("type")

        # Step 1: Check if required field is missing
        if field not in data or data[field] is None:
            if is_required:
                errors.append(f"{field}: this field is required")
            continue  # skip further checks for missing optional fields

        value = data[field]

        # Step 2: Check if type is supported
        if field_type not in VALIDATORS:
            errors.append(f"{field}: unknown type '{field_type}'")
            continue

        # Step 3: Run the type-specific validator
        validator_func = VALIDATORS[field_type]
        field_errors = validator_func(field, value, rules)
        errors.extend(field_errors)

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


# ---- Example Usage ----

if __name__ == "__main__":
    schema = {
        "name": {"type": "string", "required": True, "min": 2, "max": 50},
        "email": {"type": "email", "required": True},
        "age": {"type": "number", "min": 18, "max": 120},
        "website": {"type": "url", "required": False},
        "birthday": {"type": "date", "required": False},
    }

    # Valid data
    print("--- Test 1: Valid Data ---")
    data1 = {
        "name": "Akshit",
        "email": "akshit@gmail.com",
        "age": 22,
        "website": "https://akshit.dev",
        "birthday": "2004-01-15",
    }
    result = validate(data1, schema)
    print(f"Valid: {result['valid']}")
    print(f"Errors: {result['errors']}")

    # Invalid data
    print("\n--- Test 2: Invalid Data ---")
    data2 = {
        "name": "A",
        "email": "not-an-email",
        "age": 15,
        "website": "just-text",
        "birthday": "15-01-2004",
    }
    result = validate(data2, schema)
    print(f"Valid: {result['valid']}")
    for error in result["errors"]:
        print(f"  - {error}")

    # Missing required fields
    print("\n--- Test 3: Missing Required Fields ---")
    data3 = {"age": 25}
    result = validate(data3, schema)
    print(f"Valid: {result['valid']}")
    for error in result["errors"]:
        print(f"  - {error}")
