import asyncio
import inspect
import sys
import threading
import traceback
from typing import Any, Callable, Dict, List, Tuple, Union


# Fallback for Python versions < 3.11 without ExceptionGroup
try:
    ActiveExceptionGroup = ExceptionGroup
except NameError:
    class ActiveExceptionGroup(Exception):  # type: ignore
        def __init__(self, message: str, exceptions: List[Exception]) -> None:
            super().__init__(message)
            self.exceptions = exceptions


def match_segments(p1: List[str], p2: List[str]) -> bool:
    """Recursively checks if two list of segments match, supporting wildcards."""
    if not p1 and not p2:
        return True

    if p1 and p1[0] == '**':
        # '**' matches zero or more segments
        for i in range(len(p2) + 1):
            if match_segments(p1[1:], p2[i:]):
                return True
        return False

    if p2 and p2[0] == '**':
        # '**' matches zero or more segments
        for i in range(len(p1) + 1):
            if match_segments(p1[i:], p2[1:]):
                return True
        return False

    if not p1 or not p2:
        return False

    s1, s2 = p1[0], p2[0]
    if s1 == '*' or s2 == '*' or s1 == s2:
        return match_segments(p1[1:], p2[1:])

    return False


def match_event(pattern1: str, pattern2: str) -> bool:
    """
    Returns True if pattern1 matches pattern2.
    Supports '*' for single segment and '**' for zero or more segments.
    """
    if pattern1 == pattern2:
        return True
    return match_segments(pattern1.split('.'), pattern2.split('.'))


def is_async_callable(obj: Any) -> bool:
    """Helper to detect if a callable is an async function or has an async __call__."""
    if inspect.iscoroutinefunction(obj):
        return True
    if hasattr(obj, '__call__') and inspect.iscoroutinefunction(obj.__call__):
        return True
    return False


class Listener:
    """Internal wrapper for registered event listeners."""

    def __init__(self, handler: Callable[..., Any], once: bool = False) -> None:
        self.handler = handler
        self.once = once


