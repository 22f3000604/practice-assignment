import threading
import time
from typing import Any, Dict, Optional, Tuple

class CacheEntry:
    """Represents an entry in the cache with a value and an expiration time."""

    def __init__(self, value: Any, expires_at: Optional[float]) -> None:
        self.value = value
        self.expires_at = expires_at  # Absolute epoch timestamp, or None for no expiration

    def is_expired(self, current_time: float) -> bool:
        """Check if the cache entry has expired."""
        if self.expires_at is None:
            return False
        return current_time >= self.expires_at


class SimpleCache:
    """A thread-safe, in-memory cache with lazy and active TTL expiration and performance stats."""

    def __init__(self, cleanup_interval: float = 1.0) -> None:
        """
        Initializes the SimpleCache.
        
        Args:
            cleanup_interval: The interval in seconds at which the background thread cleans up expired entries.
        """
        self._lock = threading.RLock()
        self._cache: Dict[str, CacheEntry] = {}
        
        # Stats
        self._hits = 0
        self._misses = 0

        # Background active cleanup thread
        self._cleanup_interval = cleanup_interval
        self._stop_cleanup = threading.Event()
        self._cleanup_thread = threading.Thread(
            target=self._active_cleanup_loop, 
            name="SimpleCache-CleanupThread",
            daemon=True
        )
        self._cleanup_thread.start()

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Sets a key in the cache with an optional TTL (in seconds).
        If TTL is provided, the key will expire after the TTL duration.
        """
        with self._lock:
            expires_at = time.time() + ttl if ttl is not None else None
            self._cache[key] = CacheEntry(value, expires_at)

    def get(self, key: str) -> Any:
        """
        Gets a key's value from the cache.
        If the key is present and not expired, increments hit statistics and returns the value.
        If the key is expired, deletes the key from the cache, increments miss statistics, and returns None.
        If the key is not present, increments miss statistics and returns None.
        """
        with self._lock:
            now = time.time()
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired(now):
                    self._hits += 1
                    return entry.value
                else:
                    # Lazy expiration
                    del self._cache[key]
            
            self._misses += 1
            return None

    def delete(self, key: str) -> bool:
        """
        Deletes a key from the cache.
        Returns True if the key existed and was deleted, False otherwise.
        """
        with self._lock:
            # We check if the key is present. If it is expired, we still delete it and return False,
            # because from the user's perspective, it had already expired/ceased to exist.
            if key in self._cache:
                entry = self._cache[key]
                del self._cache[key]
                return not entry.is_expired(time.time())
            return False

    def del_(self, key: str) -> bool:
        """Alias for delete."""
        return self.delete(key)

    def __delitem__(self, key: str) -> None:
        """Supports the pythonic 'del cache[key]' syntax."""
        with self._lock:
            if not self.delete(key):
                raise KeyError(key)

    def clear(self) -> None:
        """Clears all cached items and resets lookup statistics."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def has(self, key: str) -> bool:
        """
        Checks if a key exists in the cache and is not expired.
        Does not affect hits or misses statistics.
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired(time.time()):
                    return True
                else:
                    # Lazy expiration
                    del self._cache[key]
            return False

    def ttl(self, key: str, new_ttl: Optional[float]) -> bool:
        """
        Updates the TTL of an existing, non-expired key.
        Returns True on success, False if the key doesn't exist or has expired.
        """
        with self._lock:
            now = time.time()
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired(now):
                    entry.expires_at = now + new_ttl if new_ttl is not None else None
                    return True
                else:
                    # Lazy expiration
                    del self._cache[key]
            return False

    def stats(self) -> Dict[str, Any]:
        """
        Returns performance statistics of the cache:
        - total_entries: Number of active, non-expired items in cache.
        - hits: Total successful lookups.
        - misses: Total failed lookups.
        - hit_rate: Ratio of hits to total lookups (hits / (hits + misses)), defaults to 0.0.
        """
        with self._lock:
            # Clean expired items first to give accurate total_entries count
            now = time.time()
            expired_keys = [k for k, entry in self._cache.items() if entry.is_expired(now)]
            for k in expired_keys:
                del self._cache[k]

            total_entries = len(self._cache)
            total_lookups = self._hits + self._misses
            hit_rate = self._hits / total_lookups if total_lookups > 0 else 0.0

            return {
                "total_entries": total_entries,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate
            }

    def close(self) -> None:
        """Stops the active background cleanup thread."""
        self._stop_cleanup.set()
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=1.0)

    def _active_cleanup_loop(self) -> None:
        """Background loop to periodically evict expired entries."""
        while not self._stop_cleanup.is_set():
            # Sleep in short increments of 0.1 seconds to respond quickly to stopping
            sleep_needed = self._cleanup_interval
            while sleep_needed > 0 and not self._stop_cleanup.is_set():
                time.sleep(min(0.1, sleep_needed))
                sleep_needed -= 0.1
            
            if self._stop_cleanup.is_set():
                break

            with self._lock:
                now = time.time()
                expired_keys = [k for k, entry in self._cache.items() if entry.is_expired(now)]
                for k in expired_keys:
                    del self._cache[k]


# Export default instance
cache = SimpleCache()

# Add dynamic attribute 'del' to allow getattr(cache, 'del') calls without syntax error
setattr(SimpleCache, "del", SimpleCache.delete)
