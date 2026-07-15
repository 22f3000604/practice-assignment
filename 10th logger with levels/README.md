# Logger with Levels

A robust, thread-safe logging library for Python supporting multiple log levels, configurable minimum log levels, multiple transports (console, file), output formatting (pretty print vs structured JSON), and size-based file rotation.

## Features

- **Log Levels**: Support for `DEBUG`, `INFO`, `WARN` (or `WARNING`), and `ERROR`.
- **Configurable Minimum Level**: Filter out less critical logs at runtime using `setLevel()`.
- **Multiple Transports**: Direct logs to the Console (`ConsoleTransport`), Files (`FileTransport`), or custom memory/external destinations.
- **Format Options**:
  - **Pretty Print**: Formatted human-readable output, ideal for local development console viewing.
  - **JSON**: Structured JSON output including timestamp, level, message, and metadata, ideal for indexing and query systems.
- **File Rotation**: Automatically rotate logs when they exceed a configurable byte threshold (`max_bytes`), retaining a designated number of backup files (`backup_count`).
- **Thread-Safe**: Fully thread-safe operations protected by reentrant and mutex locks.
- **PEP 8 & Prompt Compatibility**: Supports both camelCase and snake_case for methods (e.g. `setLevel` / `set_level`, `addTransport` / `add_transport`).

## Installation & Setup

1. Verify Python 3.x is installed.
2. Initialize virtual environment, install `pytest`, and run tests:
   ```bash
   # Set up virtual environment
   python3 -m venv .venv
   source .venv/bin/activate

   # Install pytest
   pip install pytest

   # Run tests
   pytest test_app.py -v
   ```

## Detailed Usage

### 1. Basic Log Level Configurations

```python
from app import logger

# Set configurable minimum log level
logger.setLevel('INFO')

# Logging at different levels
logger.debug('Query executed', {'sql': 'SELECT * FROM users'})  # Ignored (below INFO)
logger.info('User logged in', {'userId': 123})                  # Logged
logger.warn('Rate limit warning', {'ip': '192.168.1.1'})        # Logged
logger.error('Database connection failed', {'error': 'timeout'}) # Logged
```

### 2. Output Formatting (Pretty vs JSON)

Formatters can be specified when initializing transports:

```python
from app import Logger, ConsoleTransport, PrettyFormatter, JSONFormatter

# 1. Human-friendly Pretty printing (Default)
pretty_transport = ConsoleTransport(formatter=PrettyFormatter())
pretty_logger = Logger(level='DEBUG', transports=[pretty_transport])
pretty_logger.info('System startup successful')
# Output: [2026-07-15 08:30:00.123] [INFO] System startup successful

# 2. Machine-friendly JSON printing
json_transport = ConsoleTransport(formatter=JSONFormatter())
json_logger = Logger(level='DEBUG', transports=[json_transport])
json_logger.info('Processing file', {'filename': 'data.csv'})
# Output: {"timestamp": "2026-07-15T08:30:00.123456", "level": "INFO", "message": "Processing file", "metadata": {"filename": "data.csv"}}
```

### 3. File Transport and Rotation

Configure log rotation to automatically split files when they grow too large:

```python
from app import Logger, FileTransport, JSONFormatter

# Configure FileTransport: max size 1MB (1,000,000 bytes) keeping 3 backups
file_transport = FileTransport(
    filepath='logs/app.log',
    formatter=JSONFormatter(),
    max_bytes=1000000,
    backup_count=3
)

logger = Logger(level='INFO', transports=[file_transport])
logger.info('Structured log to file')
# If app.log exceeds 1MB, it will rotate:
# app.log -> app.log.1 -> app.log.2 -> app.log.3
```
