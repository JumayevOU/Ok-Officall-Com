import asyncpg
import os
import logging
from typing import Optional

# Logger sozlamalari
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Ma'lumotlar bazasi boshqaruvchi klassi"""
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self._connection: Optional[asyncpg.Connection] = None
    
    async def _get_connection(self) -> asyncpg.Connection:
        """Xavfsiz ulanishni olish"""
        if not self.db_url:
            raise ValueError("DATABASE_URL muhit o'zgaruvchisi topilmadi")
        
        if not self._connection or self._connection.is_closed():
            self._connection = await asyncpg.connect(self.db_url)
        
        return self._connection
    
    async def _safe_execute(self, query: str, *args) -> bool:
        """Xavfsiz execute funksiyasi"""
        try:
            conn = await self._get_connection()
            await conn.execute(query, *args)
            return True
        except Exception as e:
            logger.error(f"SQL bajarishda xatolik: {e}\nSo'rov: {query}")
            return False
    
    async def _check_table_exists(self, table_name: str) -> bool:
        """Jadval mavjudligini tekshirish"""
        try:
            conn = await self._get_connection()
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = $1
                );
            """, table_name)
            return result
        except Exception as e:
            logger.error(f"Jadval mavjudligini tekshirishda xatolik: {e}")
            return False
    
    async def _add_column_if_not_exists(self, table: str, column: str, column_type: str) -> bool:
        """Agar ustun mavjud bo'lmasa, qo'shish"""
        try:
            conn = await self._get_connection()
            await conn.execute(f"""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = '{table}' AND column_name = '{column}'
                    ) THEN
                        ALTER TABLE {table} ADD COLUMN {column} {column_type};
                    END IF;
                END $$;
            """)
            logger.info(f"✅ '{table}.{column}' ustuni muvaffaqiyatli tekshirildi/qo'shildi.")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Ustun qo'shishda xatolik: {e}")
            return False

async def create_tables():
    """Jadvallarni yaratish va migratsiya qilish"""
    db_manager = DatabaseManager()
    
    # DATABASE_URL tekshiruvi
    if not db_manager.db_url:
        logger.critical("❌ DATABASE_URL topilmadi! .env faylni tekshiring.")
        return False

    try:
        conn = await db_manager._get_connection()
        
        # 1. Workers jadvali
        workers_success = await db_manager._safe_execute("""
            CREATE TABLE IF NOT EXISTS workers(
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                rate REAL NOT NULL CHECK (rate >= 0),
                code INTEGER UNIQUE NOT NULL,
                telegram_id BIGINT UNIQUE,
                location TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        if workers_success:
            # Workers jadvali migratsiyalari
            await db_manager._add_column_if_not_exists("workers", "location", "TEXT")
            await db_manager._add_column_if_not_exists("workers", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            await db_manager._add_column_if_not_exists("workers", "updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            
            # Indexlar
            await db_manager._safe_execute("CREATE INDEX IF NOT EXISTS idx_workers_code ON workers(code)")
            await db_manager._safe_execute("CREATE INDEX IF NOT EXISTS idx_workers_telegram_id ON workers(telegram_id)")
            await db_manager._safe_execute("CREATE INDEX IF NOT EXISTS idx_workers_active ON workers(active)")

        # 2. Attendance jadvali
        attendance_success = await db_manager._safe_execute("""
            CREATE TABLE IF NOT EXISTS attendance(
                id SERIAL PRIMARY KEY,
                worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
                date DATE NOT NULL,
                hours REAL NOT NULL CHECK (hours >= 0 AND hours <= 24),
                status TEXT NOT NULL CHECK (status IN ('present', 'absent', 'late', 'vacation')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(worker_id, date)
            )
        """)
        
        if attendance_success:
            await db_manager._add_column_if_not_exists("attendance", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            await db_manager._safe_execute("CREATE INDEX IF NOT EXISTS idx_attendance_worker_id ON attendance(worker_id)")
            await db_manager._safe_execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)")

        # 3. Advances jadvali
        advances_success = await db_manager._safe_execute("""
            CREATE TABLE IF NOT EXISTS advances(
                id SERIAL PRIMARY KEY,
                worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
                date DATE NOT NULL,
                amount REAL NOT NULL CHECK (amount >= 0),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        if advances_success:
            await db_manager._add_column_if_not_exists("advances", "description", "TEXT")
            await db_manager._add_column_if_not_exists("advances", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            await db_manager._safe_execute("CREATE INDEX IF NOT EXISTS idx_advances_worker_id ON advances(worker_id)")
            await db_manager._safe_execute("CREATE INDEX IF NOT EXISTS idx_advances_date ON advances(date)")

        # Ulanishni yopish
        if conn and not conn.is_closed():
            await conn.close()

        # Natijani log qilish
        if all([workers_success, attendance_success, advances_success]):
            logger.info("✅ Baza jadvallari to'liq tekshirildi va migratsiya bajarildi.")
            return True
        else:
            logger.error("❌ Ba'zi jadvallar yaratilmadi")
            return False

    except ValueError as ve:
        logger.critical(f"❌ Konfiguratsiya xatosi: {ve}")
        return False
    except asyncpg.PostgresConnectionError as pce:
        logger.critical(f"❌ PostgreSQL ulanish xatosi: {pce}")
        return False
    except asyncpg.PostgresError as pe:
        logger.critical(f"❌ PostgreSQL xatosi: {pe}")
        return False
    except Exception as e:
        logger.critical(f"❌ Kutilmagan xatolik: {e}")
        return False
    finally:
        # Har doim ulanishni yopishni tekshirish
        try:
            if db_manager._connection and not db_manager._connection.is_closed():
                await db_manager._connection.close()
        except Exception as e:
            logger.error(f"⚠️ Ulanishni yopishda xatolik: {e}")

# Qo'shimcha funksiya: Baza holatini tekshirish
async def check_database_health() -> bool:
    """Ma'lumotlar bazasi holatini tekshirish"""
    try:
        db_manager = DatabaseManager()
        conn = await db_manager._get_connection()
        
        # Oddiy so'rov orqali ulanishni tekshirish
        result = await conn.fetchval("SELECT 1")
        
        # Asosiy jadvallarni tekshirish
        tables = ['workers', 'attendance', 'advances']
        for table in tables:
            exists = await db_manager._check_table_exists(table)
            if not exists:
                logger.warning(f"⚠️ {table} jadvali topilmadi")
                return False
        
        await conn.close()
        logger.info("✅ Baza holati yaxshi")
        return True
        
    except Exception as e:
        logger.error(f"❌ Baza holati tekshirishida xatolik: {e}")
        return False