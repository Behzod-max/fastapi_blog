# app/ da test_redis.py yarating:
from app.cache import redis_client

try:
    redis_client.ping()
    print("✅ Redis ga ulandi!")
except Exception as e:
    print(f"❌ Redis xato: {e}")