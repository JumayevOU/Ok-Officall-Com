from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import requests as db
from utils.keyboards import worker_main, start_kb
import os

router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    
    try:
        ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
        if user_id == ADMIN_ID:
            from utils.keyboards import admin_main
            await message.answer(
                "🏢 Admin Panelga xush kelibsiz!",
                reply_markup=admin_main
            )
            return
    except:
        pass
    
    worker_stats = await db.get_worker_stats(user_id)
    if worker_stats:
        await message.answer(
            f"👷‍♂️ Ishchi paneliga xush kelibsiz!\n\n👤 {worker_stats['name']}",
            reply_markup=worker_main
        )
    else:
        await message.answer(
            "👷‍♂️ Ishchi hisob qaydnomasi\n\nTizimga kirish uchun 3 xonali kirish kodini yuboring:",
            reply_markup=start_kb
        )

@router.message(F.text == "🔑 Kirish kodi")
async def request_login_code(message: Message):
    await message.answer(
        "🔐 Tizimga kirish\n\nIltimos, 3 xonali kirish kodini yuboring:"
    )

@router.message(F.text.regexp(r'^\d{3}$'))
async def process_login_code(message: Message):
    code = int(message.text)
    telegram_id = message.from_user.id
    
    success, result = await db.verify_login(code, telegram_id)
    
    if success:
        worker_stats = await db.get_worker_stats(telegram_id)
        if worker_stats:
            await message.answer(
                f"✅ Xush kelibsiz, {result}!",
                reply_markup=worker_main
            )
    else:
        await message.answer(f"❌ {result}")