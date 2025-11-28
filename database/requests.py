import asyncpg
import os
from datetime import datetime, date
import calendar

async def get_db():
    return await asyncpg.connect(os.getenv("DATABASE_URL"))

# --- SOZLAMALAR ---
async def set_work_location(lat, lon):
    conn = await get_db()
    val = f"{lat},{lon}"
    await conn.execute("INSERT INTO settings (key, value) VALUES ('work_loc', $1) ON CONFLICT (key) DO UPDATE SET value = $1", val)
    await conn.close()

async def get_work_location():
    conn = await get_db()
    val = await conn.fetchval("SELECT value FROM settings WHERE key='work_loc'")
    await conn.close()
    if val:
        lat, lon = val.split(',')
        return float(lat), float(lon)
    return None

# --- ISHCHILARNI BOSHQARISH ---
async def add_worker(name, rate, code, location):
    conn = await get_db()
    loc = location if location else "Umumiy"
    await conn.execute("INSERT INTO workers (name, rate, code, location, active) VALUES ($1, $2, $3, $4, TRUE)", name, rate, code, loc)
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
    rows = await conn.fetch("SELECT id, name, rate, COALESCE(location, 'Umumiy') as location FROM workers WHERE active=TRUE ORDER BY location, name")
    await conn.close()
    return [dict(row) for row in rows]

async def search_worker_by_name(text):
    conn = await get_db()
    # Ism bo'yicha qidirish (ILIKE - katta kichik farqi yo'q)
    rows = await conn.fetch("SELECT id, name, location FROM workers WHERE active=TRUE AND name ILIKE $1", f"%{text}%")
    await conn.close()
    return [dict(row) for row in rows]

async def get_worker_tg_id(worker_id):
    conn = await get_db()
    val = await conn.fetchval("SELECT telegram_id FROM workers WHERE id=$1", int(worker_id))
    await conn.close()
    return val

# --- KELDI-KETDI ---
async def check_in_worker(worker_id):
    conn = await get_db()
    today = datetime.now().date()
    now = datetime.now()
    exists = await conn.fetchrow("SELECT id FROM attendance WHERE worker_id=$1 AND date=$2", worker_id, today)
    if exists:
        await conn.execute("UPDATE attendance SET start_time=$1, status='Keldi' WHERE id=$2", now, exists['id'])
    else:
        await conn.execute("INSERT INTO attendance (worker_id, date, start_time, hours, status) VALUES ($1, $2, $3, 0, 'Keldi')", worker_id, today, now)
    await conn.close()

async def check_out_worker(worker_id):
    conn = await get_db()
    today = datetime.now().date()
    now = datetime.now()
    row = await conn.fetchrow("SELECT id, start_time FROM attendance WHERE worker_id=$1 AND date=$2", worker_id, today)
    
    if not row or not row['start_time']:
        await conn.close()
        return False, "Siz hali 'Keldim' tugmasini bosmagansiz!"
    
    start_time = row['start_time']
    duration = (now - start_time).total_seconds() / 3600
    hours = round(duration, 1)
    
    await conn.execute("UPDATE attendance SET end_time=$1, hours=$2 WHERE id=$3", now, hours, row['id'])
    await conn.close()
    return True, hours

async def is_checked_in(worker_id):
    conn = await get_db()
    today = datetime.now().date()
    val = await conn.fetchval("SELECT start_time FROM attendance WHERE worker_id=$1 AND date=$2", worker_id, today)
    await conn.close()
    return val is not None

async def add_attendance_manual(worker_id, hours, status):
    conn = await get_db()
    today = datetime.now().date()
    await conn.execute("DELETE FROM attendance WHERE worker_id=$1 AND date=$2", worker_id, today)
    await conn.execute("INSERT INTO attendance (worker_id, date, hours, status) VALUES ($1, $2, $3, $4)", worker_id, today, hours, status)
    await conn.close()

# --- MOLIYA VA HISOBOT ---
async def add_advance_money(worker_id, amount):
    conn = await get_db()
    today = datetime.now().date()
    await conn.execute("INSERT INTO advances (worker_id, date, amount) VALUES ($1, $2, $3)", worker_id, today, amount)
    await conn.close()

async def get_month_attendance(year, month):
    conn = await get_db()
    rows = await conn.fetch("SELECT worker_id, TO_CHAR(date, 'YYYY-MM-DD') as date_str, hours FROM attendance WHERE TO_CHAR(date, 'YYYY-MM') = $1", f"{year}-{month:02d}")
    await conn.close()
    return rows

async def get_month_advances(year, month):
    conn = await get_db()
    rows = await conn.fetch("SELECT worker_id, SUM(amount) as total FROM advances WHERE TO_CHAR(date, 'YYYY-MM') = $1 GROUP BY worker_id", f"{year}-{month:02d}")
    await conn.close()
    return rows

async def get_workers_for_report(year, month):
    conn = await get_db()
    last = calendar.monthrange(year, month)[1]
    start, end = date(year, month, 1), date(year, month, last)
    rows = await conn.fetch("""
        SELECT id, name, rate, location, created_at, archived_at 
        FROM workers 
        WHERE created_at <= $2 AND (archived_at IS NULL OR archived_at >= $1)
        ORDER BY location, name
    """, start, end)
    await conn.close()
    return [dict(row) for row in rows]

# --- LOGIN VA STATISTIKA ---
async def verify_login(code, telegram_id):
    conn = await get_db()
    worker = await conn.fetchrow("SELECT * FROM workers WHERE code=$1", int(code))
    if worker:
        if worker['active'] is False: await conn.close(); return False, "Siz arxivdasiz (ishlamaysiz)."
        if worker['telegram_id'] is None or worker['telegram_id'] == telegram_id:
            await conn.execute("UPDATE workers SET telegram_id=$1 WHERE id=$2", telegram_id, worker['id'])
            await conn.close(); return True, worker['name']
        else: await conn.close(); return False, "Kod band qilingan!"
    await conn.close(); return False, "Kod noto'g'ri!"

async def get_worker_stats(telegram_id):
    conn = await get_db()
    month = datetime.now().strftime("%Y-%m")
    worker = await conn.fetchrow("SELECT id, name, rate FROM workers WHERE telegram_id=$1", telegram_id)
    if not worker: await conn.close(); return None
    stats = await conn.fetchrow("SELECT SUM(hours) as total FROM attendance WHERE worker_id=$1 AND TO_CHAR(date, 'YYYY-MM')=$2", worker['id'], month)
    adv = await conn.fetchrow("SELECT SUM(amount) as total FROM advances WHERE worker_id=$1 AND TO_CHAR(date, 'YYYY-MM')=$2", worker['id'], month)
    await conn.close()
    return {"name": worker['name'], "rate": worker['rate'], "hours": stats['total'] or 0, "advance": adv['total'] or 0}