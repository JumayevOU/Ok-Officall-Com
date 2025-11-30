import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enum import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from database.models import create_db_pool, create_tables, close_db_pool
from handlers import admin, worker, other
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import signal
import sys

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class WorkforceBot:
    def __init__(self):
        self.bot = None
        self.dp = None
        self.scheduler = None
        
    async def startup(self):
        """Botni ishga tushirish"""
        logger.info("🚀 Workforce Bot ishga tushmoqda...")
        
        # Database pool yaratish
        db_pool = await create_db_pool()
        if not db_pool:
            logger.error("❌ Database bilan ulanishda xatolik!")
            return False
        
        # Database jadvallarini yaratish
        success = await create_tables()
        if not success:
            logger.error("❌ Jadvallarni yaratishda xatolik!")
            return False
        
        # Botni yaratish
        token = os.getenv("BOT_TOKEN")
        if not token:
            logger.error("❌ BOT_TOKEN topilmadi!")
            return False
        
        self.bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Dispatcher yaratish
        storage = MemoryStorage()
        self.dp = Dispatcher(storage=storage)
        
        # Routerlarni qo'shish
        self.dp.include_router(admin.router)
        self.dp.include_router(worker.router)
        self.dp.include_router(other.router)
        
        # Scheduler ni sozlash
        self.scheduler = AsyncIOScheduler()
        self._setup_scheduler()
        
        logger.info("✅ Bot muvaffaqiyatli ishga tushirildi!")
        return True
    
    def _setup_scheduler(self):
        """Planlashtiruvchini sozlash"""
        # Har kuni soat 18:00 da eslatma
        self.scheduler.add_job(
            self._send_daily_reminder,
            CronTrigger(hour=18, minute=0),
            id='daily_reminder'
        )
        
        # Har yakshanba soat 10:00 da haftalik eslatma
        self.scheduler.add_job(
            self._send_weekly_report_reminder,
            CronTrigger(day_of_week=0, hour=10, minute=0),
            id='weekly_reminder'
        )
    
    async def _send_daily_reminder(self):
        """Kunlik eslatma yuborish"""
        try:
            admin_id = os.getenv("ADMIN_ID")
            if admin_id and self.bot:
                await self.bot.send_message(
                    chat_id=int(admin_id),
                    text="⏰ <b>Kunlik eslatma</b>\n\n"
                         "📝 Bugungi hisobotni kiritishni unutmang!\n"
                         "💰 Yangi avans so'rovlari bo'lsa tekshiring."
                )
                logger.info("✅ Kunlik eslatma yuborildi")
        except Exception as e:
            logger.error(f"❌ Eslatma yuborishda xato: {e}")
    
    async def _send_weekly_report_reminder(self):
        """Haftalik eslatma yuborish"""
        try:
            admin_id = os.getenv("ADMIN_ID")
            if admin_id and self.bot:
                await self.bot.send_message(
                    chat_id=int(admin_id),
                    text="📊 <b>Haftalik eslatma</b>\n\n"
                         "📈 O'tgan hafta statistikasini ko'rib chiqing.\n"
                         "📥 Excel hisobot tayyorlang.\n"
                         "👥 Yangi ishchilar qo'shish kerakmi?"
                )
                logger.info("✅ Haftalik eslatma yuborildi")
        except Exception as e:
            logger.error(f"❌ Haftalik eslatma yuborishda xato: {e}")
    
    async def shutdown(self):
        """Botni to'xtatish"""
        logger.info("🛑 Bot to'xtatilmoqda...")
        
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("✅ Scheduler to'xtatildi")
        
        if self.bot:
            await self.bot.session.close()
            logger.info("✅ Bot sessiyasi yopildi")
        
        await close_db_pool()
        logger.info("✅ Database pool yopildi")
        
        logger.info("👋 Bot to'liq to'xtatildi")

async def main():
    """Asosiy dastur"""
    bot = WorkforceBot()
    
    # Signal handlers
    def signal_handler(signum, frame):
        logger.info(f"📞 Signal qabul qilindi: {signum}")
        asyncio.create_task(bot.shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Botni ishga tushirish
        success = await bot.startup()
        if not success:
            logger.error("❌ Botni ishga tushirib bo'lmadi!")
            return
        
        # Scheduler ni ishga tushirish
        bot.scheduler.start()
        logger.info("✅ Scheduler ishga tushirildi")
        
        # Botni ishga tushirish
        await bot.dp.start_polling(bot.bot)
        
    except Exception as e:
        logger.error(f"❌ Botda xatolik yuz berdi: {e}")
    
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    # Asyncio event loop ni ishga tushirish
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot foydalanuvchi tomonidan to'xtatildi")
    except Exception as e:
        logger.error(f"❌ Kutilmagan xatolik: {e}")