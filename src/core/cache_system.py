"""
Cache system multi-livello con Redis
Basato su: aioredis/aioredis-py e leonsk/cachier
Ref: https://github.com/aio-libs/aioredis-py
"""
import asyncio
import redis.asyncio as aioredis
import pickle
import hashlib
from typing import Optional, Any, Union, Callable
from datetime import timedelta
from functools import wraps
import aiocache
from aiocache import Cache
from aiocache.serializers import PickleSerializer

class MultiLevelCache:
    """
    Cache multi-livello: Memory (L1) -> Redis (L2)
    Pattern da cachier e django-redis
    """
    
    def __init__(self, redis_url: str = 'redis://localhost:6379', default_ttl: int = 3600, redis_client: Optional[aioredis.Redis] = None):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        
        # L1: In-memory cache
        self.memory_cache = Cache(Cache.MEMORY, serializer=PickleSerializer())
        
        # L2: Redis cache (optional)
        self.redis_client = redis_client
        
    async def initialize(self):
        """Inizializza connessione Redis"""
        self.redis_client = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=False
        )
        
    async def get(self, key: str) -> Optional[Any]:
        """Get con fallback L1 -> L2"""
        # Try L1
        value = await self.memory_cache.get(key)
        if value is not None:
            return value
            
        # Try L2
        if self.redis_client:
            raw_value = await self.redis_client.get(key)
            if raw_value:
                value = pickle.loads(raw_value)
                # Populate L1
                await self.memory_cache.set(key, value, ttl=300)  # 5 min in memory
                return value
                
        return None
        
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set su entrambi i livelli"""
        ttl = ttl or self.default_ttl
        
        # Set L1
        await self.memory_cache.set(key, value, ttl=min(ttl, 300))
        
        # Set L2
        if self.redis_client:
            serialized = pickle.dumps(value)
            await self.redis_client.setex(key, ttl, serialized)
            
    async def delete(self, key: str):
        """Delete da entrambi i livelli"""
        await self.memory_cache.delete(key)
        if self.redis_client:
            await self.redis_client.delete(key)
            
    def make_key(self, prefix: str, *args, **kwargs) -> str:
        """Genera cache key deterministico"""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()

def cached(ttl: int = 3600, key_prefix: str = None):
    """
    Decorator per caching automatico
    Ispirato a leonsk/cachier
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip cache if requested
            if kwargs.pop('skip_cache', False):
                return await func(*args, **kwargs)
                
            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = cache.make_key(prefix, *args, **kwargs)
            
            # Try cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
                
            # Compute and cache
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl)
            return result
            
        return wrapper
    return decorator

# Global cache instance
cache = MultiLevelCache(redis_url="redis://localhost:6379")
