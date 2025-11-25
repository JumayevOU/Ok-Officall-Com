import asyncpg
import os
from datetime import datetime

async def get_db():
    return await asyncpg.connect(os.getenv("DATABASE_URL"))

# --- ADMIN QISMI ---

async def add_worker(name, rate, code, location):
    conn = await get_db()
    loc = location if location else "Umumiy"
    await conn.execute(
        "INSERT INTO workers (name, rate, code, location) VALUES ($1, $2, $3, $4)", 
        name, rate, code, loc
    )
    await conn.close()

async def get_active_workers():
    conn = await get_db()
    # Location bo'yicha saralaymiz (Excel va Ro'yxat chiroyli chiqishi uchun)
    rows = await conn.fetch("""
        SELECT id, name, rate, COALESCE(location, 'Umumiy') as location 
        FROM workers 
        WHERE active=TRUE 
        ORDER BY location, name
    """)
    await conn.close()
    return [dict(row) for row in rows]

async def add_attendance(worker_id, hours, status):
    conn = await get_db()
    date = datetime.now().date()
    # Agar bugun uchun yozilgan bo'lsa, o'chirib yangisini yozamiz (Update)
    await conn.execute("DELETE FROM attendance WHERE worker_id=$1 AND date=$2", worker_id, date)
    await conn.execute(
        "INSERT INTO attendance (worker_id, date, hours, status) VALUES ($1, $2, $3, $4)",
        worker_id, date, hours, status
    )
    await conn.close()

async def add_advance_money(worker_id, amount):
    conn = await get_db()
    date = datetime.now().date()
    await conn.execute(
        "INSERT INTO advances (worker_id, date, amount) VALUES ($1, $2, $3)",
        worker_id, date, amount
    )
    await conn.close()

# --- ISHCHI LOGIN ---

async def verify_login(code, telegram_id):
    conn = await get_db()
    worker = await conn.fetchrow("SELECT * FROM workers WHERE code=$1", int(code))
    
    if worker:
        if worker['telegram_id'] is None:
            await conn.execute("UPDATE workers SET telegram_id=$1 WHERE id=$2", telegram_id, worker['id'])
            await conn.close()
            return True, worker['name']
        elif worker['telegram_id'] == telegram_id:
            await conn.close()
            return True, worker['name']
        else:
            await conn.close()
            return False, "⛔️ Bu kod band qilingan!"
    
    await conn.close()
    return False, "⛔️ Kod noto'g'ri!"

async def get_worker_stats(telegram_id):
    conn = await get_db()
    current_month = datetime.now().strftime("%Y-%m")
    
    worker = await conn.fetchrow("SELECT id, name, rate FROM workers WHERE telegram_id=$1", telegram_id)
    if not worker: 
        await conn.close()
        return None
    
    stats = await conn.fetchrow("""
        SELECT SUM(hours) as total_hours 
        FROM attendance 
        WHERE worker_id=$1 AND TO_CHAR(date, 'YYYY-MM') = $2
    """, worker['id'], current_month)
    
    adv = await conn.fetchrow("""
        SELECT SUM(amount) as total_adv 
        FROM advances 
        WHERE worker_id=$1 AND TO_CHAR(date, 'YYYY-MM') = $2
    """, worker['id'], current_month)
    
    await conn.close()
    return {
        "name": worker['name'],
        "rate": worker['rate'],
        "hours": stats['total_hours'] or 0,
        "advance": adv['total_adv'] or 0
    }

# --- HISOBOTLAR UCHUN ---

async def get_month_attendance(year, month):
    conn = await get_db()
    date_filter = f"{year}-{month:02d}"
    rows = await conn.fetch("""
        SELECT worker_id, TO_CHAR(date, 'YYYY-MM-DD') as date_str, hours 
        FROM attendance WHERE TO_CHAR(date, 'YYYY-MM') = $1
    """, date_filter)
    await conn.close()
    return rows

async def get_month_advances(year, month):
    conn = await get_db()
    date_filter = f"{year}-{month:02d}"
    rows = await conn.fetch("""
        SELECT worker_id, SUM(amount) as total 
        FROM advances WHERE TO_CHAR(date, 'YYYY-MM') = $1 GROUP BY worker_id
    """, date_filter)
    await conn.close()
    return rows