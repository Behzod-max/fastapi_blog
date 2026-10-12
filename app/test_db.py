from .database import engine

try:
    connection = engine.connect()
    print("✅ PostgreSQL ga muvaffaqiyatli ulandi!")
    connection.close()
except Exception as e:
    print(f"❌ Xato: {e}")