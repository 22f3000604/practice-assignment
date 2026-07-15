# Event Emitter System

A thread-safe, publish-subscribe event management library for Python. It supports one-time listeners, wildcard event patterns (single segment and multi-segment/recursive), concurrent asynchronous event handlers, and customizable error recovery.

## Features

- **Standard Pub/Sub**: Register listeners (`on`), unregister listeners (`off`), and broadcast events (`emit`).
- **One-time Listeners**: Support for `once` listeners that run exactly once and are immediately cleaned up.
- **Wildcard Matches**:
  - `*` matches a single dot-separated segment (e.g. `user.*` matches `user.created` but not `user.created.details`).
  - `**` matches zero or more segments recursively (e.g. `user.**` matches `user.created`, `user.created.details`, etc.).
  - Match is symmetric: Emitting a wildcard also triggers matching exact listeners.
- **Async Event Handlers**:
  - **Synchronous trigger (`emit`)**: Executes sync handlers immediately. If a running event loop is active, schedules async coroutines in the loop.
  - **Asynchronous trigger (`aemit`)**: Executes sync handlers immediately and awaits async handlers concurrently using `asyncio.gather`.
- **Robust Error Handling**:
  - Errors inside handlers do not interrupt the execution of other matching handlers.
  - If a handler throws an error, it is either forwarded to the `'error'` event listeners or logged to `sys.stderr` to prevent silent suppression.
  - Set `suppress_errors=False` on initialization to propagate handler exceptions to the caller.
- **Thread-safe**: Fully thread-safe operations guarded by reentrant locks (`RLock`).

## Installation & Setup

1. Verify Python 3.x is installed.
2. Initialize virtual environment, install requirements (`pytest`, `pytest-asyncio`), and run tests:
   ```bash
   # Set up virtual environment
   python3 -m venv .venv
   source .venv/bin/activate

   # Install test dependencies
   pip install pytest pytest-asyncio

   # Run tests
   pytest test_app.py -v
   ```

## Detailed Usage

### 1. Basic Operations

```python
from app import EventEmitter

emitter = EventEmitter()

def on_user_created(data):
    print(f"User created: {data}")

# Register listener
emitter.on('user.created', on_user_created)

# Emit event
emitter.emit('user.created', {'id': 100, 'name': 'Alice'})
# Output: User created: {'id': 100, 'name': 'Alice'}

# Remove listener
emitter.off('user.created', on_user_created)
```

### 2. One-time Listeners (`once`)

```python
emitter.once('app.startup', lambda data: print("App started!"))

emitter.emit('app.startup')  # Prints: "App started!"
emitter.emit('app.startup')  # Does nothing (listener was removed)
```

### 3. Wildcard Event Patterns

We support single-segment wildcards (`*`) and recursive wildcards (`**`):

```python
# Listeners can register with wildcards
emitter.on('logs.*', lambda msg: print(f"Log: {msg}"))
emitter.on('analytics.**', lambda data: print(f"Metric: {data}"))

emitter.emit('logs.info', 'Normal log')          # Matches logs.* -> Triggered
emitter.emit('logs.error.fatal', 'Crash')        # Does not match logs.* (multiple levels)

emitter.emit('analytics.page.load', '120ms')     # Matches analytics.** -> Triggered
emitter.emit('analytics.click', 'btn_login')     # Matches analytics.** -> Triggered

# Emitted events can also contain wildcards to trigger exact listeners
emitter.on('auth.login', lambda user: print(f"{user} logged in"))
emitter.on('auth.logout', lambda user: print(f"{user} logged out"))

emitter.emit('auth.*', 'Guest')
# Triggers both auth.login and auth.logout!
```

### 4. Async Handlers and Concurrency

Async handlers can be run synchronously via background scheduling (`emit`) or awaited asynchronously (`aemit`):

```python
import asyncio
from app import EventEmitter

emitter = EventEmitter()

async def fetch_user_avatar(userId):
    await asyncio.sleep(1)
    print(f"Avatar fetched for {userId}")

emitter.on('user.login', fetch_user_avatar)

# 1. Asynchronous execution - Await all handlers concurrently
async def main():
    await emitter.aemit('user.login', 123)

asyncio.run(main())
```
