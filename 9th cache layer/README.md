# Simple Cache Layer

A thread-safe, in-memory cache implementation in Python. It supports time-to-live (TTL) expiration, both lazy and active (background thread) eviction of expired entries, detailed hit/miss statistics, and standard Python dict syntax options.

## Features

- **TTL Expiration**: Expire cache entries after a configurable duration in seconds.
- **Double Eviction Strategy**:
  - **Lazy Eviction**: Items are checked and deleted when accessed (`get`, `has`, `ttl`).
  - **Active Eviction**: A background daemon thread periodically sweeps the cache to evict expired items and free up memory.
- **Detailed Cache Statistics**: Track total entries, hits, misses, and hit rate.
- **Thread-Safe**: Fully thread-safe operations using Reentrant Locks (`RLock`).
- **Pythonic Syntax**: Supports dictionary-like syntax (e.g. `del cache[key]`).
- **Keyword Workaround**: Safely exposes the `del` method dynamically to avoid Python syntax conflicts.

## Installation & Setup

1. Verify Python 3.x is installed.
2. Activate your virtual environment and run the test suite:
   ```bash
   # Activate virtual environment
   source .venv/bin/activate

   # Run tests
   pytest test_app.py -v
   ```

## Detailed Usage

### 1. Basic Operations

```python
from app import cache

# Set with an optional TTL (e.g., 300 seconds)
cache.set("session_id", "xyz123", ttl=300)

# Get the value
session = cache.get("session_id")  # Returns "xyz123"

# Check if a key exists and is valid (does not affect stats)
exists = cache.has("session_id")   # Returns True

# Delete a key
deleted = cache.delete("session_id")  # Returns True
```

### 2. Pythonic Dictionary Syntax

In addition to standard method calls, the cache supports native `del` syntax:

```python
from app import cache

cache.set("key", "value")

# Delete using Python's del keyword
del cache["key"]
```

### 3. Expiration and TTL Updates

You can view or update the TTL of an active key:

```python
from app import cache

# Set a key to expire in 5 seconds
cache.set("temp_token", "abc", ttl=5)

# Extend/update the TTL of the key to 600 seconds
success = cache.ttl("temp_token", 600)  # Returns True

# Make the key persistent (never expires)
cache.ttl("temp_token", None)
```

### 4. Cache Statistics

Monitor cache performance using the `stats()` method:

```python
from app import cache

cache.clear() # Clears entries and resets stats

# Perform operations
cache.set("k1", "v1")
cache.get("k1")       # Hit
cache.get("k2")       # Miss

# Retrieve statistics dictionary
stats = cache.stats()
print(stats)
# Output:
# {
#     "total_entries": 1,
#     "hits": 1,
#     "misses": 1,
#     "hit_rate": 0.5
# }
```

### 5. Cleaning Up Resources

To stop the background active cleanup thread when shutting down your application:

```python
from app import cache

# Stop background thread
cache.close()
```
