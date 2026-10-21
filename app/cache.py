import redis
import json
from typing import Optional, Any
from .config import settings

# Redis ulanish
redis_client = redis.from_url(
    settings.redis_url,
    decode_responses=True    # Bytes → String avtomatik
)

def cache_get(key: str) -> Optional[Any]:
    """Redis dan qiymat olish"""
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"Cache get xato: {e}")
        return None

def cache_set(key: str, value: Any, ttl: int = None) -> bool:
    """Redis ga qiymat saqlash"""
    try:
        if ttl is None:
            ttl = settings.cache_ttl
        redis_client.setex(
            key,
            ttl,
            json.dumps(value, default=str)  # datetime uchun str
        )
        return True
    except Exception as e:
        print(f"Cache set xato: {e}")
        return False

def cache_delete(key: str) -> bool:
    """Redis dan o'chirish"""
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        print(f"Cache delete xato: {e}")
        return False

def cache_delete_pattern(pattern: str) -> int:
    """Pattern bo'yicha o'chirish (masalan: 'posts:*')"""
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        return len(keys)
    except Exception as e:
        print(f"Cache pattern delete xato: {e}")
        return 0

def cache_exists(key: str) -> bool:
    """Kalit borligini tekshirish"""
    try:
        return bool(redis_client.exists(key))
    except Exception:
        return False