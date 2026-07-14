# Data Validator

A flexible data validation library that validates Python dictionaries against schemas. Supports string, number, email, URL, and date validations with clear error messages.

## Features

- **5 built-in types**: string, number, email, url, date
- **Required/optional fields**: mark fields as required or optional
- **Min/max constraints**: length for strings, value for numbers
- **Regex validation**: email and URL format checking
- **Clear error messages**: human-readable errors per field
- **Extensible design**: easy to add new types via VALIDATORS mapping

## Usage

```python
from app import validate

schema = {
    "name":     {"type": "string", "required": True, "min": 2, "max": 50},
    "email":    {"type": "email",  "required": True},
    "age":      {"type": "number", "min": 18, "max": 120},
    "website":  {"type": "url",    "required": False},
    "birthday": {"type": "date",   "required": False},
}

data = {
    "name": "Akshit",
    "email": "akshit@gmail.com",
    "age": 22,
}

result = validate(data, schema)
# {"valid": True, "errors": []}
```

## Supported Types

### `string`
Validates that the value is a Python string. Supports `min` and `max` for **length**.

```python
{"type": "string", "required": True, "min": 2, "max": 50}
```

### `number`
Validates that the value is an int or float (booleans rejected). Supports `min` and `max` for **value**.

```python
{"type": "number", "min": 18, "max": 120}
```

### `email`
Validates email format: `user@domain.tld`

```python
{"type": "email", "required": True}
```

### `url`
Validates URL format: must start with `http://` or `https://`

```python
{"type": "url", "required": False}
```

### `date`
Validates ISO date format: `YYYY-MM-DD`

```python
{"type": "date", "required": False}
```

## Schema Rules

| Rule | Type | Description |
|------|------|-------------|
| `type` | all | The validation type (string, number, email, url, date) |
| `required` | all | If `True`, field must be present. Default: `False` |
| `min` | string, number | Min length (string) or min value (number) |
| `max` | string, number | Max length (string) or max value (number) |

## Running

```bash
# Run example
python3 app.py

# Run tests
python3 -m pytest test_app.py -v
```

## Test Coverage

62 tests covering:
- 11 string tests (min/max length, wrong type, empty, spaces)
- 11 number tests (int, float, boolean rejection, zero, negative)
- 11 email tests (valid formats, missing @, double @, spaces)
- 11 URL tests (http/https, paths, missing protocol, ftp rejected)
- 11 date tests (ISO format, invalid months/days, leap years)
- 4 required/optional tests
- 3 full schema tests
