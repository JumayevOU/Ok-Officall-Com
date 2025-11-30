from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from utils.keyboards import admin_main_kb, worker_main_kb, remove_kb
from utils.states import WorkerLogin
from database import requests as db
import os
import logging
from typing import Dict, List

router = Router()

# --- ADMINLAR RO'YXATINI OLISH (MULTI-ADMIN) ---
ADMIN_LIST: List[int] = []
try:
    env_admins = os.getenv("ADMIN_ID", "")
    ADMIN_LIST = [int(id_str.strip()) for id_str in env_admins.split(",") if id_str.strip()]
except (ValueError, TypeError):
    logging.warning("ADMIN_ID to'g'ri o'rnatilmagan")

# Login urinishlari
login_attempts: Dict[int, int] = {}

def format_bold(text: str) -> str:
    """Matnni qalin qilish"""
    bold_map = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳"
    )
    return text.translate(bold_map)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Start komandasi"""
    user_id = message.from_user.id
    
    # Login urinishlarini tozalash
    if user_id in login_attempts:
        del login_attempts[user_id]
    
    # Admin tekshiruvi (Multi-Admin)
    if user_id in ADMIN_LIST:
        welcome_text = (
            f"👑 {format_bold('ADMIN PANELI')}\n\n"
            f"🛠️ <b>Boshqaruv paneliga xush kelibsiz!</b>\n"
            f"Quyidagi menyular orqali tizimni boshqarishingiz mumkin:"
        )
        await message.answer(welcome_text, reply_markup=admin_main_kb())
        await state.clear()
        return
    
    # Ishchi uchun login sahifasi
    welcome_text = (
        f"🔐 {format_bold('TIZIMGA KIRISH')}\n"
        f"────────────────\n\n"
        f"👋 Assalomu alaykum!\n"
        f"📋 <b>Ishchi hisobiga kirish</b>\n\n"
        f"🆔 Iltimos, <b>shaxsiy kodingizni</b> kiriting:"
    )
    
    await message.answer(welcome_text, reply_markup=remove_kb)
    await state.set_state(WorkerLogin.enter_code)

@router.message(WorkerLogin.enter_code)
async def process_login_code(message: Message, state: FSMContext):
    """Login kodini tekshirish"""
    user_id = message.from_user.id
    
    # Urinishlar sonini tekshirish
    attempts = login_attempts.get(user_id, 0) + 1
    login_attempts[user_id] = attempts
    
    if attempts > 3:
        await message.answer(
            "🚫 <b>Juda ko'p noto'g'ri urinish!</b>\n\n"
            "Iltimos, 10 daqiqadan keyin qayta urinib ko'ring."
        )
        await state.clear()
        return
    
    # Kodni tekshirish
    code = message.text.strip()
    success, result = await db.verify_login(code, user_id)
    
    if success:
        # Muvaffaqiyatli login
        welcome_text = (
            f"✅ {format_bold('MUVAFFAQIYATLI KIRISH')}\n"
            f"────────────────\n\n"
            f"🎉 Xush kelibsiz, <b>{result}</b>!\n"
            f"📊 Endi siz shaxsiy hisobingizga kirdingiz."
        )
        await message.answer(welcome_text, reply_markup=worker_main_kb())
        
        # Urinishlarni tozalash
        if user_id in login_attempts:
            del login_attempts[user_id]
            
        await state.clear()
    else:
        # Xato xabari
        remaining_attempts = 3 - attempts
        error_text = (
            f"❌ {format_bold('KIRISH XATOSI')}\n"
            f"────────────────\n\n"
            f"<b>{result}</b>\n\n"
        )
        
        if remaining_attempts > 0:
            error_text += f"♻️ Qayta urinish: <b>{remaining_attempts}</b> ta qoldi"
        else:
            error_text += "⏰ Iltimos, keyinroq qayta urinib ko'ring"
        
        await message.answer(error_text)
        
        if attempts >= 3:
            await state.clear()

@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: Message, state: FSMContext):
    """Bekor qilish handleri - barcha state lar uchun"""
    current_state = await state.get_state()
    
    # Admin tekshiruvi (Multi-Admin)
    user_id = message.from_user.id
    is_admin_user = user_id in ADMIN_LIST

    if current_state is None:
        # Agar state bo'lmasa, oddiy menyuni ko'rsatish
        if is_admin_user:
            await message.answer("🏠 <b>Asosiy menyu</b>", reply_markup=admin_main_kb())
        else:
            await message.answer("🏠 <b>Asosiy menyu</b>", reply_markup=worker_main_kb())
        return
    
    # State ni tozalash
    await state.clear()
    
    # Foydalanuvchi turiga qarab javob berish
    if is_admin_user:
        await message.answer("✅ <b>Amal bekor qilindi</b>", reply_markup=admin_main_kb())
    else:
        await message.answer("✅ <b>Amal bekor qilindi</b>", reply_markup=worker_main_kb())
