from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.keyboards import worker_main_kb, cancel_kb
from utils.states import WorkerAdvance
from database import requests as db
import os
import logging
from datetime import datetime
from typing import Dict

router = Router()

# Avans so'rovlari
advance_requests: Dict[int, float] = {}

def format_bold(text: str) -> str:
    """Matnni qalin qilish"""
    bold_map = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳"
    )
    return text.translate(bold_map)

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
    
    stats_text = (
        f"🧾 {format_bold('SHAXSIY HISOB')}\n"
        f"🗓 {datetime.now().strftime('%B %Y')}\n"
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
        f"💸 {format_bold('AVANS SO\'RASH')}\n"
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
        
        # Admin ga so'rov yuborish
        admin_id = int(os.getenv("ADMIN_ID", 0))
        if admin_id:
            from utils.keyboards import approval_kb
            request_text = (
                f"🔔 {format_bold('YANGI AVANS SO\'ROVI')}\n"
                f"────────────────\n\n"
                f"👤 <b>Ishchi:</b> {stats['name']}\n"
                f"💰 <b>Summa:</b> {amount:,.0f} so'm\n"
                f"📅 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            await message.bot.send_message(
                admin_id,
                request_text,
                reply_markup=approval_kb(message.from_user.id, amount)
            )
        
        # Ishchiga tasdiqlash xabari
        success_text = (
            f"✅ {format_bold('SO\'ROV YUBORILDI')}\n"
            f"────────────────\n\n"
            f"💰 <b>Summa:</b> {amount:,.0f} so'm\n"
            f"📅 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"⏳ <i>Admin javobini kuting...</i>\n"
            f"📩 Tasdiqlash/rad etish haqida xabar beramiz."
        )
        
        await message.answer(success_text, reply_markup=worker_main_kb())
        await state.clear()
        
    except ValueError:
        await message.answer("⚠️ <b>Iltimos, faqat raqam kiriting!</b>")