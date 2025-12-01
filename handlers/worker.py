from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from utils.keyboards import worker_main_kb, cancel_kb
from utils.states import WorkerAdvance
from database import requests as db
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List

router = Router()

# --- ADMINLARNI OLISH ---
ADMIN_LIST: List[int] = []
try:
    env_admins = os.getenv("ADMIN_ID", "")
    # Vergul bilan ajratilgan ID larni olamiz
    ADMIN_LIST = [int(id_str.strip()) for id_str in env_admins.split(",") if id_str.strip()]
except (ValueError, TypeError):
    logging.warning("ADMIN_ID worker.py da topilmadi")

def format_bold(text: str) -> str:
    return f"<b>{text}</b>"

def get_tashkent_time():
    return datetime.utcnow() + timedelta(hours=5)

# --- SHAXSIY HISOB ---
@router.message(F.text == "💰 Mening hisobim")
async def show_worker_stats(message: Message):
    stats = await db.get_worker_stats(message.from_user.id)
    
    if not stats:
        await message.answer("❌ Profilingiz topilmadi yoki aktiv emas.")
        return
    
    salary = stats['hours'] * stats['rate']
    net_salary = salary - stats['advance']
    
    now = get_tashkent_time()
    
    # Xatosiz oddiy matn
    text = (
        f"🧾 {format_bold('SHAXSIY HISOB')}\n"
        f"🗓 {now.strftime('%m.%Y')}\n"
        f"────────────────\n\n"
        f"👤 <b>{stats['name']}</b>\n"
        f"💎 Stavka: {stats['rate']:,.0f} so'm\n\n"
        f"⏱ Ishlangan: <b>{stats['hours']} soat</b>\n"
        f"💵 Hisoblangan: <b>{salary:,.0f} so'm</b>\n"
        f"💸 Avanslar: <b>{stats['advance']:,.0f} so'm</b>\n"
        f"────────────────\n"
        f"💰 <b>QOLGA TEGADI: {net_salary:,.0f} so'm</b>"
    )
    
    await message.answer(text, reply_markup=worker_main_kb())

# --- AVANS SO'RASH ---
@router.message(F.text == "💸 Avans so'rash")
async def start_advance_request(message: Message, state: FSMContext):
    stats = await db.get_worker_stats(message.from_user.id)
    if not stats:
        await message.answer("❌ Profil topilmadi")
        return
    
    max_advance = (stats['hours'] * stats['rate']) * 0.7
    
    # XATOLIK TUZATILDI: Oddiy matn ishlatildi
    text = (
        f"💸 {format_bold('AVANS SORASH')}\n"
        f"────────────────\n\n"
        f"💰 <b>Summani kiriting (so'mda):</b>\n"
        f"Maksimal: {max_advance:,.0f} so'm"
    )
    
    await state.set_state(WorkerAdvance.enter_amount)
    await message.answer(text, reply_markup=cancel_kb)

@router.message(WorkerAdvance.enter_amount)
async def process_advance_request(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Bekor qilindi", reply_markup=worker_main_kb())
        return
    
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            await message.answer("⚠️ 0 dan katta son kiriting!")
            return

        # Limitni tekshirish
        stats = await db.get_worker_stats(message.from_user.id)
        max_advance = (stats['hours'] * stats['rate']) * 0.7
        
        if max_advance > 0 and amount > max_advance:
            await message.answer(f"⚠️ Limitdan oshdi! Maksimal: {max_advance:,.0f} so'm")
            return
            
        # Adminlarga xabar
        from utils.keyboards import approval_kb
        now = get_tashkent_time()
        
        msg_text = (
            f"🔔 <b>YANGI AVANS SOROVI</b>\n"
            f"👤 Ishchi: {stats['name']}\n"
            f"💰 Summa: {amount:,.0f} so'm\n"
            f"📅 Vaqt: {now.strftime('%d.%m.%Y %H:%M')}"
        )
        
        for admin_id in ADMIN_LIST:
            try:
                await message.bot.send_message(
                    admin_id, 
                    msg_text, 
                    reply_markup=approval_kb(message.from_user.id, amount)
                )
            except:
                pass
        
        await message.answer("✅ So'rov adminga yuborildi!", reply_markup=worker_main_kb())
        await state.clear()
        
    except ValueError:
        await message.answer("⚠️ Faqat raqam kiriting!")


