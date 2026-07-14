import os
import json
import re
from typing import Any, Dict, List, Optional, Union

# ---- Exceptions ----

class ConfigError(Exception):
    """Base exception for all configuration-related errors."""
    pass


class InterpolationError(ConfigError):
    """Raised when environment variable interpolation fails."""
    pass


class ValidationError(ConfigError):
    """Raised when configuration validation fails."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors))


# ---- Helper Functions ----

def coerce_type(val: str) -> Any:
    """Coerce a string representation to a proper Python type (int, float, bool, None)."""
    val_lower = val.strip().lower()
    if val_lower in ("null", "none"):
        return None
    if val_lower == "true":
        return True
    if val_lower == "false":
        return False

    # Try parsing as integer
    try:
        return int(val)
    except ValueError:
        pass

    # Try parsing as float
    try:
        return float(val)
    except ValueError:
        pass

    return val


def interpolate_value(val: Any) -> Any:
    """
    Recursively interpolate environment variables in the format ${VAR_NAME} or ${VAR_NAME:default}.
    Supports type coercion for exact matches, and inline substitution for mixed strings.
    """
    if isinstance(val, str):
        # 1. Exact match for a single environment variable with optional default
        # E.g., "${DB_PORT}" or "${DB_PORT:5432}"
        exact_match = re.match(r"^\$\{([A-Za-z0-9_]+)(?::([^}]*))?\}$", val)
        if exact_match:
            var_name = exact_match.group(1)
            default_val = exact_match.group(2)

            if var_name in os.environ:
                resolved = os.environ[var_name]
            elif default_val is not None:
                resolved = default_val
            else:
                raise InterpolationError(f"Missing environment variable: '{var_name}' and no default value was provided.")

            return coerce_type(resolved)

        # 2. Inline/embedded substitution
        # E.g., "myapp_${NODE_ENV}" or "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}"
        def replace_match(m: re.Match) -> str:
            var_name = m.group(1)
            default_val = m.group(2)
            if var_name in os.environ:
                return os.environ[var_name]
            elif default_val is not None:
                return default_val
            else:
                raise InterpolationError(f"Missing environment variable: '{var_name}' and no default value was provided.")

        try:
            return re.sub(r"\$\{([A-Za-z0-9_]+)(?::([^}]*))?\}", replace_match, val)
        except InterpolationError as e:
            raise e

    elif isinstance(val, dict):
        return {k: interpolate_value(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [interpolate_value(item) for item in val]
    else:
        return val


def deep_merge(dict_a: dict, dict_b: dict) -> dict:
    """Recursively merges dict_b into dict_a in place and returns dict_a."""
    for key, val in dict_b.items():
        if key in dict_a and isinstance(dict_a[key], dict) and isinstance(val, dict):
            deep_merge(dict_a[key], val)
        else:
            dict_a[key] = val
    return dict_a


def validate_data(data: Any, schema: dict, path: str = "") -> List[str]:
    """Validates data against a schema and returns a list of error messages."""
    errors = []
    expected_type = schema.get("type")

    # If expected_type is not defined, we cannot validate type, but continue other constraints if possible.
    if expected_type is None:
        return errors

    # Check for null values
    if data is None:
        if expected_type != "null":
            errors.append(f"{path}: expected type '{expected_type}', got null" if path else f"Expected type '{expected_type}', got null")
        return errors

    # Type matching checks
    type_matches = True
    actual_type_name = type(data).__name__

    if expected_type == "object":
        if not isinstance(data, dict):
            errors.append(f"{path}: expected 'object', got '{actual_type_name}'" if path else f"Expected 'object', got '{actual_type_name}'")
            type_matches = False
    elif expected_type == "array":
        if not isinstance(data, (list, tuple)):
            errors.append(f"{path}: expected 'array', got '{actual_type_name}'" if path else f"Expected 'array', got '{actual_type_name}'")
            type_matches = False
    elif expected_type == "string":
        if not isinstance(data, str):
            errors.append(f"{path}: expected 'string', got '{actual_type_name}'" if path else f"Expected 'string', got '{actual_type_name}'")
            type_matches = False
    elif expected_type == "integer":
        if not isinstance(data, int) or isinstance(data, bool):
            errors.append(f"{path}: expected 'integer', got '{actual_type_name}'" if path else f"Expected 'integer', got '{actual_type_name}'")
            type_matches = False
    elif expected_type == "number":
        if not isinstance(data, (int, float)) or isinstance(data, bool):
            errors.append(f"{path}: expected 'number', got '{actual_type_name}'" if path else f"Expected 'number', got '{actual_type_name}'")
            type_matches = False
    elif expected_type == "boolean":
        if not isinstance(data, bool):
            errors.append(f"{path}: expected 'boolean', got '{actual_type_name}'" if path else f"Expected 'boolean', got '{actual_type_name}'")
            type_matches = False

    if not type_matches:
        return errors

    # Constraint validations
    if expected_type == "object" and isinstance(data, dict):
        # 1. Required keys check
        required_fields = schema.get("required", [])
        if isinstance(required_fields, list):
            for req in required_fields:
                if req not in data:
                    field_path = f"{path}.{req}" if path else req
                    errors.append(f"{field_path}: is a required field" if field_path else "Required field is missing")

        # 2. Nested properties check
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for prop_name, prop_schema in properties.items():
                if prop_name in data:
                    field_path = f"{path}.{prop_name}" if path else prop_name
                    errors.extend(validate_data(data[prop_name], prop_schema, field_path))

    elif expected_type == "array" and isinstance(data, list):
        # check items schema if present
        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for index, item in enumerate(data):
                field_path = f"{path}[{index}]"
                errors.extend(validate_data(item, items_schema, field_path))

    elif expected_type == "string" and isinstance(data, str):
        # minLength
        min_len = schema.get("minLength") or schema.get("min_length")
        if min_len is not None and len(data) < min_len:
            errors.append(f"{path}: length is {len(data)}, must be at least {min_len}" if path else f"Length is {len(data)}, must be at least {min_len}")
        # maxLength
        max_len = schema.get("maxLength") or schema.get("max_length")
        if max_len is not None and len(data) > max_len:
            errors.append(f"{path}: length is {len(data)}, must be at most {max_len}" if path else f"Length is {len(data)}, must be at most {max_len}")
        # pattern
        pattern = schema.get("pattern")
        if pattern is not None:
            if not re.search(pattern, data):
                errors.append(f"{path}: does not match pattern '{pattern}'" if path else f"Does not match pattern '{pattern}'")
        # enum
        enum_list = schema.get("enum")
        if enum_list is not None and isinstance(enum_list, list):
            if data not in enum_list:
                errors.append(f"{path}: value '{data}' is not in allowed values {enum_list}" if path else f"Value '{data}' is not in allowed values {enum_list}")

    elif expected_type in ("integer", "number") and isinstance(data, (int, float)):
        # minimum
        minimum = schema.get("minimum")
        if minimum is not None and data < minimum:
            errors.append(f"{path}: value {data} must be at least {minimum}" if path else f"Value {data} must be at least {minimum}")
        # maximum
        maximum = schema.get("maximum")
        if maximum is not None and data > maximum:
            errors.append(f"{path}: value {data} must be at most {maximum}" if path else f"Value {data} must be at most {maximum}")
        # enum
        enum_list = schema.get("enum")
        if enum_list is not None and isinstance(enum_list, list):
            if data not in enum_list:
                errors.append(f"{path}: value {data} is not in allowed values {enum_list}" if path else f"Value {data} is not in allowed values {enum_list}")

    # Fallback enum check for other types (e.g. boolean, null)
    if expected_type not in ("string", "integer", "number"):
        enum_list = schema.get("enum")
        if enum_list is not None and isinstance(enum_list, list):
            if data not in enum_list:
                errors.append(f"{path}: value is not in allowed values {enum_list}" if path else f"Value is not in allowed values {enum_list}")

    return errors


# ---- Configuration Manager ----

class ConfigurationManager:
    """Manages application configurations loaded from JSON files with environment interpolation and schema validation."""

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}

    def clear(self) -> None:
        """Resets the configuration object to empty."""
        self._config = {}

    def load(self, filepath: str) -> None:
        """
        Loads configuration from a JSON file. Environment variables in the format
        ${VAR_NAME} or ${VAR_NAME:default} are recursively interpolated.
        Overlaps in configurations are recursively deep merged.
        """
        try:
            with open(filepath, "r") as f:
                raw_data = json.load(f)
        except FileNotFoundError as e:
            raise ConfigError(f"Configuration file not found: '{filepath}'") from e
        except json.JSONDecodeError as e:
            raise ConfigError(f"Failed to parse JSON file '{filepath}': {e}") from e

        # Interpolate variables recursively
        interpolated = interpolate_value(raw_data)

        if not isinstance(interpolated, dict):
            raise ConfigError(f"Loaded configuration must be a JSON object (got {type(interpolated).__name__})")

        # Deep merge into active configuration
        self._config = deep_merge(self._config, interpolated)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value. Supports nested keys using dot notation (e.g., 'database.host').
        If key is empty or none, returns the entire configuration dictionary.
        """
        if not key:
            return self._config

        parts = key.split(".")
        current = self._config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def set(self, key: str, value: Any) -> None:
        """
        Sets a configuration value. Supports nested keys using dot notation (e.g., 'database.port').
        Intermediate dictionary structures are created automatically if they do not exist.
        """
        if not key:
            raise ConfigError("Cannot set config with an empty key path.")

        parts = key.split(".")
        current = self._config

        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def validate(self, schema: dict) -> bool:
        """
        Validates the configuration against a schema.
        Supports both standard JSON Schema format (with top-level 'type': 'object')
        and direct key-schema maps.
        Raises ValidationError if validation fails.
        """
        if not isinstance(schema, dict):
            raise ConfigError("Schema must be a dictionary.")

        # Normalize schema if it's key-schema mapping directly
        if "type" not in schema:
            normalized_schema = {
                "type": "object",
                "properties": schema
            }
        else:
            normalized_schema = schema

        errors = validate_data(self._config, normalized_schema)
        if errors:
            raise ValidationError(errors)

        return True


# Default instance export
config = ConfigurationManager()
