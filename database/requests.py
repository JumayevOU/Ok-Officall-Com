import asyncpg
import os
import logging
from datetime import datetime, date
import calendar
from typing import List, Dict, Any, Optional
# DIQQAT: DB_POOL ni to'g'ridan-to'g'ri import qilmang, models ni import qiling
from database import models

class DatabaseError(Exception):
    pass

async def execute_query(query: str, *args) -> Any:
    # models.DB_POOL orqali murojaat qilamiz, shunda u har doim yangi bo'ladi
    if not models.DB_POOL:
        logging.error("❌ Database pool mavjud emas (execute_query) - Baza ulanmagan!")
        return []
    
    try:
        async with models.DB_POOL.acquire() as conn:
            if query.strip().upper().startswith('SELECT'):
                result = await conn.fetch(query, *args)
            else:
                result = await conn.execute(query, *args)
            return result
    except Exception as e:
        logging.error(f"❌ DB Xatosi: {e}\nQuery: {query}\nArgs: {args}")
        return []

# --- ISHCHILAR ---
async def add_worker(name: str, rate: float, code: int) -> bool:
    try:
        exists = await execute_query("SELECT 1 FROM workers WHERE code = $1", code)
        if exists: return False
        
        await execute_query(
            "INSERT INTO workers (name, rate, code, active, created_at) VALUES ($1, $2, $3, TRUE, CURRENT_DATE)", 
            name.strip(), float(rate), int(code)
        )
        return True
    except Exception as e:
        logging.error(f"add_worker xatosi: {e}")
        return False

async def get_active_workers() -> List[Dict[str, Any]]:
    try:
        rows = await execute_query("SELECT * FROM workers WHERE active = TRUE ORDER BY name")
        return [dict(row) for row in rows] if rows else []
    except Exception as e:
        logging.error(f"get_active_workers xatosi: {e}")
        return []

async def get_worker_by_id(worker_id: int) -> Optional[Dict[str, Any]]:
    rows = await execute_query("SELECT * FROM workers WHERE id = $1", worker_id)
    return dict(rows[0]) if rows else None

async def search_worker_by_name(text: str) -> List[Dict[str, Any]]:
    rows = await execute_query("SELECT * FROM workers WHERE active = TRUE AND name ILIKE $1", f"%{text}%")
    return [dict(row) for row in rows] if rows else []

async def update_worker_field(worker_id: int, field: str, value: Any) -> bool:
    if field not in ['name', 'rate']: return False
    try:
        await execute_query(f"UPDATE workers SET {field} = $1 WHERE id = $2", value, worker_id)
        return True
    except: return False

async def archive_worker(worker_id: int) -> bool:
    try:
        await execute_query("UPDATE workers SET active = FALSE, archived_at = CURRENT_DATE WHERE id = $1", worker_id)
        return True
    except: return False

# --- DAVOMAT ---
async def add_attendance(worker_id: int, hours: float, status: str) -> bool:
    try:
        await execute_query("""
            INSERT INTO attendance (worker_id, date, hours, status) 
            VALUES ($1, CURRENT_DATE, $2, $3)
            ON CONFLICT (worker_id, date) 
            DO UPDATE SET hours = EXCLUDED.hours, status = EXCLUDED.status
        """, worker_id, float(hours), status)
        return True
    except Exception as e:
        logging.error(f"add_attendance error: {e}")
        return False

async def add_advance(worker_id: int, amount: float, approved: bool = True) -> bool:
    try:
        await execute_query(
            "INSERT INTO advances (worker_id, date, amount, approved) VALUES ($1, CURRENT_DATE, $2, $3)",
            worker_id, float(amount), approved
        )
        return True
    except Exception as e:
        logging.error(f"add_advance error: {e}")
        return False

# --- HISOBOT UCHUN ---
async def get_month_data(year: int, month: int) -> tuple:
    date_filter = f"{year}-{month:02d}"
    
    att = await execute_query("""
        SELECT worker_id, hours FROM attendance 
        WHERE TO_CHAR(date, 'YYYY-MM') = $1
    """, date_filter)
    
    adv = await execute_query("""
        SELECT worker_id, SUM(amount) as total FROM advances 
        WHERE TO_CHAR(date, 'YYYY-MM') = $1 AND approved = TRUE
        GROUP BY worker_id
    """, date_filter)
    
    return att, adv

async def get_workers_for_report(year: int, month: int) -> List[Dict[str, Any]]:
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    start_date = date(year, month, 1)
    
    rows = await execute_query("""
        SELECT * FROM workers 
        WHERE (created_at IS NULL OR created_at <= $2)
          AND (archived_at IS NULL OR archived_at >= $1)
        ORDER BY name
    """, start_date, end_date)
    
    return [dict(row) for row in rows] if rows else []

async def get_month_attendance(year: int, month: int):
    date_filter = f"{year}-{month:02d}"
    return await execute_query("""
        SELECT worker_id, TO_CHAR(date, 'YYYY-MM-DD') as date_str, hours 
        FROM attendance 
        WHERE TO_CHAR(date, 'YYYY-MM') = $1
    """, date_filter)

async def get_month_advances(year: int, month: int):
    date_filter = f"{year}-{month:02d}"
    return await execute_query("""
        SELECT worker_id, SUM(amount) as total 
        FROM advances 
        WHERE TO_CHAR(date, 'YYYY-MM') = $1 AND approved = TRUE
        GROUP BY worker_id
    """, date_filter)

# --- LOGIN ---
async def verify_login(code: str, telegram_id: int) -> tuple:
    if not code.isdigit(): return False, "Faqat raqam kiriting"
    
    rows = await execute_query("SELECT * FROM workers WHERE code = $1", int(code))
    if not rows: return False, "❌ Noto'g'ri kod"
    
    worker = dict(rows[0])
    if not worker['active']: return False, "❌ Profil aktiv emas"
    
    if worker['telegram_id'] and worker['telegram_id'] != telegram_id:
        return False, "❌ Bu kod band"
        
    await execute_query("UPDATE workers SET telegram_id = $1 WHERE id = $2", telegram_id, worker['id'])
    return True, worker['name']

async def get_worker_stats(telegram_id: int) -> Optional[Dict[str, Any]]:
    rows = await execute_query("SELECT * FROM workers WHERE telegram_id = $1 AND active = TRUE", telegram_id)
    if not rows: return None
    
    worker = dict(rows[0])
    month = datetime.now().strftime("%Y-%m")
    
    h_data = await execute_query("SELECT SUM(hours) as t FROM attendance WHERE worker_id=$1 AND TO_CHAR(date, 'YYYY-MM')=$2", worker['id'], month)
    a_data = await execute_query("SELECT SUM(amount) as t FROM advances WHERE worker_id=$1 AND TO_CHAR(date, 'YYYY-MM')=$2 AND approved=TRUE", worker['id'], month)
    
    total_hours = float(h_data[0]['t']) if h_data and h_data[0]['t'] else 0.0
    total_adv = float(a_data[0]['t']) if a_data and a_data[0]['t'] else 0.0
    
    return {
        "name": worker['name'],
        "rate": float(worker['rate']),
        "hours": total_hours,
        "advance": total_adv
    }
