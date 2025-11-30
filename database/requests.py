import asyncpg
import os
import logging
from datetime import datetime, date
import calendar
from typing import List, Dict, Any, Optional
from database import models

class DatabaseError(Exception):
    """Maxsus database xatoliklari"""
    pass

async def execute_query(query: str, *args) -> Any:
    """Umumiy so'rovni bajarish - DB_POOL bilan"""
    if not DB_POOL:
        raise DatabaseError("Database pool mavjud emas")
    
    try:
        async with DB_POOL.acquire() as conn:
            if query.strip().upper().startswith('SELECT'):
                result = await conn.fetch(query, *args)
            else:
                result = await conn.execute(query, *args)
            return result
    except Exception as e:
        logging.error(f"Database xatosi: {e} - So'rov: {query}")
        raise DatabaseError(f"Database xatosi: {e}")

# --- ISHCHILAR BO'LIMI ---
async def add_worker(name: str, rate: float, code: int) -> bool:
    """Yangi ishchi qo'shish"""
    try:
        # Kod takrorlanmasligini tekshirish
        existing = await execute_query("SELECT id FROM workers WHERE code = $1", code)
        if existing:
            logging.error(f"Kod allaqachon mavjud: {code}")
            return False
        
        await execute_query(
            "INSERT INTO workers (name, rate, code, active) VALUES ($1, $2, $3, $4)", 
            name.strip(), float(rate), int(code), True
        )
        return True
    except Exception as e:
        logging.error(f"add_worker xatosi: {e}")
        return False

async def update_worker_field(worker_id: int, field: str, value: Any) -> bool:
    """Ishchi ma'lumotlarini yangilash"""
    valid_fields = ['name', 'rate']
    if field not in valid_fields:
        return False
    
    try:
        await execute_query(f"UPDATE workers SET {field} = $1 WHERE id = $2", value, worker_id)
        return True
    except Exception as e:
        logging.error(f"update_worker_field xatosi: {e}")
        return False

async def archive_worker(worker_id: int) -> bool:
    """Ishchini arxivlash"""
    try:
        await execute_query(
            "UPDATE workers SET active = FALSE, archived_at = CURRENT_DATE WHERE id = $1",
            worker_id
        )
        return True
    except Exception as e:
        logging.error(f"archive_worker xatosi: {e}")
        return False

async def get_active_workers() -> List[Dict[str, Any]]:
    """Faol ishchilar ro'yxati"""
    try:
        rows = await execute_query("""
            SELECT id, name, rate, code
            FROM workers 
            WHERE active = TRUE 
            ORDER BY name
        """)
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"get_active_workers xatosi: {e}")
        return []

async def search_worker_by_name(search_text: str) -> List[Dict[str, Any]]:
    """Ism bo'yicha ishchi qidirish"""
    try:
        rows = await execute_query("""
            SELECT id, name, code
            FROM workers 
            WHERE active = TRUE AND name ILIKE $1
            ORDER BY name
        """, f"%{search_text.strip()}%")
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"search_worker_by_name xatosi: {e}")
        return []

async def get_worker_by_id(worker_id: int) -> Optional[Dict[str, Any]]:
    """ID bo'yicha ishchi ma'lumotlari"""
    try:
        rows = await execute_query("SELECT * FROM workers WHERE id = $1", worker_id)
        return dict(rows[0]) if rows else None
    except Exception as e:
        logging.error(f"get_worker_by_id xatosi: {e}")
        return None

async def get_worker_by_code(code: int) -> Optional[Dict[str, Any]]:
    """Kod bo'yicha ishchi ma'lumotlari"""
    try:
        rows = await execute_query("SELECT * FROM workers WHERE code = $1", code)
        return dict(rows[0]) if rows else None
    except Exception as e:
        logging.error(f"get_worker_by_code xatosi: {e}")
        return None

# --- DAVOMAT BO'LIMI ---
async def add_attendance(worker_id: int, hours: float, status: str = "Keldi") -> bool:
    """Davomat qo'shish/yangilash"""
    try:
        await execute_query("""
            INSERT INTO attendance (worker_id, date, hours, status) 
            VALUES ($1, CURRENT_DATE, $2, $3)
            ON CONFLICT (worker_id, date) 
            DO UPDATE SET hours = EXCLUDED.hours, status = EXCLUDED.status
        """, worker_id, float(hours), status)
        return True
    except Exception as e:
        logging.error(f"add_attendance xatosi: {e}")
        return False

async def add_advance(worker_id: int, amount: float, approved: bool = True) -> bool:
    """Avans qo'shish"""
    try:
        await execute_query(
            "INSERT INTO advances (worker_id, date, amount, approved) VALUES ($1, CURRENT_DATE, $2, $3)",
            worker_id, float(amount), approved
        )
        return True
    except Exception as e:
        logging.error(f"add_advance xatosi: {e}")
        return False

