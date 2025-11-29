import asyncpg
import os
import logging

async def create_tables():
    db_url = os.getenv("DATABASE_URL")
    if not db_url: return

    try:
        conn = await asyncpg.connect(db_url)
        
        # Jadvallar
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
            );
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS attendance(
                id SERIAL PRIMARY KEY,
                worker_id INTEGER REFERENCES workers(id),
                date DATE,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                hours REAL,
                status TEXT
            );
            CREATE TABLE IF NOT EXISTS advances(
                id SERIAL PRIMARY KEY,
                worker_id INTEGER REFERENCES workers(id),
                date DATE,
                amount REAL
            );
        """)

        # Migratsiya (xatosiz)
        queries = [
            "ALTER TABLE workers ADD COLUMN location TEXT",
            "ALTER TABLE workers ADD COLUMN created_at DATE DEFAULT CURRENT_DATE",
            "ALTER TABLE workers ADD COLUMN archived_at DATE DEFAULT NULL",
            "ALTER TABLE attendance ADD COLUMN start_time TIMESTAMP",
            "ALTER TABLE attendance ADD COLUMN end_time TIMESTAMP"
        ]
        for q in queries:
            try: await conn.execute(q)
            except: pass
            
        await conn.close()
        logging.info("✅ Baza tizimi yuklandi.")
    except Exception as e:
        logging.error(f"❌ Baza xatosi: {e}")