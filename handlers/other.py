from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from utils.keyboards import admin_main_kb, worker_main_kb, remove_kb
from utils.states import WorkerLogin
from database import requests as db
import os
import logging
from typing import Dict

router = Router()

# Admin ID ni tekshirish
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
except (ValueError, TypeError):
    ADMIN_ID = 0
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
    
    # Admin tekshiruvi
    if user_id == ADMIN_ID:
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

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Yordam komandasi"""
    help_text = (
        f"🆘 {format_bold('YORDAM')}\n"
        f"────────────────\n\n"
    )
    
    if message.from_user.id == ADMIN_ID:
        help_text += (
            "<b>Admin buyruqlari:</b>\n"
            "• /start - Asosiy menyu\n"
            "• /help - Yordam\n"
            "• /stats - Statistika\n\n"
            "<b>Admin funksiyalari:</b>\n"
            "• 📝 Bugungi hisobot - Davomat kiritish\n"
            "• 📊 Joriy holat - Oylik statistika\n"
            "• 👥 Ishchilar - Ishchilar ro'yxati\n"
            "• 💰 Avans yozish - Ishchilarga avans\n"
            "• 📥 Excel hisobot - Excel formatda yuklab olish\n"
            "• ⚙️ Sozlamalar - Tizim sozlamalari"
        )
    else:
        help_text += (
            "<b>Ishchi buyruqlari:</b>\n"
            "• /start - Asosiy menyu\n"
            "• /help - Yordam\n\n"
            "<b>Ishchi funksiyalari:</b>\n"
            "• 💰 Mening hisobim - Shaxsiy statistika\n"
            "• 💸 Avans so'rash - Avans so'rov yuborish"
        )
    
    await message.answer(help_text)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Statistika komandasi"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Bu buyruq faqat admin uchun!")
        return
    
    # Bu yerda stats logikasini qo'shish mumkin
    stats_text = (
        f"📈 {format_bold('TIZIM STATISTIKASI')}\n"
        f"────────────────\n\n"
        f"🔄 Statistika funksiyasi tez orada qo'shiladi..."
    )
    await message.answer(stats_text)

@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: Message, state: FSMContext):
    """Bekor qilish handleri"""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("⚠️ Hech qanday amal bajarilmagan", reply_markup=admin_main_kb())
        return
    
    await state.clear()
    
    if message.from_user.id == ADMIN_ID:
        await message.answer("✅ Amal bekor qilindi", reply_markup=admin_main_kb())
    else:
        await message.answer("✅ Amal bekor qilindi", reply_markup=worker_main_kb())