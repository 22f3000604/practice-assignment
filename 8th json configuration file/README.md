# JSON Configuration Manager

A lightweight, robust configuration management library for Python. It loads configuration files from JSON, supports nested configuration path access using dot notation, resolves environment variables with optional defaults and type coercion, and validates configurations against JSON schemas.

## Features

- **Nested Key Access**: Retrieve and modify settings using dot-separated keys (e.g., `database.host`).
- **Environment Variable Interpolation**: Replace placeholders in the format `${VAR_NAME}` or `${VAR_NAME:default_value}`.
- **Smart Type Coercion**: Automatically converts isolated env var values to `int`, `float`, `bool`, or `None` during resolution.
- **Deep Configuration Merging**: Load multiple files sequentially to merge default settings and environment-specific overrides.
- **Schema Validation**: Validate your configurations against standard JSON schemas or simple direct mapping schemas.

## Installation & Setup

1. Make sure you are using Python 3.14+ (or any modern Python 3.x version).
2. Activate your virtual environment and run the test suite:
   ```bash
   # Activate virtual environment
   source .venv/bin/activate

   # Run tests
   pytest test_app.py -v
   ```

## Detailed Usage

### 1. Basic Usage (Get and Set)

You can set values at flat or nested paths, and retrieve them:

```python
from app import config

# Set flat and nested values
config.set("app_name", "my-app")
config.set("database.host", "localhost")
config.set("database.port", 5432)

# Get values
app_name = config.get("app_name")               # Returns "my-app"
db_port = config.get("database.port")           # Returns 5432
db_ssl = config.get("database.ssl", True)       # Returns True (default fallback)

# Get entire configuration object
entire_config = config.get("")                  # Returns {"app_name": "my-app", "database": {"host": "localhost", "port": 5432}}
```

### 2. Loading Files and Environment Interpolation

Assuming a file `config.json` containing:

```json
{
  "database": {
    "host": "${DB_HOST:localhost}",
    "port": "${DB_PORT}",
    "name": "myapp_${NODE_ENV}"
  }
}
```

You can load and interpolate it:

```python
import os
from app import config

# Set required environment variables
os.environ["DB_PORT"] = "5432"
os.environ["NODE_ENV"] = "production"

# DB_HOST is not set, so it will fall back to the default "localhost"
config.load("config.json")

print(config.get("database.host"))  # "localhost" (coerced fallback default)
print(config.get("database.port"))  # 5432 (coerced to integer)
print(config.get("database.name"))  # "myapp_production" (inline substitution)
```

### 3. Sequential Loading (Deep Merging)

If you load multiple configuration files, they will be recursively merged:

```python
# default_config.json -> {"server": {"port": 8080, "host": "0.0.0.0"}}
# prod_config.json    -> {"server": {"port": 80}}

config.load("default_config.json")
config.load("prod_config.json")

print(config.get("server.port"))  # 80 (overwritten)
print(config.get("server.host"))  # "0.0.0.0" (preserved)
```

### 4. Schema Validation

Verify that your loaded configurations are correct and safe:

```python
from app import config, ValidationError

schema = {
    "type": "object",
    "required": ["database"],
    "properties": {
        "database": {
            "type": "object",
            "required": ["host", "port"],
            "properties": {
                "host": {"type": "string", "min_length": 3},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535}
            }
        }
    }
}

try:
    config.validate(schema)
    print("Configuration is valid!")
except ValidationError as e:
    print("Invalid Configuration:")
    for error in e.errors:
        print(error)
```
