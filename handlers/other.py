from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from utils.keyboards import admin_main, worker_main
from utils.states import WorkerLogin
from database import requests as db
import os

router = Router()
ADMIN_ID = int(os.getenv("ADMIN_ID"))

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        await message.answer(f"Xush kelibsiz, Xo'jayin! 👨‍💼", reply_markup=admin_main)
    else:
        # Ishchini tekshirish: Bazada bormi?
        # Bu yerda avtomatik tekshiruv qilish mumkin, lekin 
        # birinchi marta kirishda Login so'raymiz
        await message.answer("Assalomu alaykum! Tizimga kirish uchun Admin bergan ID kodni yozing:")
        await state.set_state(WorkerLogin.waiting_code)

@router.message(WorkerLogin.waiting_code)
async def process_login(message: Message, state: FSMContext):
    code = message.text
    if not code.isdigit():
        await message.answer("Iltimos, faqat raqam yozing.")
        return
        
    success, msg = await db.verify_login(code, message.from_user.id)
    if success:
        await message.answer(f"Xush kelibsiz, {msg}! ✅", reply_markup=worker_main)
        await state.clear()
    else:
        await message.answer(f"Xatolik: {msg}\nQaytadan urinib ko'ring:")