import asyncpg
import os
import logging

async def create_tables():
    """Baza jadvallarini yaratadi va kerak bo'lsa yangi ustunlarni qo'shadi."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logging.error("❌ DATABASE_URL topilmadi!")
        return

    try:
        conn = await asyncpg.connect(db_url)
        
        # 1. Ishchilar jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS workers(
                id SERIAL PRIMARY KEY,
                name TEXT,
                rate REAL,
                code INTEGER UNIQUE, 
                telegram_id BIGINT,
                location TEXT,
                active BOOLEAN DEFAULT TRUE
            )
        """)

        # --- MIGRATSIYA (Eski bazada location yo'q bo'lsa qo'shadi) ---
        try:
            await conn.execute("ALTER TABLE workers ADD COLUMN location TEXT")
            logging.info("✅ 'location' ustuni muvaffaqiyatli qo'shildi.")
        except asyncpg.exceptions.DuplicateColumnError:
            pass 
        except Exception as e:
            logging.warning(f"⚠️ Migratsiya xabari: {e}")
        # --------------------------------------------------------------

        # 2. Davomat
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance(
                id SERIAL PRIMARY KEY,
                worker_id INTEGER REFERENCES workers(id),
                date DATE,
                hours REAL,
                status TEXT
            )
        """)

        # 3. Avanslar
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS advances(
                id SERIAL PRIMARY KEY,
                worker_id INTEGER REFERENCES workers(id),
                date DATE,
                amount REAL
            )
        """)
        
        await conn.close()
        logging.info("✅ Baza 100% tayyor.")
        
    except Exception as e:
        logging.error(f"❌ Bazaga ulanishda xatolik: {e}")