from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.keyboards import worker_main_kb, cancel_kb
from utils.states import WorkerAdvance
from database import requests as db
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List

router = Router()

# --- ADMINLAR RO'YXATI (Multi-Admin) ---
ADMIN_LIST: List[int] = []
try:
    env_admins = os.getenv("ADMIN_ID", "")
    ADMIN_LIST = [int(id_str.strip()) for id_str in env_admins.split(",") if id_str.strip()]
except (ValueError, TypeError):
    logging.warning("ADMIN_ID worker.py da to'g'ri o'qilmadi")

# Avans so'rovlari
advance_requests: Dict[int, float] = {}

# Oylar tarjimasi
MONTHS = {
    1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
    5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
    9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr"
}

def format_bold(text: str) -> str:
    """Matnni qalin qilish"""
    return f"<b>{text}</b>"

def get_tashkent_time():
    """Toshkent vaqti (UTC+5)"""
    return datetime.utcnow() + timedelta(hours=5)

# --- SHAXSIY HISOB ---
@router.message(F.text == "💰 Mening hisobim")
async def show_worker_stats(message: Message):
    """Ishchi statistikasini ko'rsatish"""
    stats = await db.get_worker_stats(message.from_user.id)
    
    if not stats:
        await message.answer(
            "❌ <b>Ma'lumot topilmadi</b>\n\n"
            "ℹ️ Profilingiz topilmadi yoki hali ma'lumot kiritilmagan."
        )
        return
    
    # Hisob-kitoblar
    salary = stats['hours'] * stats['rate']
    net_salary = salary - stats['advance']
    
    now = get_tashkent_time()
    month_name = MONTHS.get(now.month, str(now.month))
    
    stats_text = (
        f"🧾 {format_bold('SHAXSIY HISOB')}\n"
        f"🗓 {month_name} {now.year}\n"
        f"────────────────\n\n"
        f"👤 <b>{stats['name']}</b>\n"
        f"💎 <b>Soatlik stavka:</b> {stats['rate']:,.0f} so'm\n\n"
        f"📊 <b>Joriy oy statistikasi:</b>\n"
        f"⏱ Ishlangan soat: <b>{stats['hours']}</b>\n"
        f"💵 Hisoblangan: <b>{salary:,.0f} so'm</b>\n"
        f"💸 Avanslar: <b>{stats['advance']:,.0f} so'm</b>\n"
        f"────────────────\n"
        f"💰 <b>Qo'lga tegadi: {net_salary:,.0f} so'm</b>\n\n"
    )
    
    if net_salary < 0:
        stats_text += "⚠️ <i>Avanslar hisoblangan summandan oshib ketgan</i>"
    elif stats['hours'] == 0:
        stats_text += "ℹ️ <i>Hozircha ishlagan soatingiz mavjud emas</i>"
    else:
        stats_text += "✅ <i>Ma'lumotlar joriy oy uchun</i>"
    
    await message.answer(stats_text, reply_markup=worker_main_kb())

# --- AVANS SO'RASH ---
@router.message(F.text == "💸 Avans so'rash")
async def start_advance_request(message: Message, state: FSMContext):
    """Avans so'rovini boshlash"""
    # Avval stats ni tekshirish
    stats = await db.get_worker_stats(message.from_user.id)
    if not stats:
        await message.answer("❌ <b>Profil ma'lumotlari topilmadi</b>")
        return
    
    # Maksimal avans miqdorini hisoblash
    max_advance = (stats['hours'] * stats['rate']) * 0.7  # 70% chegarasi
    
    prompt_text = (
        f"💸 {format_bold('AVANS SO\\'RASH')}\n"
        f"────────────────\n\n"
        f"💰 <b>Qancha avans kerak?</b>\n\n"
    )
    
    if max_advance > 0:
        prompt_text += (
            f"ℹ️ <b>Maksimal ruxsat etilgan:</b> {max_advance:,.0f} so'm\n"
            f"(Joriy ishlaganligingizning 70% i)\n\n"
        )
    
    prompt_text += "<i>Faqat raqam kiriting (so'mda). Masalan: 500000</i>"
    
    await state.set_state(WorkerAdvance.enter_amount)
    await message.answer(prompt_text, reply_markup=cancel_kb)

@router.message(WorkerAdvance.enter_amount)
async def process_advance_request(message: Message, state: FSMContext):
    """Avans so'rov miqdorini qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Amal bekor qilindi", reply_markup=worker_main_kb())
        return
    
    try:
        amount = float(message.text.strip())
        
        if amount <= 0:
            await message.answer("⚠️ <b>Iltimos, 0 dan katta raqam kiriting</b>")
            return
        
        # Maksimal avans chegarasini tekshirish
        stats = await db.get_worker_stats(message.from_user.id)
        if not stats:
            await state.clear()
            await message.answer("❌ <b>Profil ma'lumotlari topilmadi</b>", reply_markup=worker_main_kb())
            return
        
        max_advance = (stats['hours'] * stats['rate']) * 0.7
        
        if max_advance > 0 and amount > max_advance:
            await message.answer(
                f"⚠️ <b>Avans miqdori chegaradan oshib ketdi!</b>\n\n"
                f"💰 So'ralgan: {amount:,.0f} so'm\n"
                f"📊 Maksimal: {max_advance:,.0f} so'm\n\n"
                f"ℹ️ Iltimos, {max_advance:,.0f} so'm dan kamroq summa kiriting."
            )
            return
        
        # Admin(lar)ga so'rov yuborish (MULTI-ADMIN)
        if ADMIN_LIST:
            from utils.keyboards import approval_kb
            now = get_tashkent_time()
            request_text = (
                f"🔔 {format_bold('YANGI AVANS SOROVI')}\n"
                f"────────────────\n\n"
                f"👤 <b>Ishchi:</b> {stats['name']}\n"
                f"💰 <b>Summa:</b> {amount:,.0f} so'm\n"
                f"📅 <b>Vaqt:</b> {now.strftime('%d.%m.%Y %H:%M')}"
            )
            
            # Har bir adminga xabar yuborish
            for admin_id in ADMIN_LIST:
                try:
                    await message.bot.send_message(
                        admin_id,
                        request_text,
                        reply_markup=approval_kb(message.from_user.id, amount)
                    )
                except Exception as e:
                    logging.warning(f"Admin {admin_id} ga xabar yuborib bo'lmadi: {e}")
        
        # Ishchiga tasdiqlash xabari
        now = get_tashkent_time()
        success_text = (
            f"✅ {format_bold('SOROV YUBORILDI')}\n"
            f"────────────────\n\n"
            f"💰 <b>Summa:</b> {amount:,.0f} so'm\n"
            f"📅 <b>Vaqt:</b> {now.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"⏳ <i>Admin javobini kuting...</i>\n"
            f"📩 Tasdiqlash/rad etish haqida xabar beramiz."
        )
        
        await message.answer(success_text, reply_markup=worker_main_kb())
        await state.clear()
        
    except ValueError:
        await message.answer("⚠️ <b>Iltimos, faqat raqam kiriting!</b>")


