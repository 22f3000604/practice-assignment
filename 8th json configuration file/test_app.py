import os
import json
import pytest
from app import (
    ConfigurationManager,
    ConfigError,
    InterpolationError,
    ValidationError,
    config
)


# ---- Fixtures ----

@pytest.fixture
def clean_config():
    """Returns a fresh, clean ConfigurationManager instance."""
    return ConfigurationManager()


@pytest.fixture(autouse=True)
def clean_global_config():
    """Ensure the global config singleton is cleared before/after each test."""
    config.clear()
    yield
    config.clear()


# ---- Core Get / Set Tests ----

class TestGetSet:

    def test_initial_state_empty(self, clean_config):
        """Initial configuration should be empty."""
        assert clean_config.get("") == {}
        assert clean_config.get("any.key") is None

    def test_get_with_default(self, clean_config):
        """Should return default value if key is not found."""
        assert clean_config.get("database.port", 5432) == 5432
        assert clean_config.get("missing_key", "default_val") == "default_val"

    def test_set_flat_key(self, clean_config):
        """Should set and get a top-level key."""
        clean_config.set("app_name", "my_awesome_app")
        assert clean_config.get("app_name") == "my_awesome_app"

    def test_set_nested_key(self, clean_config):
        """Should set nested keys and automatically create intermediate dictionaries."""
        clean_config.set("database.host", "localhost")
        clean_config.set("database.port", 5432)
        assert clean_config.get("database.host") == "localhost"
        assert clean_config.get("database.port") == 5432
        assert clean_config.get("database") == {"host": "localhost", "port": 5432}

    def test_set_overwrite_intermediate_non_dict(self, clean_config):
        """Should overwrite a non-dictionary intermediate value if setting a nested path."""
        clean_config.set("database", "sqlite:///:memory:")
        assert clean_config.get("database") == "sqlite:///:memory:"
        # Now set nested
        clean_config.set("database.host", "127.0.0.1")
        assert clean_config.get("database") == {"host": "127.0.0.1"}

    def test_set_empty_key_path(self, clean_config):
        """Setting config with an empty key should raise a ConfigError."""
        with pytest.raises(ConfigError, match="Cannot set config with an empty key path."):
            clean_config.set("", "value")


# ---- Load & Merge Tests ----

class TestLoadAndMerge:

    def test_load_valid_json(self, clean_config, tmp_path):
        """Should load JSON config from file."""
        file = tmp_path / "config.json"
        file.write_text(json.dumps({"app": {"port": 8080, "debug": True}}))

        clean_config.load(str(file))
        assert clean_config.get("app.port") == 8080
        assert clean_config.get("app.debug") is True

    def test_load_non_existent_file(self, clean_config):
        """Loading a non-existent file should raise a ConfigError."""
        with pytest.raises(ConfigError, match="Configuration file not found"):
            clean_config.load("non_existent_file.json")

    def test_load_invalid_json(self, clean_config, tmp_path):
        """Loading an invalid JSON file should raise a ConfigError."""
        file = tmp_path / "config.json"
        file.write_text("{invalid json}")

        with pytest.raises(ConfigError, match="Failed to parse JSON file"):
            clean_config.load(str(file))

    def test_load_not_object(self, clean_config, tmp_path):
        """Loading a JSON that isn't a top-level object should raise ConfigError."""
        file = tmp_path / "config.json"
        file.write_text(json.dumps([1, 2, 3]))

        with pytest.raises(ConfigError, match="Loaded configuration must be a JSON object"):
            clean_config.load(str(file))

    def test_load_multiple_files_deep_merge(self, clean_config, tmp_path):
        """Sequential loading of configuration files should deep merge values."""
        file1 = tmp_path / "default.json"
        file1.write_text(json.dumps({
            "app": {"name": "app", "port": 8080},
            "db": {"host": "localhost", "port": 5432}
        }))

        file2 = tmp_path / "prod.json"
        file2.write_text(json.dumps({
            "app": {"port": 9000},
            "db": {"host": "prod-db"}
        }))

        clean_config.load(str(file1))
        clean_config.load(str(file2))

        # Overwritten
        assert clean_config.get("app.port") == 9000
        assert clean_config.get("db.host") == "prod-db"
        # Preserved
        assert clean_config.get("app.name") == "app"
        assert clean_config.get("db.port") == 5432

    def test_clear_resets_config(self, clean_config):
        """clear() should empty all configuration values."""
        clean_config.set("foo", "bar")
        assert clean_config.get("foo") == "bar"
        clean_config.clear()
        assert clean_config.get("foo") is None
        assert clean_config.get("") == {}


