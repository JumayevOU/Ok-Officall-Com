import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from database.models import create_tables
from handlers import admin, worker, other
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

async def send_reminder(bot: Bot):
    aid = os.getenv("ADMIN_ID")
    if aid:
        try: await bot.send_message(chat_id=aid, text="⏰ <b>Eslatma:</b> Hisobotni kiritish vaqti bo'ldi!")
        except: pass

async def main():
    logging.basicConfig(level=logging.INFO)
    await create_tables()
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher()
    dp.include_router(admin.router)
    dp.include_router(worker.router)
    dp.include_router(other.router)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_reminder, 'cron', hour=15, minute=0, args=[bot])
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())