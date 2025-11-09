"""
Simple TTL cache for GitHub API responses
"""
import time
from typing import Dict, Any, Optional


class TTLCache:
    """Simple time-to-live cache"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, tuple[Any, float]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache with current timestamp"""
        self.cache[key] = (value, time.time())
    
    def clear(self):
        """Clear all cached values"""
        self.cache.clear()


# Global cache instance
_cache = TTLCache(ttl_seconds=300)


def get_cache() -> TTLCache:
    """Get the global cache instance"""
    return _cache

