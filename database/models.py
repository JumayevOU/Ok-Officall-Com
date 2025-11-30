import asyncpg
import os
import logging
from typing import Optional

# Connection pool global o'zgaruvchisi
DB_POOL: Optional[asyncpg.Pool] = None

async def create_db_pool():
    """Database connection pool yaratish"""
    global DB_POOL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logging.error("❌ DATABASE_URL topilmadi!")
        return None
    
    try:
        DB_POOL = await asyncpg.create_pool(
            db_url,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logging.info("✅ Database pool yaratildi")
        return DB_POOL
    except Exception as e:
        logging.error(f"❌ Database pool yaratishda xato: {e}")
        return None

async def create_tables():
    """Database jadvallarini yaratish"""
    if not DB_POOL:
        logging.error("❌ Database pool mavjud emas!")
        return False

    try:
        async with DB_POOL.acquire() as conn:
            # 1. Ishchilar jadvali (location ustunisiz)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS workers(
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    rate DECIMAL(10,2) NOT NULL,
                    code INTEGER UNIQUE NOT NULL,
                    telegram_id BIGINT UNIQUE,
                    active BOOLEAN DEFAULT TRUE,
                    created_at DATE DEFAULT CURRENT_DATE,
                    archived_at DATE DEFAULT NULL
                )
            """)

            # 2. Davomat jadvali
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS attendance(
                    id SERIAL PRIMARY KEY,
                    worker_id INTEGER REFERENCES workers(id) ON DELETE CASCADE,
                    date DATE NOT NULL,
                    hours DECIMAL(4,2) DEFAULT 0,
                    status TEXT DEFAULT 'Keldi',
                    UNIQUE(worker_id, date)
                )
            """)

            # 3. Avans jadvali
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS advances(
                    id SERIAL PRIMARY KEY,
                    worker_id INTEGER REFERENCES workers(id) ON DELETE CASCADE,
                    date DATE NOT NULL,
                    amount DECIMAL(12,2) NOT NULL,
                    approved BOOLEAN DEFAULT TRUE
                )
            """)

            # location ustunini olib tashlash (agar mavjud bo'lsa)
            try:
                await conn.execute("ALTER TABLE workers DROP COLUMN IF EXISTS location")
            except Exception as e:
                logging.warning(f"Location ustunini o'chirishda xato: {e}")

            # Indexlar
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_workers_telegram ON workers(telegram_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_workers_active ON workers(active)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_advances_date ON advances(date)")

            logging.info("✅ Barcha jadvallar va indexlar yaratildi")
            return True
            
    except Exception as e:
        logging.error(f"❌ Jadvallarni yaratishda xato: {e}")
        return False

async def close_db_pool():
    """Database poolni yopish"""
    global DB_POOL
    if DB_POOL:
        await DB_POOL.close()
        logging.info("✅ Database pool yopildi")