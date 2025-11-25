import asyncpg
import os
from datetime import datetime, date
import calendar

async def get_db():
    return await asyncpg.connect(os.getenv("DATABASE_URL"))

# --- ADMIN ---
async def add_worker(name, rate, code, location):
    conn = await get_db()
    loc = location if location else "Umumiy"
    await conn.execute(
        "INSERT INTO workers (name, rate, code, location, active) VALUES ($1, $2, $3, $4, TRUE)", 
        name, rate, code, loc
    )
    await conn.close()

async def update_worker_field(worker_id, field, value):
    conn = await get_db()
    if field in ['name', 'rate', 'location']:
        await conn.execute(f"UPDATE workers SET {field} = $1 WHERE id = $2", value, int(worker_id))
    await conn.close()

async def archive_worker_date(worker_id):
    conn = await get_db()
    today = datetime.now().date()
    await conn.execute("UPDATE workers SET active=FALSE, archived_at=$1 WHERE id=$2", today, int(worker_id))
    await conn.close()

async def get_active_workers():
    conn = await get_db()
    rows = await conn.fetch("""
        SELECT id, name, rate, COALESCE(location, 'Umumiy') as location 
        FROM workers WHERE active=TRUE ORDER BY location, name
    """)
    await conn.close()
    return [dict(row) for row in rows]

async def get_workers_for_report(year, month):
    conn = await get_db()
    last_day = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)
    
    rows = await conn.fetch("""
        SELECT id, name, rate, location, created_at, archived_at 
        FROM workers 
        WHERE created_at <= $2 
          AND (archived_at IS NULL OR archived_at >= $1)
        ORDER BY location, name
    """, start_date, end_date)
    
    await conn.close()
    return [dict(row) for row in rows]

# --- DAVOMAT ---
async def add_attendance(worker_id, hours, status):
    conn = await get_db()
    today = datetime.now().date()
    await conn.execute("DELETE FROM attendance WHERE worker_id=$1 AND date=$2", worker_id, today)
    await conn.execute("INSERT INTO attendance (worker_id, date, hours, status) VALUES ($1, $2, $3, $4)", worker_id, today, hours, status)
    await conn.close()

async def add_advance_money(worker_id, amount):
    conn = await get_db()
    today = datetime.now().date()
    await conn.execute("INSERT INTO advances (worker_id, date, amount) VALUES ($1, $2, $3)", worker_id, today, amount)
    await conn.close()

async def get_month_attendance(year, month):
    conn = await get_db()
    date_filter = f"{year}-{month:02d}"
    rows = await conn.fetch("SELECT worker_id, TO_CHAR(date, 'YYYY-MM-DD') as date_str, hours FROM attendance WHERE TO_CHAR(date, 'YYYY-MM') = $1", date_filter)
    await conn.close()
    return rows

async def get_month_advances(year, month):
    conn = await get_db()
    date_filter = f"{year}-{month:02d}"
    rows = await conn.fetch("SELECT worker_id, SUM(amount) as total FROM advances WHERE TO_CHAR(date, 'YYYY-MM') = $1 GROUP BY worker_id", date_filter)
    await conn.close()
    return rows

# --- LOGIN ---
async def verify_login(code, telegram_id):
    conn = await get_db()
    worker = await conn.fetchrow("SELECT * FROM workers WHERE code=$1", int(code))
    if worker:
        if worker['active'] is False:
             await conn.close(); return False, "Siz ishdan bo'shatilgansiz."
        if worker['telegram_id'] is None or worker['telegram_id'] == telegram_id:
            await conn.execute("UPDATE workers SET telegram_id=$1 WHERE id=$2", telegram_id, worker['id'])
            await conn.close(); return True, worker['name']
        else:
            await conn.close(); return False, "Kod band!"
    await conn.close(); return False, "Kod xato!"

async def get_worker_stats(telegram_id):
    conn = await get_db()
    month = datetime.now().strftime("%Y-%m")
    worker = await conn.fetchrow("SELECT id, name, rate FROM workers WHERE telegram_id=$1", telegram_id)
    if not worker: await conn.close(); return None
    stats = await conn.fetchrow("SELECT SUM(hours) as total FROM attendance WHERE worker_id=$1 AND TO_CHAR(date, 'YYYY-MM')=$2", worker['id'], month)
    adv = await conn.fetchrow("SELECT SUM(amount) as total FROM advances WHERE worker_id=$1 AND TO_CHAR(date, 'YYYY-MM')=$2", worker['id'], month)
    await conn.close()
    return {"name": worker['name'], "rate": worker['rate'], "hours": stats['total'] or 0, "advance": adv['total'] or 0}