# ---- Env Var Interpolation Tests ----

class TestInterpolation:

    def test_interpolate_exact_match(self, clean_config, tmp_path, monkeypatch):
        """Should interpolate a exact env var reference with type coercion."""
        monkeypatch.setenv("TEST_HOST", "db.internal")
        monkeypatch.setenv("TEST_PORT", "1234")
        monkeypatch.setenv("TEST_DEBUG", "True")
        monkeypatch.setenv("TEST_NULL", "null")

        file = tmp_path / "config.json"
        file.write_text(json.dumps({
            "host": "${TEST_HOST}",
            "port": "${TEST_PORT}",
            "debug": "${TEST_DEBUG}",
            "nullable": "${TEST_NULL}"
        }))

        clean_config.load(str(file))

        assert clean_config.get("host") == "db.internal"
        # coerced to int
        assert clean_config.get("port") == 1234
        # coerced to bool
        assert clean_config.get("debug") is True
        # coerced to None
        assert clean_config.get("nullable") is None

    def test_interpolate_with_defaults(self, clean_config, tmp_path, monkeypatch):
        """Should resolve fallback defaults when env var is missing."""
        # Ensure they are not set
        monkeypatch.delenv("TEST_HOST", raising=False)
        monkeypatch.delenv("TEST_PORT", raising=False)

        file = tmp_path / "config.json"
        file.write_text(json.dumps({
            "host": "${TEST_HOST:localhost}",
            "port": "${TEST_PORT:3306}"
        }))

        clean_config.load(str(file))

        assert clean_config.get("host") == "localhost"
        assert clean_config.get("port") == 3306

    def test_interpolate_missing_raises_error(self, clean_config, tmp_path, monkeypatch):
        """Should raise InterpolationError if an env var is missing and has no default."""
        monkeypatch.delenv("MISSING_VAR", raising=False)

        file = tmp_path / "config.json"
        file.write_text(json.dumps({"key": "${MISSING_VAR}"}))

        with pytest.raises(InterpolationError, match="Missing environment variable: 'MISSING_VAR'"):
            clean_config.load(str(file))

    def test_interpolate_inline_mixed_string(self, clean_config, tmp_path, monkeypatch):
        """Should interpolate multiple env vars inline inside a larger string without type coercion."""
        monkeypatch.setenv("DB_USER", "postgres")
        monkeypatch.setenv("DB_PASS", "secret")
        monkeypatch.setenv("DB_PORT", "5432")

        file = tmp_path / "config.json"
        file.write_text(json.dumps({
            "connection_uri": "postgresql://${DB_USER}:${DB_PASS}@localhost:${DB_PORT}/mydb"
        }))

        clean_config.load(str(file))

        expected = "postgresql://postgres:secret@localhost:5432/mydb"
        assert clean_config.get("connection_uri") == expected

    def test_interpolate_nested_structures(self, clean_config, tmp_path, monkeypatch):
        """Should interpolate env vars in nested structures (lists, nested dicts)."""
        monkeypatch.setenv("ENV_NAME", "dev")
        monkeypatch.setenv("SERVER_IP", "10.0.0.1")

        file = tmp_path / "config.json"
        file.write_text(json.dumps({
            "environments": ["local", "${ENV_NAME}"],
            "servers": [
                {"ip": "${SERVER_IP}", "active": True}
            ]
        }))

        clean_config.load(str(file))

        assert clean_config.get("environments") == ["local", "dev"]
        assert clean_config.get("servers") == [{"ip": "10.0.0.1", "active": True}]


