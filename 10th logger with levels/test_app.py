import json
import os
import sys
import tempfile
import threading
import time
from typing import Generator
import pytest
from app import (
    ConsoleTransport,
    FileTransport,
    Formatter,
    JSONFormatter,
    Logger,
    LogLevel,
    PrettyFormatter,
)


@pytest.fixture
def temp_log_file() -> Generator[str, None, None]:
    """Provides a temporary file path for testing FileTransport and deletes it after."""
    fd, path = tempfile.mkstemp(suffix=".log")
    os.close(fd)
    yield path
    # Clean up files created during rotation
    for suffix in ["", ".1", ".2", ".3"]:
        p = f"{path}{suffix}"
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


# ---- Log Level Tests ----


class TestLogLevels:

    def test_log_level_values(self):
        assert LogLevel.DEBUG == 10
        assert LogLevel.INFO == 20
        assert LogLevel.WARN == 30
        assert LogLevel.ERROR == 40

    def test_get_value(self):
        assert LogLevel.get_value('DEBUG') == 10
        assert LogLevel.get_value('info') == 20
        assert LogLevel.get_value('WARN') == 30
        assert LogLevel.get_value('warning') == 30
        assert LogLevel.get_value('ERROR') == 40
        assert LogLevel.get_value(30) == 30

        with pytest.raises(ValueError):
            LogLevel.get_value('INVALID')


# ---- Formatter Tests ----


class TestFormatters:

    def test_pretty_formatter(self):
        formatter = PrettyFormatter()
        from datetime import datetime
        now = datetime(2026, 7, 15, 8, 30, 0, 123456)
        record = {
            'timestamp': now,
            'level': 'INFO',
            'message': 'Hello world',
            'metadata': {'user_id': 42},
        }
        result = formatter.format(record)
        assert result.startswith("[2026-07-15 08:30:00.123] [INFO] Hello world")
        assert '{"user_id": 42}' in result

        # Test no metadata
        record_no_meta = {
            'timestamp': now,
            'level': 'WARN',
            'message': 'Warning alert',
            'metadata': None,
        }
        result_no_meta = formatter.format(record_no_meta)
        assert result_no_meta == "[2026-07-15 08:30:00.123] [WARN] Warning alert"

    def test_json_formatter(self):
        formatter = JSONFormatter()
        from datetime import datetime
        now = datetime(2026, 7, 15, 8, 30, 0, 123456)
        record = {
            'timestamp': now,
            'level': 'ERROR',
            'message': 'Database connection failed',
            'metadata': {'db_host': 'localhost'},
        }
        result = formatter.format(record)
        data = json.loads(result)
        assert data['timestamp'] == now.isoformat()
        assert data['level'] == 'ERROR'
        assert data['message'] == 'Database connection failed'
        assert data['metadata'] == {'db_host': 'localhost'}


# ---- Mock/Memory Transport for verification ----


class MemoryTransport:
    """A transport that records log records in memory for assertions."""

    def __init__(self, formatter=None):
        self.formatter = formatter or PrettyFormatter()
        self.records = []
        self.formatted_records = []

    def emit(self, record):
        self.records.append(record)
        self.formatted_records.append(self.formatter.format(record))


# ---- Logger Tests ----


class TestLogger:

    def test_logger_respects_minimum_level(self):
        transport = MemoryTransport()
        logger = Logger(level='INFO', transports=[transport])

        logger.debug("Debug msg")  # Ignored
        logger.info("Info msg")  # Logged
        logger.warn("Warn msg")  # Logged
        logger.error("Error msg")  # Logged

        assert len(transport.records) == 3
        assert transport.records[0]['message'] == "Info msg"
        assert transport.records[1]['message'] == "Warn msg"
        assert transport.records[2]['message'] == "Error msg"

    def test_logger_set_level_runtime(self):
        transport = MemoryTransport()
        logger = Logger(level='ERROR', transports=[transport])

        logger.info("Info msg")  # Ignored
        assert len(transport.records) == 0

        logger.setLevel('INFO')
        logger.info("Info msg")  # Logged now
        assert len(transport.records) == 1

        # Check support for snake_case alias
        logger.set_level('DEBUG')
        logger.debug("Debug msg")  # Logged now
        assert len(transport.records) == 2

    def test_add_and_clear_transports(self):
        logger = Logger(level='DEBUG')
        t1 = MemoryTransport()
        t2 = MemoryTransport()

        logger.addTransport(t1)
        logger.add_transport(t2)  # Check support for snake_case alias
        assert len(logger.getTransports()) == 2
        assert len(logger.get_transports()) == 2

        logger.debug("Message")
        assert len(t1.records) == 1
        assert len(t2.records) == 1

        logger.clearTransports()
        assert len(logger.getTransports()) == 0

        # Check support for snake_case alias
        logger.add_transport(t1)
        logger.clear_transports()
        assert len(logger.get_transports()) == 0


# ---- Console Transport Tests ----


