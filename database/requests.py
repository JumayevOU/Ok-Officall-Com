import asyncpg
import os
from datetime import datetime

async def get_db():
    return await asyncpg.connect(os.getenv("DATABASE_URL"))

# --- ADMIN UCHUN ---
async def add_worker(name, rate, code):
    conn = await get_db()
    await conn.execute("INSERT INTO workers (name, rate, code) VALUES ($1, $2, $3)", name, rate, code)
    await conn.close()

async def get_active_workers():
    conn = await get_db()
    rows = await conn.fetch("SELECT id, name, rate FROM workers WHERE active=TRUE ORDER BY id")
    await conn.close()
    return rows

async def archive_worker(worker_id):
    conn = await get_db()
    await conn.execute("UPDATE workers SET active=FALSE WHERE id=$1", int(worker_id))
    await conn.close()

async def add_attendance(worker_id, hours, status):
    conn = await get_db()
    date = datetime.now().date()
    await conn.execute("INSERT INTO attendance (worker_id, date, hours, status) VALUES ($1, $2, $3, $4)",
                       worker_id, date, hours, status)
    await conn.close()

async def add_advance_money(worker_id, amount):
    conn = await get_db()
    date = datetime.now().date()
    await conn.execute("INSERT INTO advances (worker_id, date, amount) VALUES ($1, $2, $3)",
                       worker_id, date, amount)
    await conn.close()

# --- ISHCHI UCHUN ---
async def verify_login(code, telegram_id):
    conn = await get_db()
    # Kod bormi va unga hali telegram_id ulanmaganmi?
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
            return False, "Bu kod boshqa odam tomonidan ishlatilgan!"
    await conn.close()
    return False, "Kod noto'g'ri!"

async def get_worker_stats(telegram_id):
    conn = await get_db()
    current_month = datetime.now().strftime("%Y-%m")
    
    worker = await conn.fetchrow("SELECT id, name, rate FROM workers WHERE telegram_id=$1", telegram_id)
    if not worker: return None
    
    # Hisob-kitob
    stats = await conn.fetchrow("""
        SELECT SUM(hours) as total_hours, COUNT(*) as days 
        FROM attendance 
        WHERE worker_id=$1 AND TO_CHAR(date, 'YYYY-MM') = $2
    """, worker['id'], current_month)
    
    advances = await conn.fetchrow("""
        SELECT SUM(amount) as total_adv 
        FROM advances 
        WHERE worker_id=$1 AND TO_CHAR(date, 'YYYY-MM') = $2
    """, worker['id'], current_month)
    
    await conn.close()
    return {
        "name": worker['name'],
        "rate": worker['rate'],
        "hours": stats['total_hours'] or 0,
        "advance": advances['total_adv'] or 0
    }

# --- EXCEL UCHUN ---
async def get_monthly_report_data():
    conn = await get_db()
    current_month = datetime.now().strftime("%Y-%m")
    
    # Barcha ma'lumotlarni tortib olish (Murakkab SQL)
    rows = await conn.fetch("""
        SELECT w.name, w.rate, 
               COALESCE(SUM(a.hours), 0) as total_hours,
               (SELECT COALESCE(SUM(amount), 0) FROM advances adv WHERE adv.worker_id=w.id AND TO_CHAR(adv.date, 'YYYY-MM')=$1) as total_advance
        FROM workers w
        LEFT JOIN attendance a ON w.id = a.worker_id AND TO_CHAR(a.date, 'YYYY-MM')=$1
        WHERE w.active=TRUE
        GROUP BY w.id, w.name, w.rate
    """, current_month)
    await conn.close()
    return rows