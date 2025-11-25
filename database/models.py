import asyncpg
import os

async def create_tables():
    db_url = os.getenv("DATABASE_URL")
    conn = await asyncpg.connect(db_url)
    
    # Ishchilar jadvali (code - bu ishchi kirishi uchun ID)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS workers(
            id SERIAL PRIMARY KEY,
            name TEXT,
            rate REAL,
            code INTEGER UNIQUE, 
            telegram_id BIGINT,
            active BOOLEAN DEFAULT TRUE
        )
    """)
    
    # Davomat
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance(
            id SERIAL PRIMARY KEY,
            worker_id INTEGER REFERENCES workers(id),
            date DATE,
            hours REAL,
            status TEXT
        )
    """)
    
    # Avanslar
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS advances(
            id SERIAL PRIMARY KEY,
            worker_id INTEGER REFERENCES workers(id),
            date DATE,
            amount REAL
        )
    """)
    
    await conn.close()