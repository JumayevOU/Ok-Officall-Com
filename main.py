import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from database.models import create_tables
from handlers import admin, worker, other

load_dotenv()

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 Bot ishga tushirilmoqda...")
    
    # 1. Baza jadvallarini tekshirish
    await create_tables()

    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ XATOLIK: .env faylida BOT_TOKEN yo'q!")
        return

    bot = Bot(token=token)
    dp = Dispatcher()
    
    # 2. Routerlarni ulash
    dp.include_router(admin.router)
    dp.include_router(worker.router)
    dp.include_router(other.router)

    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())