# ---- Schema Validation Tests ----

class TestSchemaValidation:

    @pytest.fixture
    def full_schema(self):
        return {
            "type": "object",
            "required": ["app_name", "database"],
            "properties": {
                "app_name": {"type": "string", "min_length": 3, "max_length": 20},
                "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                "database": {
                    "type": "object",
                    "required": ["host", "port"],
                    "properties": {
                        "host": {"type": "string", "pattern": r"^[a-zA-Z0-9.-]+$"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                        "driver": {"type": "string", "enum": ["pg", "mysql", "sqlite"]}
                    }
                },
                "features": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        }

    def test_validation_success(self, clean_config, full_schema):
        """Should return True if schema validation succeeds."""
        clean_config.set("app_name", "My Cool App")
        clean_config.set("port", 8080)
        clean_config.set("database.host", "db-prod.internal")
        clean_config.set("database.port", 5432)
        clean_config.set("database.driver", "pg")
        clean_config.set("features", ["auth", "billing"])

        assert clean_config.validate(full_schema) is True

    def test_validation_fails_missing_required(self, clean_config, full_schema):
        """Should raise ValidationError listing missing required fields."""
        clean_config.set("app_name", "My App")
        # Missing 'database'

        with pytest.raises(ValidationError) as excinfo:
            clean_config.validate(full_schema)

        errors = excinfo.value.errors
        assert any("database: is a required field" in err for err in errors)

    def test_validation_fails_type_mismatch(self, clean_config, full_schema):
        """Should raise ValidationError listing type mismatches."""
        clean_config.set("app_name", "My App")
        clean_config.set("port", "eight-thousand")  # string, should be integer
        clean_config.set("database.host", "db")
        clean_config.set("database.port", "5432")  # string, should be integer

        with pytest.raises(ValidationError) as excinfo:
            clean_config.validate(full_schema)

        errors = excinfo.value.errors
        assert any("port: expected 'integer', got 'str'" in err for err in errors)
        assert any("database.port: expected 'integer', got 'str'" in err for err in errors)

    def test_validation_fails_constraints(self, clean_config, full_schema):
        """Should raise ValidationError listing constraint violations (min/max, length, regex, enum)."""
        clean_config.set("app_name", "Ap")  # too short (minLength 3)
        clean_config.set("port", 80)        # too low (minimum 1024)
        clean_config.set("database.host", "db#invalid")  # pattern mismatch (letters/numbers/dots/hyphens only)
        clean_config.set("database.port", 70000)        # too high (maximum 65535)
        clean_config.set("database.driver", "oracle")    # not in enum

        with pytest.raises(ValidationError) as excinfo:
            clean_config.validate(full_schema)

        errors = excinfo.value.errors
        assert any("app_name: length is 2, must be at least 3" in err for err in errors)
        assert any("port: value 80 must be at least 1024" in err for err in errors)
        assert any("database.host: does not match pattern" in err for err in errors)
        assert any("database.port: value 70000 must be at most 65535" in err for err in errors)
        assert any("database.driver: value 'oracle' is not in allowed values" in err for err in errors)

    def test_validation_direct_mapping_format(self, clean_config):
        """Should validate successfully with direct key-schema maps (omitting top-level object wrapper)."""
        schema = {
            "host": {"type": "string", "min_length": 3},
            "port": {"type": "integer"}
        }
        clean_config.set("host", "localhost")
        clean_config.set("port", 3306)

        assert clean_config.validate(schema) is True

        # And fail appropriately
        clean_config.set("host", "lh")  # too short
        with pytest.raises(ValidationError) as excinfo:
            clean_config.validate(schema)
        
        assert any("host: length is 2, must be at least 3" in err for err in excinfo.value.errors)
