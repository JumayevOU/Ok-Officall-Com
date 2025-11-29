import asyncpg
import os
import logging

async def create_tables():
    db_url = os.getenv("DATABASE_URL")
    if not db_url: return

    try:
        conn = await asyncpg.connect(db_url)
        
        # 1. Ishchilar
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS workers(
                id SERIAL PRIMARY KEY,
                name TEXT,
                rate REAL,
                code INTEGER UNIQUE, 
                telegram_id BIGINT,
                location TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at DATE DEFAULT CURRENT_DATE,
                archived_at DATE DEFAULT NULL
            )
        """)

        # 2. Davomat (Oddiy: Sana va Soat)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance(
                id SERIAL PRIMARY KEY,
                worker_id INTEGER REFERENCES workers(id),
                date DATE,
                hours REAL,
                status TEXT
            )
        """)

        # 3. Avans
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS advances(
                id SERIAL PRIMARY KEY,
                worker_id INTEGER REFERENCES workers(id),
                date DATE,
                amount REAL
            )
        """)
        
        # Migratsiya (Ehtiyot shart)
        try:
            await conn.execute("ALTER TABLE workers ADD COLUMN location TEXT")
            await conn.execute("ALTER TABLE workers ADD COLUMN created_at DATE DEFAULT CURRENT_DATE")
            await conn.execute("ALTER TABLE workers ADD COLUMN archived_at DATE DEFAULT NULL")
        except: pass

        await conn.close()
        logging.info("✅ Baza (Stabil) yuklandi.")
        
    except Exception as e:
        logging.error(f"❌ Baza xatosi: {e}")