async def get_month_data(year: int, month: int) -> tuple:
    """Oy ma'lumotlarini olish"""
    try:
        date_filter = f"{year}-{month:02d}"
        
        attendance = await execute_query("""
            SELECT worker_id, TO_CHAR(date, 'YYYY-MM-DD') as date_str, hours 
            FROM attendance 
            WHERE TO_CHAR(date, 'YYYY-MM') = $1
        """, date_filter)
        
        advances = await execute_query("""
            SELECT worker_id, SUM(amount) as total 
            FROM advances 
            WHERE TO_CHAR(date, 'YYYY-MM') = $1 AND approved = TRUE
            GROUP BY worker_id
        """, date_filter)
        
        return attendance, advances
    except Exception as e:
        logging.error(f"get_month_data xatosi: {e}")
        return [], []

# --- HISOBOT FUNKSIYALARI ---
async def get_workers_for_report(year: int, month: int) -> List[Dict[str, Any]]:
    """Hisobot uchun ishchilar ro'yxati"""
    try:
        last_day = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)
        
        rows = await execute_query("""
            SELECT id, name, rate, code, created_at, archived_at 
            FROM workers 
            WHERE created_at <= $2 
              AND (archived_at IS NULL OR archived_at >= $1)
            ORDER BY name
        """, start_date, end_date)
        
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"get_workers_for_report xatosi: {e}")
        return []

async def get_month_attendance(year: int, month: int):
    """Oy davomati ma'lumotlari"""
    try:
        date_filter = f"{year}-{month:02d}"
        rows = await execute_query("""
            SELECT worker_id, TO_CHAR(date, 'YYYY-MM-DD') as date_str, hours 
            FROM attendance 
            WHERE TO_CHAR(date, 'YYYY-MM') = $1
        """, date_filter)
        return rows
    except Exception as e:
        logging.error(f"get_month_attendance xatosi: {e}")
        return []

async def get_month_advances(year: int, month: int):
    """Oy avanslari ma'lumotlari"""
    try:
        date_filter = f"{year}-{month:02d}"
        rows = await execute_query("""
            SELECT worker_id, SUM(amount) as total 
            FROM advances 
            WHERE TO_CHAR(date, 'YYYY-MM') = $1 AND approved = TRUE
            GROUP BY worker_id
        """, date_filter)
        return rows
    except Exception as e:
        logging.error(f"get_month_advances xatosi: {e}")
        return []

# --- AUTENTIFIKATSIYA ---
async def verify_login(code: str, telegram_id: int) -> tuple:
    """Login tekshirish"""
    try:
        if not code.isdigit():
            return False, "Iltimos, faqat raqam kiriting"
        
        worker = await execute_query("SELECT * FROM workers WHERE code = $1", int(code))
        if not worker:
            return False, "❌ Noto'g'ri kod"
        
        worker = worker[0]
        
        if not worker['active']:
            return False, "❌ Sizning profilingiz aktiv emas"
        
        if worker['telegram_id'] and worker['telegram_id'] != telegram_id:
            return False, "❌ Bu kod allaqachon boshqa foydalanuvchi tomonidan ishlatilmoqda"
        
        # Telegram ID ni yangilash
        await execute_query("UPDATE workers SET telegram_id = $1 WHERE id = $2", telegram_id, worker['id'])
        
        return True, worker['name']
        
    except Exception as e:
        logging.error(f"verify_login xatosi: {e}")
        return False, "❌ Tizim xatosi"

async def get_worker_stats(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Ishchi statistikasi"""
    try:
        worker = await execute_query("""
            SELECT id, name, rate FROM workers WHERE telegram_id = $1 AND active = TRUE
        """, telegram_id)
        
        if not worker:
            return None
        
        worker = worker[0]
        month = datetime.now().strftime("%Y-%m")
        
        hours_data = await execute_query("""
            SELECT COALESCE(SUM(hours), 0) as total_hours 
            FROM attendance 
            WHERE worker_id = $1 AND TO_CHAR(date, 'YYYY-MM') = $2
        """, worker['id'], month)
        
        advance_data = await execute_query("""
            SELECT COALESCE(SUM(amount), 0) as total_advance 
            FROM advances 
            WHERE worker_id = $1 AND TO_CHAR(date, 'YYYY-MM') = $2 AND approved = TRUE
        """, worker['id'], month)
        
        return {
            "name": worker['name'],
            "rate": float(worker['rate']),
            "hours": float(hours_data[0]['total_hours']),
            "advance": float(advance_data[0]['total_advance'])
        }
    except Exception as e:
        logging.error(f"get_worker_stats xatosi: {e}")
        return None
