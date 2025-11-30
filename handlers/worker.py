from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.keyboards import worker_main_kb, cancel_kb, confirmation_kb
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
        
        # Tasdiqlash uchun saqlash
        advance_requests[message.from_user.id] = amount
        await state.set_state(WorkerAdvance.confirmation)
        
        confirmation_text = (
            f"🔔 {format_bold('AVANS SO\'ROVI')}\n"
            f"────────────────\n\n"
            f"👤 <b>Ishchi:</b> {stats['name']}\n"
            f"💰 <b>Summa:</b> {amount:,.0f} so'm\n\n"
            f"📝 <b>So'rovni admin ga yuboraymi?</b>"
        )
        
        await message.answer(
            confirmation_text,
            reply_markup=confirmation_kb("advance_request", str(amount))
        )
        
    except ValueError:
        await message.answer("⚠️ <b>Iltimos, faqat raqam kiriting!</b>")

@router.callback_query(F.data.startswith("confirm_advance_request_"))
async def confirm_advance_request(call: CallbackQuery, state: FSMContext):
    """Avans so'rovini tasdiqlash va admin ga yuborish"""
    try:
        user_id = call.from_user.id
        amount = advance_requests.get(user_id)
        
        if not amount:
            await call.message.edit_text("❌ <b>So'rov ma'lumotlari topilmadi</b>")
            await state.clear()
            return
        
        # Ishchi ma'lumotlarini olish
        worker = await db.get_worker_by_id(user_id)
        if not worker:
            await call.message.edit_text("❌ <b>Profil ma'lumotlari topilmadi</b>")
            await state.clear()
            return
        
        # Admin ga xabar yuborish
        admin_id = int(os.getenv("ADMIN_ID", 0))
        if admin_id:
            request_text = (
                f"🔔 {format_bold('YANGI AVANS SO\'ROVI')}\n"
                f"────────────────\n\n"
                f"👤 <b>Ishchi:</b> {worker['name']}\n"
                f"🆔 <b>ID:</b> {worker['id']}\n"
                f"📍 <b>Joyi:</b> {worker.get('location', 'Umumiy')}\n"
                f"💰 <b>Summa:</b> {amount:,.0f} so'm\n"
                f"📅 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            from utils.keyboards import approval_kb
            await call.bot.send_message(
                admin_id,
                request_text,
                reply_markup=approval_kb(worker['id'], amount)
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
        
        await call.message.edit_text(success_text)
        
        # Ma'lumotlarni tozalash
        if user_id in advance_requests:
            del advance_requests[user_id]
        await state.clear()
        
    except Exception as e:
        logging.error(f"Avans so'rovini yuborishda xato: {e}")
        await call.message.edit_text("❌ <b>So'rovni yuborishda xatolik</b>")
        await state.clear()

@router.callback_query(F.data.startswith("cancel_advance"))
async def cancel_advance_request(call: CallbackQuery, state: FSMContext):
    """Avans so'rovini bekor qilish"""
    user_id = call.from_user.id
    if user_id in advance_requests:
        del advance_requests[user_id]
    
    await call.message.edit_text("❌ <b>Avans so'rovi bekor qilindi</b>")
    await state.clear()
    await call.message.answer("🏠 <b>Asosiy menyu</b>", reply_markup=worker_main_kb())

# --- YORDAM ---
@router.message(F.text == "ℹ️ Yordam")
async def show_help(message: Message):
    """Ishchi uchun yordam"""
    help_text = (
        f"🆘 {format_bold('YORDAM')}\n"
        f"────────────────\n\n"
        f"<b>Mavjud funksiyalar:</b>\n\n"
        f"💰 <b>Mening hisobim</b>\n"
        f"• Joriy oy statistikasi\n"
        f"• Ishlagan soatlaringiz\n"
        f"• Avanslar va qoldiq\n\n"
        f"💸 <b>Avans so'rash</b>\n"
        f"• Admin ga avans so'rovi yuborish\n"
        f"• Maksimal 70% gacha ruxsat etiladi\n\n"
        f"📞 <b>Aloqa</b>\n"
        f"Muammo bo'lsa admin bilan bog'laning."
    )
    
    await message.answer(help_text, reply_markup=worker_main_kb())