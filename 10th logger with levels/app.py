import json
import os
import sys
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


class LogLevel:
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40

    _name_to_val = {
        'DEBUG': DEBUG,
        'INFO': INFO,
        'WARN': WARN,
        'WARNING': WARN,
        'ERROR': ERROR,
    }

    _val_to_name = {
        DEBUG: 'DEBUG',
        INFO: 'INFO',
        WARN: 'WARN',
        ERROR: 'ERROR',
    }

    @classmethod
    def get_value(cls, name_or_val: Union[int, str]) -> int:
        if isinstance(name_or_val, int):
            return name_or_val
        if isinstance(name_or_val, str):
            name_upper = name_or_val.upper()
            if name_upper in cls._name_to_val:
                return cls._name_to_val[name_upper]
        raise ValueError(f"Invalid log level: {name_or_val}")


class Formatter:
    """Base formatter interface."""

    def format(self, record: Dict[str, Any]) -> str:
        raise NotImplementedError


class PrettyFormatter(Formatter):
    """Formats log records in a human-readable text line."""

    def format(self, record: Dict[str, Any]) -> str:
        # record contains: timestamp (datetime), level (str), message (str), metadata (dict or None)
        ts = record['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        level = record['level']
        msg = record['message']
        meta = record.get('metadata')

        meta_str = f" {json.dumps(meta)}" if meta else ""
        return f"[{ts}] [{level}] {msg}{meta_str}"


class JSONFormatter(Formatter):
    """Formats log records into a JSON string."""

    def format(self, record: Dict[str, Any]) -> str:
        data = {
            'timestamp': record['timestamp'].isoformat(),
            'level': record['level'],
            'message': record['message'],
        }
        if record.get('metadata') is not None:
            data['metadata'] = record['metadata']
        return json.dumps(data)


class Transport:
    """Base transport interface."""

    def __init__(self, formatter: Optional[Formatter] = None) -> None:
        self.formatter = formatter or PrettyFormatter()

    def emit(self, record: Dict[str, Any]) -> None:
        raise NotImplementedError


class ConsoleTransport(Transport):
    """Emits log records to stdout or stderr."""

    def emit(self, record: Dict[str, Any]) -> None:
        formatted = self.formatter.format(record)
        # Write to stderr for ERROR, stdout otherwise
        if record['level'] == 'ERROR':
            sys.stderr.write(formatted + '\n')
            sys.stderr.flush()
        else:
            sys.stdout.write(formatted + '\n')
            sys.stdout.flush()


class FileTransport(Transport):
    """Emits log records to a file, with optional size-based rotation."""

    def __init__(
        self,
        filepath: str,
        formatter: Optional[Formatter] = None,
        max_bytes: Optional[int] = None,
        backup_count: int = 0,
    ) -> None:
        super().__init__(formatter)
        self.filepath = os.path.abspath(filepath)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._lock = threading.Lock()

        # Ensure directory exists
        dir_name = os.path.dirname(self.filepath)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    def emit(self, record: Dict[str, Any]) -> None:
        formatted = self.formatter.format(record) + '\n'
        with self._lock:
            self._write_to_file(formatted)

    def _write_to_file(self, content: str) -> None:
        # Check size and rotate if necessary before writing
        if self.max_bytes is not None and self.max_bytes > 0:
            if os.path.exists(self.filepath):
                try:
                    size = os.path.getsize(self.filepath)
                except OSError:
                    size = 0
                if size + len(content.encode('utf-8')) > self.max_bytes:
                    self._rotate_files()

        # Write to file
        try:
            with open(self.filepath, 'a', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            sys.stderr.write(f"Failed to write log to {self.filepath}: {e}\n")
            sys.stderr.flush()

    def _rotate_files(self) -> None:
        if self.backup_count > 0:
            # Remove oldest backup file
            oldest_backup = f"{self.filepath}.{self.backup_count}"
            if os.path.exists(oldest_backup):
                try:
                    os.remove(oldest_backup)
                except OSError:
                    pass

            # Shift names of existing backup files: e.g. log.1 -> log.2, log.2 -> log.3
            for i in range(self.backup_count - 1, 0, -1):
                src = f"{self.filepath}.{i}"
                dest = f"{self.filepath}.{i+1}"
                if os.path.exists(src):
                    try:
                        os.rename(src, dest)
                    except OSError:
                        pass

            # Rename current file to log.1
            if os.path.exists(self.filepath):
                try:
                    os.rename(self.filepath, f"{self.filepath}.1")
                except OSError:
                    pass
        else:
            # If backup_count is 0, we simply delete/truncate the file
            if os.path.exists(self.filepath):
                try:
                    os.remove(self.filepath)
                except OSError:
                    pass


class Logger:
    """Thread-safe logger class supporting multiple transports and configurable log level."""

    def __init__(
        self,
        level: Union[int, str] = 'INFO',
        transports: Optional[List[Transport]] = None,
    ) -> None:
        self._lock = threading.Lock()
        self._level = LogLevel.get_value(level)
        self._transports = transports or []

    def setLevel(self, level: Union[int, str]) -> None:
        with self._lock:
            self._level = LogLevel.get_value(level)

    def set_level(self, level: Union[int, str]) -> None:
        self.setLevel(level)

    def addTransport(self, transport: Transport) -> None:
        with self._lock:
            self._transports.append(transport)

    def add_transport(self, transport: Transport) -> None:
        self.addTransport(transport)

    def clearTransports(self) -> None:
        with self._lock:
            self._transports.clear()

    def clear_transports(self) -> None:
        self.clearTransports()

    def getTransports(self) -> List[Transport]:
        with self._lock:
            return list(self._transports)

    def get_transports(self) -> List[Transport]:
        return self.getTransports()

    def log(
        self,
        level: Union[int, str],
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        level_val = LogLevel.get_value(level)
        with self._lock:
            if level_val < self._level:
                return

            record = {
                'timestamp': datetime.now(),
                'level': LogLevel._val_to_name.get(level_val, str(level)),
                'message': str(message),
                'metadata': metadata,
            }

            for transport in self._transports:
                try:
                    transport.emit(record)
                except Exception as e:
                    sys.stderr.write(f"Error in logger transport emit: {e}\n")
                    sys.stderr.flush()

    def debug(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.log('DEBUG', message, metadata)

    def info(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.log('INFO', message, metadata)

    def warn(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.log('WARN', message, metadata)

    def warning(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.log('WARN', message, metadata)

    def error(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.log('ERROR', message, metadata)


# Export default instance
logger = Logger(level='INFO', transports=[ConsoleTransport()])