class TestConsoleTransport:

    def test_console_transport_routing(self, capsys):
        # We test that ConsoleTransport routes ERROR to stderr and other levels to stdout
        t = ConsoleTransport()
        from datetime import datetime
        now = datetime.now()

        t.emit({
            'timestamp': now,
            'level': 'INFO',
            'message': 'Stdout log',
            'metadata': None
        })
        captured = capsys.readouterr()
        assert "Stdout log" in captured.out
        assert captured.err == ""

        t.emit({
            'timestamp': now,
            'level': 'ERROR',
            'message': 'Stderr log',
            'metadata': None
        })
        captured = capsys.readouterr()
        assert "Stderr log" in captured.err
        assert captured.out == ""


# ---- File Transport Tests ----


class TestFileTransport:

    def test_file_transport_writes_to_file(self, temp_log_file):
        formatter = JSONFormatter()
        transport = FileTransport(temp_log_file, formatter=formatter)

        logger = Logger(level='DEBUG', transports=[transport])
        logger.info("Log to file", {"a": 1})

        with open(temp_log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        assert len(lines) == 1
        data = json.loads(lines[0].strip())
        assert data['message'] == "Log to file"
        assert data['metadata'] == {"a": 1}

    def test_file_rotation_by_bytes(self, temp_log_file):
        # We specify a small max_bytes and a backup_count of 2.
        # Format returns exact bytes we control.
        class FixedLengthFormatter(Formatter):
            def format(self, record):
                # Always returns exactly 10 characters
                return record['message'][:10].ljust(10)

        # max_bytes = 20, backup_count = 2
        # Since each record is formatted to 10 chars + 1 newline = 11 bytes,
        # 1st write: 11 bytes (fits, total file size = 11)
        # 2nd write: 11 bytes (total size 22 > 20, triggers rotation.
        #   Old file becomes log.1. New file contains record 2 (size = 11))
        # 3rd write: 11 bytes (total size 22 > 20, triggers rotation.
        #   Old log.1 becomes log.2, old primary becomes log.1, new file contains record 3 (size = 11))
        transport = FileTransport(
            temp_log_file,
            formatter=FixedLengthFormatter(),
            max_bytes=20,
            backup_count=2
        )

        # Write first line
        transport.emit({'message': '1234567890'})  # 10 chars + \n = 11 bytes
        assert os.path.exists(temp_log_file)
        with open(temp_log_file, 'r') as f:
            assert f.read() == "1234567890\n"

        # Write second line (will cause rotation)
        transport.emit({'message': 'abcdefghij'})
        # Now temp_log_file should contain 'abcdefghij\n', and temp_log_file.1 should contain '1234567890\n'
        assert os.path.exists(temp_log_file)
        assert os.path.exists(f"{temp_log_file}.1")
        with open(temp_log_file, 'r') as f:
            assert f.read() == "abcdefghij\n"
        with open(f"{temp_log_file}.1", 'r') as f:
            assert f.read() == "1234567890\n"

        # Write third line (will cause rotation again)
        transport.emit({'message': 'xyz_abc_de'})
        # temp_log_file -> 'xyz_abc_de\n'
        # temp_log_file.1 -> 'abcdefghij\n'
        # temp_log_file.2 -> '1234567890\n'
        assert os.path.exists(temp_log_file)
        assert os.path.exists(f"{temp_log_file}.1")
        assert os.path.exists(f"{temp_log_file}.2")

        with open(temp_log_file, 'r') as f:
            assert f.read() == "xyz_abc_de\n"
        with open(f"{temp_log_file}.1", 'r') as f:
            assert f.read() == "abcdefghij\n"
        with open(f"{temp_log_file}.2", 'r') as f:
            assert f.read() == "1234567890\n"

        # Write fourth line (will cause rotation, temp_log_file.2 gets replaced, temp_log_file.3 doesn't exist since backup_count = 2)
        transport.emit({'message': 'final_line'})
        assert not os.path.exists(f"{temp_log_file}.3")
        with open(temp_log_file, 'r') as f:
            assert f.read() == "final_line\n"
        with open(f"{temp_log_file}.1", 'r') as f:
            assert f.read() == "xyz_abc_de\n"
        with open(f"{temp_log_file}.2", 'r') as f:
            assert f.read() == "abcdefghij\n"


# ---- Thread Safety / Concurrency Test ----


class TestConcurrency:

    def test_concurrent_logging(self, temp_log_file):
        # Multiple threads write to the same FileTransport log file.
        # We check that there are no write/race crashes and all messages are correctly recorded.
        transport = FileTransport(temp_log_file, formatter=JSONFormatter())
        logger = Logger(level='DEBUG', transports=[transport])

        num_threads = 5
        writes_per_thread = 50
        errors = []

        def worker(thread_id):
            try:
                for i in range(writes_per_thread):
                    logger.info("Log message", {"thread": thread_id, "index": i})
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"

        # Read back all lines from log file
        with open(temp_log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        assert len(lines) == num_threads * writes_per_thread

        # Parse and verify each line
        logged_entries = []
        for line in lines:
            data = json.loads(line.strip())
            assert data['message'] == "Log message"
            logged_entries.append(data['metadata'])

        # Verify we have all entries from all threads
        for thread_id in range(num_threads):
            thread_entries = [e for e in logged_entries if e['thread'] == thread_id]
            assert len(thread_entries) == writes_per_thread
            indices = [e['index'] for e in thread_entries]
            assert sorted(indices) == list(range(writes_per_thread))
