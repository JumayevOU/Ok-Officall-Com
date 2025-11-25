import asyncpg
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from contextlib import asynccontextmanager

# Logger sozlamalari
logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Ma'lumotlar bazasi ulanishlarini boshqarish klassi"""
    
    _pool: Optional[asyncpg.pool.Pool] = None
    
    @classmethod
    async def get_pool(cls):
        """Connection poolni yaratish"""
        if cls._pool is None:
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                raise ValueError("DATABASE_URL muhit o'zgaruvchisi topilmadi")
            
            cls._pool = await asyncpg.create_pool(
                db_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("✅ Connection pool yaratildi")
        return cls._pool

    @classmethod
    @asynccontextmanager
    async def get_connection(cls):
        """Context manager orqali xavfsiz ulanish olish"""
        pool = await cls.get_pool()
        connection = await pool.acquire()
        try:
            yield connection
        finally:
            await pool.release(connection)

    @classmethod
    async def close_pool(cls):
        """Poolni yopish"""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("✅ Connection pool yopildi")

async def execute_query(query: str, *args) -> Optional[asyncpg.Record]:
    """Xavfsiz so'rov bajarish"""
    try:
        async with DatabaseConnection.get_connection() as conn:
            return await conn.execute(query, *args)
    except asyncpg.PostgresError as e:
        logger.error(f"❌ So'rov bajarishda xatolik: {e}\nSo'rov: {query}")
        return None

async def fetch_row(query: str, *args) -> Optional[asyncpg.Record]:
    """Bitta qator o'qish"""
    try:
        async with DatabaseConnection.get_connection() as conn:
            return await conn.fetchrow(query, *args)
    except asyncpg.PostgresError as e:
        logger.error(f"❌ Qator o'qishda xatolik: {e}\nSo'rov: {query}")
        return None

async def fetch_all(query: str, *args) -> List[asyncpg.Record]:
    """Barcha qatorlarni o'qish"""
    try:
        async with DatabaseConnection.get_connection() as conn:
            return await conn.fetch(query, *args)
    except asyncpg.PostgresError as e:
        logger.error(f"❌ Ma'lumotlarni o'qishda xatolik: {e}\nSo'rov: {query}")
        return []

# --- VALIDATION FUNCTIONS ---

def validate_worker_data(name: str, rate: float, code: int, location: str) -> Tuple[bool, str]:
    """Ishchi ma'lumotlarini tekshirish"""
    if not name or len(name.strip()) < 2:
        return False, "Ism kamida 2 belgidan iborat bo'lishi kerak"
    if rate < 0:
        return False, "Stavka manfiy bo'lishi mumkin emas"
    if code <= 0:
        return False, "Kod musbat son bo'lishi kerak"
    if not location or len(location.strip()) < 2:
        return False, "Lokatsiya kamida 2 belgidan iborat bo'lishi kerak"
    return True, ""

def validate_attendance_data(hours: float, status: str) -> Tuple[bool, str]:
    """Davomat ma'lumotlarini tekshirish"""
    if hours < 0 or hours > 24:
        return False, "Soatlar 0 va 24 oralig'ida bo'lishi kerak"
    valid_statuses = ['present', 'absent', 'late', 'vacation']
    if status not in valid_statuses:
        return False, f"Status quyidagilardan biri bo'lishi kerak: {', '.join(valid_statuses)}"
    return True, ""

# --- ADMIN BO'LIMI ---

async def add_worker(name: str, rate: float, code: int, location: str) -> Tuple[bool, str]:
    """Yangi ishchi qo'shish"""
    # Validatsiya
    is_valid, error_msg = validate_worker_data(name, rate, code, location)
    if not is_valid:
        return False, error_msg

    try:
        async with DatabaseConnection.get_connection() as conn:
            await conn.execute(
                "INSERT INTO workers (name, rate, code, location) VALUES ($1, $2, $3, $4)",
                name.strip(), float(rate), int(code), location.strip()
            )
            logger.info(f"✅ Yangi ishchi qo'shildi: {name} (Kod: {code})")
            return True, "Ishchi muvaffaqiyatli qo'shildi"
    except asyncpg.UniqueViolationError:
        error_msg = f"❌ {code} kodli ishchi allaqachon mavjud"
        logger.warning(error_msg)
        return False, error_msg
    except asyncpg.PostgresError as e:
        error_msg = f"❌ Ishchi qo'shishda xatolik: {e}"
        logger.error(error_msg)
        return False, error_msg

async def get_active_workers() -> List[Dict[str, Any]]:
    """Faol ishchilarni olish"""
    rows = await fetch_all(
        "SELECT id, name, rate, code, location FROM workers WHERE active=TRUE ORDER BY location, name"
    )
    return [dict(row) for row in rows]

async def archive_worker(worker_id: int) -> Tuple[bool, str]:
    """Ishchini arxivlash"""
    try:
        async with DatabaseConnection.get_connection() as conn:
            result = await conn.execute(
                "UPDATE workers SET active=FALSE, updated_at=CURRENT_TIMESTAMP WHERE id=$1",
                int(worker_id)
            )
            
            if "UPDATE 1" in result:
                logger.info(f"✅ Ishchi arxivlandi (ID: {worker_id})")
                return True, "Ishchi muvaffaqiyatli arxivlandi"
            else:
                logger.warning(f"⚠️ Ishchi topilmadi (ID: {worker_id})")
                return False, "Ishchi topilmadi"
    except asyncpg.PostgresError as e:
        error_msg = f"❌ Ishchini arxivlashda xatolik: {e}"
        logger.error(error_msg)
        return False, error_msg

async def add_attendance(worker_id: int, hours: float, status: str) -> Tuple[bool, str]:
    """Davomat qo'shish"""
    # Validatsiya
    is_valid, error_msg = validate_attendance_data(hours, status)
    if not is_valid:
        return False, error_msg

    try:
        date = datetime.now().date()
        async with DatabaseConnection.get_connection() as conn:
            # Transaction boshlash
            async with conn.transaction():
                # Dublikatni oldini olish
                await conn.execute(
                    "DELETE FROM attendance WHERE worker_id=$1 AND date=$2",
                    worker_id, date
                )
                await conn.execute(
                    "INSERT INTO attendance (worker_id, date, hours, status) VALUES ($1, $2, $3, $4)",
                    worker_id, date, hours, status
                )
                
                logger.info(f"✅ Davomat qo'shildi (Ishchi ID: {worker_id}, Sana: {date})")
                return True, "Davomat muvaffaqiyatli qo'shildi"
    except asyncpg.PostgresError as e:
        error_msg = f"❌ Davomat qo'shishda xatolik: {e}"
        logger.error(error_msg)
        return False, error_msg

async def add_advance_money(worker_id: int, amount: float) -> Tuple[bool, str]:
    """Avans qo'shish"""
    if amount <= 0:
        return False, "Avans miqdori musbat son bo'lishi kerak"

    try:
        date = datetime.now().date()
        async with DatabaseConnection.get_connection() as conn:
            await conn.execute(
                "INSERT INTO advances (worker_id, date, amount, description) VALUES ($1, $2, $3, $4)",
                worker_id, date, amount, f"Avans - {date}"
            )
            logger.info(f"✅ Avans qo'shildi (Ishchi ID: {worker_id}, Miqdor: {amount})")
            return True, "Avans muvaffaqiyatli qo'shildi"
    except asyncpg.PostgresError as e:
        error_msg = f"❌ Avans qo'shishda xatolik: {e}"
        logger.error(error_msg)
        return False, error_msg

# --- ISHCHI LOGIN ---

async def verify_login(code: int, telegram_id: int) -> Tuple[bool, str]:
    """Login tekshirish"""
    try:
        worker = await fetch_row("SELECT * FROM workers WHERE code=$1", int(code))
        
        if not worker:
            return False, "Kod noto'g'ri!"

        worker_id = worker['id']
        existing_telegram_id = worker['telegram_id']

        if existing_telegram_id is None:
            # Yangi telegram_id qo'shish
            async with DatabaseConnection.get_connection() as conn:
                await conn.execute(
                    "UPDATE workers SET telegram_id=$1, updated_at=CURRENT_TIMESTAMP WHERE id=$2",
                    telegram_id, worker_id
                )
            logger.info(f"✅ Yangi Telegram ID bog'landi (Ishchi ID: {worker_id})")
            return True, worker['name']
        elif existing_telegram_id == telegram_id:
            # Telegram ID mos keladi
            return True, worker['name']
        else:
            # Telegram ID boshqaga tegishli
            logger.warning(f"⚠️ Bog'langan Telegram ID (Kod: {code}, Telegram ID: {telegram_id})")
            return False, "Bu kod boshqa odam tomonidan band qilingan!"
            
    except asyncpg.PostgresError as e:
        error_msg = f"❌ Login tekshirishda xatolik: {e}"
        logger.error(error_msg)
        return False, "Tizim xatosi. Iltimos, keyinroq urinib ko'ring."

async def get_worker_stats(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Ishchi statistikasini olish"""
    try:
        worker = await fetch_row(
            "SELECT id, name, rate, location FROM workers WHERE telegram_id=$1 AND active=TRUE", 
            telegram_id
        )
        
        if not worker:
            return None

        current_month = datetime.now().strftime("%Y-%m")
        worker_id = worker['id']

        # Soatlar yig'indisi
        hours_result = await fetch_row("""
            SELECT COALESCE(SUM(hours), 0) as total_hours 
            FROM attendance 
            WHERE worker_id=$1 AND TO_CHAR(date, 'YYYY-MM') = $2
        """, worker_id, current_month)

        # Avanslar yig'indisi
        advances_result = await fetch_row("""
            SELECT COALESCE(SUM(amount), 0) as total_adv 
            FROM advances 
            WHERE worker_id=$1 AND TO_CHAR(date, 'YYYY-MM') = $2
        """, worker_id, current_month)

        # Joriy oyning ish kunlari
        work_days_result = await fetch_row("""
            SELECT COUNT(DISTINCT date) as work_days 
            FROM attendance 
            WHERE worker_id=$1 AND TO_CHAR(date, 'YYYY-MM') = $2 AND status != 'absent'
        """, worker_id, current_month)

        return {
            "name": worker['name'],
            "rate": float(worker['rate']),
            "location": worker['location'],
            "hours": float(hours_result['total_hours']) if hours_result else 0,
            "advance": float(advances_result['total_adv']) if advances_result else 0,
            "work_days": work_days_result['work_days'] if work_days_result else 0,
            "total_salary": float(worker['rate']) * float(hours_result['total_hours'] if hours_result else 0)
        }
    except asyncpg.PostgresError as e:
        logger.error(f"❌ Statistikani olishda xatolik: {e}")
        return None

# --- EXCEL REPORT UCHUN ---

async def get_all_workers_report() -> List[Dict[str, Any]]:
    """Hisobot uchun barcha ishchilarni olish"""
    rows = await fetch_all(
        "SELECT id, name, rate, code, location FROM workers WHERE active=TRUE ORDER BY location, name"
    )
    return [dict(row) for row in rows]

async def get_month_attendance(year: int, month: int) -> List[Dict[str, Any]]:
    """Oy davomidagi davomatni olish"""
    try:
        date_filter = f"{year}-{month:02d}"
        rows = await fetch_all("""
            SELECT worker_id, TO_CHAR(date, 'YYYY-MM-DD') as date_str, hours, status
            FROM attendance 
            WHERE TO_CHAR(date, 'YYYY-MM') = $1
            ORDER BY worker_id, date_str
        """, date_filter)
        return [dict(row) for row in rows]
    except asyncpg.PostgresError as e:
        logger.error(f"❌ Davomat ma'lumotlarini olishda xatolik: {e}")
        return []

async def get_month_advances(year: int, month: int) -> List[Dict[str, Any]]:
    """Oy davomidagi avanslarni olish"""
    try:
        date_filter = f"{year}-{month:02d}"
        rows = await fetch_all("""
            SELECT worker_id, SUM(amount) as total 
            FROM advances 
            WHERE TO_CHAR(date, 'YYYY-MM') = $1 
            GROUP BY worker_id
            ORDER BY worker_id
        """, date_filter)
        return [dict(row) for row in rows]
    except asyncpg.PostgresError as e:
        logger.error(f"❌ Avans ma'lumotlarini olishda xatolik: {e}")
        return []

# --- QO'SHIMCHA FUNCTIONS ---

async def get_worker_by_id(worker_id: int) -> Optional[Dict[str, Any]]:
    """ID bo'yicha ishchini olish"""
    worker = await fetch_row(
        "SELECT id, name, rate, code, location, active FROM workers WHERE id=$1", 
        worker_id
    )
    return dict(worker) if worker else None

async def update_worker(worker_id: int, name: str, rate: float, location: str) -> Tuple[bool, str]:
    """Ishchi ma'lumotlarini yangilash"""
    try:
        async with DatabaseConnection.get_connection() as conn:
            result = await conn.execute(
                "UPDATE workers SET name=$1, rate=$2, location=$3, updated_at=CURRENT_TIMESTAMP WHERE id=$4",
                name, rate, location, worker_id
            )
            
            if "UPDATE 1" in result:
                logger.info(f"✅ Ishchi yangilandi (ID: {worker_id})")
                return True, "Ishchi ma'lumotlari muvaffaqiyatli yangilandi"
            else:
                return False, "Ishchi topilmadi"
    except asyncpg.PostgresError as e:
        error_msg = f"❌ Ishchini yangilashda xatolik: {e}"
        logger.error(error_msg)
        return False, error_msg

# Dastur tugaganda poolni yopish
import atexit
import asyncio

async def _close_db_pool():
    await DatabaseConnection.close_pool()

def cleanup():
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(_close_db_pool())
    else:
        loop.run_until_complete(_close_db_pool())

atexit.register(cleanup)