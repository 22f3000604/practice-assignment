import time
import threading
import pytest
from app import SimpleCache, cache, CacheEntry


@pytest.fixture
def clean_cache():
    """Provides a fresh cache instance and closes it after the test."""
    # Initialize with a fast cleanup interval for testing (0.1s)
    c = SimpleCache(cleanup_interval=0.1)
    yield c
    c.close()


@pytest.fixture(autouse=True)
def clean_global_cache():
    """Ensure the global singleton cache is cleared and closed correctly."""
    cache.clear()
    yield
    cache.clear()


# ---- Basic Operations Tests ----

class TestBasicOperations:

    def test_set_and_get(self, clean_cache):
        """Should set and get values of different data types."""
        clean_cache.set("str_key", "string_val")
        clean_cache.set("int_key", 42)
        clean_cache.set("dict_key", {"a": 1})
        clean_cache.set("list_key", [1, 2, 3])

        assert clean_cache.get("str_key") == "string_val"
        assert clean_cache.get("int_key") == 42
        assert clean_cache.get("dict_key") == {"a": 1}
        assert clean_cache.get("list_key") == [1, 2, 3]

    def test_get_non_existent(self, clean_cache):
        """Getting a non-existent key should return None."""
        assert clean_cache.get("missing") is None

    def test_has_method(self, clean_cache):
        """has() should check for key existence without affecting hits/misses statistics."""
        clean_cache.set("key", "val")
        assert clean_cache.has("key") is True
        assert clean_cache.has("missing") is False

        # Verify stats were not affected by has()
        stats = clean_cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_delete_method(self, clean_cache):
        """delete() and del_() should remove the key and return True if existed, False otherwise."""
        clean_cache.set("key1", "val1")
        clean_cache.set("key2", "val2")

        # Delete existing
        assert clean_cache.delete("key1") is True
        assert clean_cache.get("key1") is None

        # Delete using alias del_
        assert clean_cache.del_("key2") is True
        assert clean_cache.get("key2") is None

        # Delete non-existing
        assert clean_cache.delete("missing") is False

    def test_del_keyword_workaround(self, clean_cache):
        """getattr(cache, 'del') should run delete successfully."""
        clean_cache.set("key", "val")
        del_func = getattr(clean_cache, "del")
        assert del_func("key") is True
        assert clean_cache.get("key") is None

    def test_delitem_syntax(self, clean_cache):
        """Should support standard python 'del cache[key]' syntax."""
        clean_cache.set("key", "val")
        del clean_cache["key"]
        assert clean_cache.get("key") is None

        # del item on missing key raises KeyError
        with pytest.raises(KeyError):
            del clean_cache["missing"]

    def test_clear_method(self, clean_cache):
        """clear() should empty all cached items and reset statistics."""
        clean_cache.set("key1", "val1")
        clean_cache.set("key2", "val2")
        clean_cache.get("key1")
        clean_cache.get("missing")

        assert clean_cache.stats()["total_entries"] == 2
        assert clean_cache.stats()["hits"] == 1
        assert clean_cache.stats()["misses"] == 1

        clean_cache.clear()

        # Verify stats are immediately reset
        stats = clean_cache.stats()
        assert stats["total_entries"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0

        # Querying post-clear should increment misses
        assert clean_cache.get("key1") is None
        stats_post = clean_cache.stats()
        assert stats_post["misses"] == 1
        assert stats_post["total_entries"] == 0


# ---- TTL & Expiration Tests ----

class TestTTLExpiration:

    def test_lazy_expiration(self, clean_cache):
        """Expired keys should be deleted upon access and count as a miss."""
        # Set with a short TTL (0.1 seconds)
        clean_cache.set("key", "val", ttl=0.1)
        assert clean_cache.get("key") == "val"

        # Wait for expiration
        time.sleep(0.15)

        # Accessing should return None (lazy expiration)
        assert clean_cache.get("key") is None

        # Stats should record 1 hit (first get) and 1 miss (second get after expiration)
        stats = clean_cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_update_ttl(self, clean_cache):
        """ttl() should update the TTL of an active key."""
        clean_cache.set("key", "val", ttl=0.1)

        # Update TTL to 10 seconds
        assert clean_cache.ttl("key", 10.0) is True

        # Wait longer than original 0.1s TTL
        time.sleep(0.15)

        # Verify key is still present and valid
        assert clean_cache.get("key") == "val"

    def test_update_ttl_non_existent_or_expired(self, clean_cache):
        """ttl() should return False for non-existent or expired keys."""
        assert clean_cache.ttl("missing", 10.0) is False

        clean_cache.set("expired_key", "val", ttl=0.05)
        time.sleep(0.1)
        assert clean_cache.ttl("expired_key", 10.0) is False

    def test_remove_ttl_expiry(self, clean_cache):
        """Updating TTL to None should make the key persistent (no expiry)."""
        clean_cache.set("key", "val", ttl=0.05)
        
        # Remove TTL
        assert clean_cache.ttl("key", None) is True
        
        time.sleep(0.1)
        assert clean_cache.get("key") == "val"

    def test_active_expiration(self, clean_cache):
        """Background thread should automatically remove expired keys without accessing them."""
        clean_cache.set("key1", "val1", ttl=0.05)
        clean_cache.set("key2", "val2", ttl=10.0)  # persists

        assert clean_cache.stats()["total_entries"] == 2

        # Wait for key1 to expire and background thread to run cleanup sweep
        time.sleep(0.2)

        # Stats should show only key2 remaining
        stats = clean_cache.stats()
        assert stats["total_entries"] == 1
        assert "key1" not in clean_cache._cache
        assert "key2" in clean_cache._cache


# ---- Statistics Tests ----

class TestStatistics:

    def test_stats_tracking(self, clean_cache):
        """Stats should correctly track total entries, hits, misses, and hit rate."""
        stats = clean_cache.stats()
        assert stats["total_entries"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0

        clean_cache.set("k1", "v1")
        clean_cache.set("k2", "v2")

        # 3 hits
        clean_cache.get("k1")
        clean_cache.get("k1")
        clean_cache.get("k2")

        # 2 misses
        clean_cache.get("missing1")
        clean_cache.get("missing2")

        stats = clean_cache.stats()
        assert stats["total_entries"] == 2
        assert stats["hits"] == 3
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 0.6  # 3 / 5


# ---- Thread Safety & Concurrency Tests ----

class TestThreadSafety:

    def test_concurrent_access(self, clean_cache):
        """Verify thread-safety by running concurrent sets, gets, and deletes."""
        num_threads = 10
        ops_per_thread = 100
        errors = []

        def worker(thread_idx):
            try:
                for i in range(ops_per_thread):
                    key = f"thread_{thread_idx}_key_{i}"
                    # Perform set
                    clean_cache.set(key, i, ttl=1.0)
                    
                    # Perform get
                    val = clean_cache.get(key)
                    if val is not None:
                        assert val == i
                    
                    # Perform has
                    clean_cache.has(key)
                    
                    # Perform delete on every alternate loop
                    if i % 2 == 0:
                        clean_cache.delete(key)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors encountered: {errors}"
        
        # Verify stats are queryable without error
        stats = clean_cache.stats()
        assert stats["hits"] + stats["misses"] == num_threads * ops_per_thread