class EventEmitter:
    """
    A thread-safe publish-subscribe Event Emitter.
    Supports synchronous and asynchronous handlers, one-time listeners,
    wildcards, and customizable error recovery.
    """

    def __init__(self, suppress_errors: bool = True) -> None:
        self._lock = threading.RLock()
        self._listeners: Dict[str, List[Listener]] = {}
        self.suppress_errors = suppress_errors

    def on(self, event: str, handler: Callable[..., Any]) -> None:
        """Registers a listener for a given event pattern."""
        if not event or not isinstance(event, str):
            raise ValueError("Event name must be a non-empty string.")
        if not callable(handler):
            raise ValueError("Handler must be a callable object.")

        with self._lock:
            if event not in self._listeners:
                self._listeners[event] = []
            self._listeners[event].append(Listener(handler, once=False))

    def add_listener(self, event: str, handler: Callable[..., Any]) -> None:
        """PEP 8 alias for on."""
        self.on(event, handler)

    def once(self, event: str, handler: Callable[..., Any]) -> None:
        """Registers a one-time listener that is removed after the first trigger."""
        if not event or not isinstance(event, str):
            raise ValueError("Event name must be a non-empty string.")
        if not callable(handler):
            raise ValueError("Handler must be a callable object.")

        with self._lock:
            if event not in self._listeners:
                self._listeners[event] = []
            self._listeners[event].append(Listener(handler, once=True))

    def off(self, event: str, handler: Callable[..., Any]) -> None:
        """Removes a registered listener for a given event pattern."""
        if not event or not isinstance(event, str):
            raise ValueError("Event name must be a non-empty string.")
        if not callable(handler):
            raise ValueError("Handler must be a callable object.")

        with self._lock:
            if event in self._listeners:
                self._listeners[event] = [
                    l for l in self._listeners[event] if l.handler != handler
                ]
                if not self._listeners[event]:
                    del self._listeners[event]

    def remove_listener(self, event: str, handler: Callable[..., Any]) -> None:
        """PEP 8 alias for off."""
        self.off(event, handler)

    def remove_all_listeners(self, event: Optional[str] = None) -> None:
        """Removes all listeners, optionally filtered by a specific event pattern."""
        with self._lock:
            if event is None:
                self._listeners.clear()
            elif event in self._listeners:
                del self._listeners[event]

    def _get_and_cleanup_listeners(self, emitted_event: str) -> List[Listener]:
        """Retrieves matching listeners and purges those marked as once."""
        matching: List[Listener] = []
        with self._lock:
            for pattern, listeners in list(self._listeners.items()):
                if match_event(pattern, emitted_event):
                    remaining = []
                    for listener in listeners:
                        matching.append(listener)
                        if not listener.once:
                            remaining.append(listener)
                    if remaining:
                        self._listeners[pattern] = remaining
                    else:
                        del self._listeners[pattern]
        return matching

    def _handle_error(self, exc: Exception, original_event: str) -> None:
        """Handles exceptions in listeners by routing to error listeners or printing to stderr."""
        if original_event == 'error':
            sys.stderr.write(f"Unhandled error in 'error' event listener: {exc}\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
            sys.stderr.flush()
            return

        # Check if any listener matches the 'error' event pattern
        has_error_listener = False
        with self._lock:
            for pattern in self._listeners:
                if match_event(pattern, 'error'):
                    has_error_listener = True
                    break

        if has_error_listener:
            try:
                self.emit('error', exc)
            except Exception as emit_err:
                sys.stderr.write(f"Failed to emit 'error' event: {emit_err}\n")
                traceback.print_exception(type(emit_err), emit_err, emit_err.__traceback__, file=sys.stderr)
                sys.stderr.flush()
        else:
            sys.stderr.write(f"Unhandled exception in handler for event '{original_event}': {exc}\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
            sys.stderr.flush()

    def emit(self, event: str, data: Any = None) -> List[Any]:
        """
        Synchronously triggers listeners matching the event.
        Returns the results of sync handlers and scheduled task objects for async handlers.
        """
        if not event or not isinstance(event, str):
            raise ValueError("Event name must be a non-empty string.")

        listeners = self._get_and_cleanup_listeners(event)
        results = []
        errors = []

        for listener in listeners:
            handler = listener.handler
            try:
                if is_async_callable(handler):
                    coro = handler(data)
                    try:
                        # Schedule task in the running loop
                        loop = asyncio.get_running_loop()
                        if loop.is_running():
                            task = loop.create_task(coro)
                            results.append(task)
                        else:
                            results.append(coro)
                    except RuntimeError:
                        # No running loop, fallback: run synchronously (blocks) or return coro
                        try:
                            res = asyncio.run(coro)
                            results.append(res)
                        except Exception as ae:
                            errors.append(ae)
                            self._handle_error(ae, event)
                else:
                    res = handler(data)
                    results.append(res)
            except Exception as e:
                errors.append(e)
                self._handle_error(e, event)

        if errors and not self.suppress_errors:
            if len(errors) == 1:
                raise errors[0]
            raise ActiveExceptionGroup("Multiple errors occurred in event handlers", errors)

        return results

    async def aemit(self, event: str, data: Any = None) -> List[Any]:
        """
        Asynchronously triggers listeners matching the event.
        Executes sync handlers immediately and awaits async handlers concurrently.
        """
        if not event or not isinstance(event, str):
            raise ValueError("Event name must be a non-empty string.")

        listeners = self._get_and_cleanup_listeners(event)
        coros = []
        sync_results = []
        errors = []

        for listener in listeners:
            handler = listener.handler
            try:
                if is_async_callable(handler):
                    coros.append(handler(data))
                else:
                    sync_results.append(handler(data))
            except Exception as e:
                errors.append(e)
                self._handle_error(e, event)

        if coros:
            async_results = await asyncio.gather(*coros, return_exceptions=True)
            for res in async_results:
                if isinstance(res, Exception):
                    errors.append(res)
                    self._handle_error(res, event)
                else:
                    sync_results.append(res)

        if errors and not self.suppress_errors:
            if len(errors) == 1:
                raise errors[0]
            raise ActiveExceptionGroup("Multiple errors occurred in event handlers", errors)

        return sync_results
