import time
import threading
from typing import Any, Optional, Dict
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a cached value with expiration time."""

    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.expiry_time = time.time() + ttl_seconds

    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return time.time() > self.expiry_time


class TTLCache:
    """
    Thread-safe TTL-based cache with LRU eviction.

    Features:
    - Time-to-live expiration per entry
    - Maximum size with LRU eviction
    - Thread-safe operations
    - Hit/miss metrics tracking
    """

    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        """
        Initialize cache.

        :param ttl_seconds: Time-to-live for cache entries (default 5 minutes)
        :param max_size: Maximum number of entries (default 1000)
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()

        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        logger.info(f"Cache initialized: TTL={ttl_seconds}s, MaxSize={max_size}")

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.

        :param key: Cache key
        :return: Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                logger.debug(f"Cache expired: {key}")
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            self._hits += 1
            logger.debug(f"Cache hit: {key}")
            return entry.value

    def put(self, key: str, value: Any) -> None:
        """
        Store value in cache.

        :param key: Cache key
        :param value: Value to cache
        """
        with self._lock:
            # Check size limit
            if key not in self._cache and len(self._cache) >= self.max_size:
                # Evict oldest entry (LRU)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._evictions += 1
                logger.debug(f"Cache eviction: {oldest_key}")

            # Store new entry
            self._cache[key] = CacheEntry(value, self.ttl_seconds)
            self._cache.move_to_end(key)
            logger.debug(f"Cache put: {key}")

    def invalidate(self, key: str) -> bool:
        """
        Remove entry from cache.

        :param key: Cache key to invalidate
        :return: True if key was found and removed
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache invalidated: {key}")
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        :return: Dictionary with cache metrics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests,
            }

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        :return: Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")

            return len(expired_keys)
