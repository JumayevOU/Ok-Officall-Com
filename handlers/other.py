from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from utils.keyboards import admin_main, worker_main
from utils.states import WorkerLogin
from database import requests as db
import os

router = Router()
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
except:
    ADMIN_ID = 0

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        await message.answer(f"👋 **Xush kelibsiz, Xo'jayin!**\nBoshqaruv paneliga marhamat.", reply_markup=admin_main)
    else:
        # Agar user oldin kirgan bo'lsa, uni avtomatik taniy olamiz (bazada telegram_id bor bo'lsa)
        # Hozircha oddiy login:
        await message.answer(
            "🔐 **Tizimga kirish**\n\n"
            "Iltimos, Admindan olgan **ID KOD**ingizni yozing:"
        )
        await state.set_state(WorkerLogin.waiting_code)

@router.message(WorkerLogin.waiting_code)
async def process_login(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Faqat raqam yozing!")
        return
    
    success, msg = await db.verify_login(message.text, message.from_user.id)
    if success:
        await message.answer(f"✅ Xush kelibsiz, **{msg}**!", reply_markup=worker_main)
        await state.clear()
    else:
        await message.answer(f"{msg}\nQaytadan urinib ko'ring:")