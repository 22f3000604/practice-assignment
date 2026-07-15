import asyncio
import threading
import time
from typing import List
import pytest
from app import EventEmitter, match_event


# ---- Wildcard Matcher Tests ----


def test_wildcard_matching():
    # Exact matches
    assert match_event("user.created", "user.created") is True
    assert match_event("user.created", "user.deleted") is False

    # Single segment wildcards
    assert match_event("user.*", "user.created") is True
    assert match_event("user.*", "user.deleted") is True
    assert match_event("user.*", "user.created.details") is False
    assert match_event("*.created", "user.created") is True
    assert match_event("*.created", "admin.created") is True

    # Multi-segment/Recursive wildcards
    assert match_event("user.**", "user.created") is True
    assert match_event("user.**", "user.created.details") is True
    assert match_event("user.**", "admin.created") is False
    assert match_event("**", "user.created.details") is True

    # Wildcards in emitted events
    assert match_event("user.created", "user.*") is True
    assert match_event("user.created.details", "user.**") is True


# ---- Basic Pub/Sub Tests ----


class TestBasicPubSub:

    def test_register_and_emit(self):
        emitter = EventEmitter()
        calls = []

        def handler(data):
            calls.append(data)

        emitter.on("test.event", handler)
        results = emitter.emit("test.event", "payload")

        assert calls == ["payload"]
        assert results == [None]  # handler returns None

    def test_unregister(self):
        emitter = EventEmitter()
        calls = []

        def handler(data):
            calls.append(data)

        emitter.on("test.event", handler)
        emitter.emit("test.event", 1)
        assert len(calls) == 1

        emitter.off("test.event", handler)
        emitter.emit("test.event", 2)
        assert len(calls) == 1  # No additional calls

    def test_multiple_listeners(self):
        emitter = EventEmitter()
        calls = []

        h1 = lambda x: calls.append(f"h1:{x}")
        h2 = lambda x: calls.append(f"h2:{x}")

        emitter.on("event", h1)
        emitter.on("event", h2)

        emitter.emit("event", "data")
        assert calls == ["h1:data", "h2:data"]

    def test_remove_all_listeners(self):
        emitter = EventEmitter()
        calls = []

        h = lambda x: calls.append(x)
        emitter.on("e1", h)
        emitter.on("e2", h)

        emitter.remove_all_listeners("e1")
        emitter.emit("e1", 1)
        emitter.emit("e2", 2)

        assert calls == [2]

        emitter.remove_all_listeners()
        emitter.emit("e2", 3)
        assert calls == [2]  # No additional calls


# ---- One-Time Listener Tests ----


class TestOnceListener:

    def test_once_execution(self):
        emitter = EventEmitter()
        calls = []

        def handler(data):
            calls.append(data)

        emitter.once("test.once", handler)
        emitter.emit("test.once", "first")
        emitter.emit("test.once", "second")

        assert calls == ["first"]

    def test_once_unregister_before_use(self):
        emitter = EventEmitter()
        calls = []

        def handler(data):
            calls.append(data)

        emitter.once("test.once", handler)
        emitter.off("test.once", handler)
        emitter.emit("test.once", "first")

        assert len(calls) == 0


# ---- Wildcard Emission Tests ----


class TestWildcardEmission:

    def test_wildcard_listener_triggered(self):
        emitter = EventEmitter()
        calls = []

        emitter.on("user.*", lambda data: calls.append(data))
        emitter.emit("user.created", "alice")
        emitter.emit("user.deleted", "bob")
        emitter.emit("admin.created", "charlie")  # shouldn't match

        assert calls == ["alice", "bob"]

    def test_wildcard_emission_triggers_exact_listener(self):
        emitter = EventEmitter()
        calls = []

        emitter.on("user.created", lambda data: calls.append(f"created:{data}"))
        emitter.on("user.deleted", lambda data: calls.append(f"deleted:{data}"))

        emitter.emit("user.*", "data")
        assert sorted(calls) == ["created:data", "deleted:data"]


# ---- Async Handler Tests ----


@pytest.mark.asyncio
async def test_async_handler_aemit():
    emitter = EventEmitter()
    calls = []

    async def async_handler(data):
        await asyncio.sleep(0.01)
        calls.append(f"async:{data}")
        return "async_res"

    def sync_handler(data):
        calls.append(f"sync:{data}")
        return "sync_res"

    emitter.on("event", async_handler)
    emitter.on("event", sync_handler)

    # Use aemit to await all async handlers concurrently
    results = await emitter.aemit("event", "test")

    assert "sync:test" in calls
    assert "async:test" in calls
    assert len(calls) == 2
    assert sorted(results) == sorted(["sync_res", "async_res"])


@pytest.mark.asyncio
async def test_async_handler_emit_running_loop():
    emitter = EventEmitter()
    calls = []

    async def async_handler(data):
        await asyncio.sleep(0.01)
        calls.append(data)

    emitter.on("event", async_handler)

    # emit() schedules in background if loop is running
    results = emitter.emit("event", "run")
    assert len(results) == 1
    assert isinstance(results[0], asyncio.Task)

    # Wait for the task to finish
    await results[0]
    assert calls == ["run"]


# ---- Error Handling Tests ----


class TestErrorHandling:

    def test_handler_error_suppression(self):
        emitter = EventEmitter(suppress_errors=True)
        calls = []

        def bad_handler(data):
            raise ValueError("Failure!")

        def good_handler(data):
            calls.append(data)

        emitter.on("event", bad_handler)
        emitter.on("event", good_handler)

        # Should not raise exception
        results = emitter.emit("event", "success")
        assert calls == ["success"]

    def test_handler_error_raising(self):
        emitter = EventEmitter(suppress_errors=False)

        def bad_handler(data):
            raise ValueError("Failure!")

        emitter.on("event", bad_handler)

        with pytest.raises(ValueError, match="Failure!"):
            emitter.emit("event", "test")

    def test_error_event_routing(self, capsys):
        emitter = EventEmitter()
        errors_received = []

        def bad_handler(data):
            raise ValueError("Failure!")

        def error_listener(err):
            errors_received.append(err)

        emitter.on("event", bad_handler)
        emitter.on("error", error_listener)

        emitter.emit("event", "test")
        
        assert len(errors_received) == 1
        assert isinstance(errors_received[0], ValueError)
        assert str(errors_received[0]) == "Failure!"

        # Stderr should be clean because the error was routed
        captured = capsys.readouterr()
        assert "Unhandled exception" not in captured.err


# ---- Concurrency / Thread Safety Tests ----


class TestConcurrency:

    def test_concurrent_registrations_and_emissions(self):
        emitter = EventEmitter()
        num_threads = 10
        ops_per_thread = 100
        errors = []

        def worker(thread_idx):
            try:
                for i in range(ops_per_thread):
                    event = f"thread_{thread_idx}.event_{i}"
                    
                    # Define handler
                    h = lambda x: None
                    
                    # Register
                    emitter.on(event, h)
                    
                    # Emit
                    emitter.emit(event, "payload")
                    
                    # Unregister
                    emitter.off(event, h)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrency errors encountered: {errors}"
