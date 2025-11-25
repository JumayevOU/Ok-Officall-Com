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
    
    print("Bazaga ulanilmoqda...")
    try:
        await create_tables()
        print("✅ Baza ulandi va jadvallar tekshirildi.")
    except Exception as e:
        print(f"❌ Bazaga ulanishda xatolik: {e}")
        return

    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher()

    dp.include_router(admin.router)
    dp.include_router(worker.router)
    dp.include_router(other.router) 

    print("🚀 Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())