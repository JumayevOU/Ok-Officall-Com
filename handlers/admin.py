from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from utils.states import AddWorker, EditWorker, DeleteWorker, DailyReport, AdminAdvance
from utils.keyboards import (
    admin_main_kb, cancel_kb, settings_kb, edit_options_kb, 
    approval_kb, confirmation_kb, remove_kb
)
from database import requests as db
from utils.excel_gen import generate_report
import os
import random
import logging
from datetime import datetime
from typing import Dict, Any

router = Router()

# Admin ID
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
except (ValueError, TypeError):
    ADMIN_ID = 0
    logging.warning("ADMIN_ID to'g'ri o'rnatilmagan")

# FSM ma'lumotlari
fsm_data: Dict[int, Dict[str, Any]] = {}

def format_bold(text: str) -> str:
    """Matnni qalin qilish"""
    bold_map = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳"
    )
    return text.translate(bold_map)

def generate_unique_code() -> int:
    """Takrorlanmas kod generatsiya qilish"""
    return random.randint(1000, 9999)

# --- SOZLAMALAR MENYUSI ---
@router.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(message: Message):
    """Sozlamalar menyusi"""
    if message.from_user.id != ADMIN_ID:
        return
    
    menu_text = (
        f"⚙️ {format_bold('BOSHQARUV MARKAZI')}\n"
        f"────────────────\n\n"
        f"🛠️ <b>Tizim sozlamalari</b>\n"
        f"Quyidagi amallardan birini tanlang:"
    )
    await message.answer(menu_text, reply_markup=settings_kb())

# --- YANGI ISHCHI QO'SHISH ---
@router.callback_query(F.data == "add_worker")
async def start_add_worker(call: CallbackQuery, state: FSMContext):
    """Yangi ishchi qo'shishni boshlash"""
    await call.message.delete()
    await state.set_state(AddWorker.name)
    
    prompt_text = (
        f"👤 {format_bold('YANGI ISHCHI QO\'SHISH')}\n"
        f"────────────────\n\n"
        f"✍️ <b>Yangi ishchining to'liq ism-familiyasini kiriting:</b>\n\n"
        f"<i>Masalan: Aliyev Valijon</i>"
    )
    await call.message.answer(prompt_text, reply_markup=cancel_kb)

@router.message(AddWorker.name)
async def process_worker_name(message: Message, state: FSMContext):
    """Ishchi ismini qabul qilish"""
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("⚠️ <b>Iltimos, to'liq ism kiriting (kamida 2 belgi)</b>")
        return
    
    await state.update_data(name=name)
    await state.set_state(AddWorker.rate)
    
    prompt_text = (
        f"💸 {format_bold('SOATLIK ISH HAQQI')}\n"
        f"────────────────\n\n"
        f"💰 <b>Ishchining soatlik ish haqqini kiriting:</b>\n\n"
        f"<i>Faqat raqam kiriting (so'mda). Masalan: 25000</i>"
    )
    await message.answer(prompt_text, reply_markup=cancel_kb)

@router.message(AddWorker.rate)
async def process_worker_rate(message: Message, state: FSMContext):
    """Ishchi stavkasini qabul qilish"""
    try:
        rate = float(message.text.strip())
        if rate <= 0:
            await message.answer("⚠️ <b>Iltimos, 0 dan katta raqam kiriting</b>")
            return
            
        await state.update_data(rate=rate)
        await state.set_state(AddWorker.location)
        
        prompt_text = (
            f"📍 {format_bold('ISH JOYI')}\n"
            f"────────────────\n\n"
            f"🏢 <b>Ishchi qaysi bo'limda ishlaydi?</b>\n\n"
            f"<i>Masalan: A Blok, H Blok, Ofis...</i>"
        )
        await message.answer(prompt_text, reply_markup=cancel_kb)
        
    except ValueError:
        await message.answer("⚠️ <b>Iltimos, faqat raqam kiriting!</b>")

@router.message(AddWorker.location)
async def process_worker_location(message: Message, state: FSMContext):
    """Ishchi lokatsiyasini qabul qilish"""
    location = message.text.strip() or "Umumiy"
    data = await state.get_data()
    
    # Takrorlanmas kod generatsiya qilish
    code = generate_unique_code()
    
    # Ishchini bazaga qo'shish
    success = await db.add_worker(data['name'], data['rate'], code, location)
    
    if success:
        success_text = (
            f"✅ {format_bold('MUVAFFAQIYATLI QO\'SHILDI')}\n"
            f"────────────────\n\n"
            f"👤 <b>Ishchi:</b> {data['name']}\n"
            f"📍 <b>Joyi:</b> {location}\n"
            f"💵 <b>Soatlik:</b> {data['rate']:,.0f} so'm\n"
            f"🔑 <b>Kirish kodi:</b> <code>{code}</code>\n\n"
            f"📝 <i>Bu kodni ishchiga bering, u botga kirishi uchun kerak.</i>"
        )
        await message.answer(success_text, reply_markup=admin_main_kb())
    else:
        error_text = (
            f"❌ {format_bold('XATOLIK')}\n"
            f"────────────────\n\n"
            f"<b>Ishchi qo'shishda xatolik yuz berdi.</b>\n"
            f"Iltimos, qayta urinib ko'ring."
        )
        await message.answer(error_text, reply_markup=admin_main_kb())
    
    await state.clear()

# --- ISHCHILAR RO'YXATI ---
@router.message(F.text == "👥 Ishchilar")
async def show_workers_list(message: Message):
    """Ishchilar ro'yxatini ko'rsatish"""
    if message.from_user.id != ADMIN_ID:
        return
    
    workers = await db.get_active_workers()
    
    list_text = (
        f"📋 {format_bold('ISHCHILAR RO\'YXATI')}\n"
        f"────────────────\n\n"
    )
    
    if not workers:
        list_text += "<i>🤷 Hozircha ishchilar ro'yxati bo'sh</i>"
    else:
        current_location = None
        for worker in workers:
            location = worker.get('location', 'Umumiy')
            
            if location != current_location:
                list_text += f"\n🏢 <b>{location}</b>\n"
                current_location = location
            
            list_text += (
                f"🆔 <code>{worker['id']}</code> | 👤 {worker['name']}\n"
                f"   💰 {worker['rate']:,.0f} so'm/soat\n\n"
            )
    
    list_text += "\n👇 <i>O'zgartirish kiritish uchun 'Sozlamalar' menyusidan foydalaning</i>"
    await message.answer(list_text, reply_markup=admin_main_kb())

# --- DAVOMAT KIRITISH ---
@router.message(F.text == "📝 Bugungi hisobot")
async def start_daily_report(message: Message, state: FSMContext):
    """Kunlik hisobotni boshlash"""
    if message.from_user.id != ADMIN_ID:
        return
    
    workers = await db.get_active_workers()
    if not workers:
        await message.answer("⚠️ <b>Hozircha ishchilar ro'yxati bo'sh</b>")
        return
    
    # FSM ma'lumotlarini saqlash
    fsm_data[message.from_user.id] = {
        'queue': workers,
        'index': 0,
        'total': len(workers)
    }
    
    await state.set_state(DailyReport.enter_hours)
    await show_next_worker(message, state)

async def show_next_worker(message: Message, state: FSMContext):
    """Keyingi ishchini ko'rsatish"""
    user_data = fsm_data.get(message.from_user.id)
    if not user_data:
        await state.clear()
        return
    
    current_index = user_data['index']
    workers = user_data['queue']
    
    if current_index >= len(workers):
        # Yakunlash
        success_text = (
            f"✅ {format_bold('HISOBOT YAKUNLANDI')}\n"
            f"────────────────\n\n"
            f"🎉 <b>Barcha ishchilar uchun hisobot muvaffaqiyatli saqlandi!</b>\n"
            f"📊 Jami: {len(workers)} ta ishchi"
        )
        await message.answer(success_text, reply_markup=admin_main_kb())
        await state.clear()
        return
    
    worker = workers[current_index]
    prompt_text = (
        f"⏱ {format_bold('DAVOMAT KIRITISH')}\n"
        f"────────────────\n\n"
        f"👤 <b>Ishchi:</b> {worker['name']}\n"
        f"📍 <b>Joyi:</b> {worker.get('location', 'Umumiy')}\n"
        f"📊 <b>Progress:</b> {current_index + 1}/{len(workers)}\n\n"
        f"👉 <b>Bugun necha soat ishladi?</b>\n\n"
        f"<i>Raqam kiriting (masalan: 8). Agar kelmagan bo'lsa 0 ni kiriting.</i>"
    )
    await message.answer(prompt_text, reply_markup=cancel_kb)

@router.message(DailyReport.enter_hours)
async def process_worker_hours(message: Message, state: FSMContext):
    """Ishchi soatlarini qabul qilish"""
    try:
        hours = float(message.text.strip())
        if hours < 0:
            await message.answer("⚠️ <b>Iltimos, manfiy bo'lmagan raqam kiriting</b>")
            return
        
        user_data = fsm_data.get(message.from_user.id)
        if not user_data:
            await state.clear()
            return
        
        current_index = user_data['index']
        worker = user_data['queue'][current_index]
        
        # Davomatni saqlash
        status = "Keldi" if hours > 0 else "Kelmadi"
        success = await db.add_attendance(worker['id'], hours, status)
        
        if not success:
            await message.answer("⚠️ <b>Davomatni saqlashda xatolik</b>")
            return
        
        # Keyingi ishchiga o'tish
        user_data['index'] += 1
        await show_next_worker(message, state)
        
    except ValueError:
        await message.answer("⚠️ <b>Iltimos, faqat raqam kiriting!</b>")

# --- JORIY HOLAT ---
@router.message(F.text == "📊 Joriy holat")
async def show_current_status(message: Message):
    """Joriy oy holatini ko'rsatish"""
    if message.from_user.id != ADMIN_ID:
        return
    
    now = datetime.now()
    workers = await db.get_active_workers()
    attendance, advances = await db.get_month_data(now.year, now.month)
    
    # Ma'lumotlarni tayyorlash
    attendance_dict = {(r['worker_id'], r['date_str']): r['hours'] for r in attendance}
    advances_dict = {r['worker_id']: r['total'] for r in advances}
    
    status_text = (
        f"📊 {format_bold('JORIY HOLAT')}\n"
        f"🗓 {now.strftime('%B %Y')}\n"
        f"────────────────\n\n"
    )
    
    if not workers:
        status_text += "<i>🤷 Hozircha ma'lumot yo'q</i>"
    else:
        total_salary = 0
        current_location = None
        
        for worker in workers:
            location = worker.get('location', 'Umumiy')
            if location != current_location:
                status_text += f"\n🏢 <b>{location}</b>\n"
                current_location = location
            
            # Soatlarni hisoblash
            total_hours = 0
            for day in range(1, 32):
                date_key = f"{now.year}-{now.month:02d}-{day:02d}"
                hours = attendance_dict.get((worker['id'], date_key), 0)
                total_hours += hours
            
            # Avans
            advance = advances_dict.get(worker['id'], 0)
            salary = total_hours * worker['rate']
            net_salary = salary - advance
            
            total_salary += net_salary
            
            status_text += (
                f"👤 {worker['name']}\n"
                f"⏱ {total_hours} soat | "
                f"💸 {advance:,.0f} so'm avans\n"
                f"💰 <b>{net_salary:,.0f} so'm</b>\n\n"
            )
        
        status_text += f"💵 <b>JAMI KASSA: {total_salary:,.0f} so'm</b>"
    
    await message.answer(status_text, reply_markup=admin_main_kb())

# --- EXCEL HISOBOT ---
@router.message(F.text == "📥 Excel hisobot")
async def generate_excel_report(message: Message):
    """Excel hisobot yaratish"""
    if message.from_user.id != ADMIN_ID:
        return
    
    processing_msg = await message.answer("🔄 <i>Hisobot tayyorlanmoqda...</i>")
    
    try:
        now = datetime.now()
        workers = await db.get_active_workers()
        attendance, advances = await db.get_month_data(now.year, now.month)
        
        if not workers:
            await processing_msg.delete()
            await message.answer("⚠️ <b>Hisobot uchun ma'lumot topilmadi</b>")
            return
        
        # Ma'lumotlarni tayyorlash
        attendance_dict = {(r['worker_id'], r['date_str']): r['hours'] for r in attendance}
        advances_dict = {r['worker_id']: r['total'] for r in advances}
        
        # Excel yaratish
        filename = generate_report(now.year, now.month, workers, attendance_dict, advances_dict)
        
        await processing_msg.delete()
        
        # Faylni yuborish
        caption = (
            f"📊 {format_bold(f'{now.strftime(\"%B %Y\")} OYI HISOBOTI')}\n"
            f"────────────────\n\n"
            f"📁 Fayl: <code>{filename}</code>\n"
            f"👥 Ishchilar: {len(workers)} ta\n"
            f"📅 Sana: {now.strftime('%d.%m.%Y %H:%M')}"
        )
        
        await message.answer_document(
            FSInputFile(filename),
            caption=caption
        )
        
        # Vaqtinchalik faylni o'chirish
        import os
        os.remove(filename)
        
    except Exception as e:
        await processing_msg.delete()
        error_text = (
            f"❌ {format_bold('XATOLIK')}\n"
            f"────────────────\n\n"
            f"<b>Hisobot yaratishda xatolik:</b>\n"
            f"<code>{str(e)}</code>"
        )
        await message.answer(error_text)
        logging.error(f"Excel hisobot xatosi: {e}")

# --- AVANS YOZISH ---
@router.message(F.text == "💰 Avans yozish")
async def start_admin_advance(message: Message, state: FSMContext):
    """Admin tomonidan avans yozish"""
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.set_state(AdminAdvance.select_worker)
    
    prompt_text = (
        f"💰 {format_bold('AVANS YOZISH')}\n"
        f"────────────────\n\n"
        f"🔎 <b>Ishchini topish uchun:</b>\n"
        f"• ID raqamini yozing\n"
        f"• Ismini yozing\n\n"
        f"<i>Masalan: 123 yoki Ali</i>"
    )
    await message.answer(prompt_text, reply_markup=cancel_kb)

@router.message(AdminAdvance.select_worker)
async def process_worker_selection(message: Message, state: FSMContext):
    """Ishchi tanlash"""
    search_text = message.text.strip()
    
    if search_text.isdigit():
        # ID orqali qidirish
        worker = await db.get_worker_by_id(int(search_text))
        if worker and worker['active']:
            await state.update_data(worker_id=worker['id'], worker_name=worker['name'])
            await state.set_state(AdminAdvance.enter_amount)
            
            prompt_text = (
                f"👤 <b>Ishchi:</b> {worker['name']}\n"
                f"📍 <b>Joyi:</b> {worker.get('location', 'Umumiy')}\n\n"
                f"💸 <b>Qancha avans bermoqchisiz?</b>\n\n"
                f"<i>Faqat raqam kiriting (so'mda). Masalan: 500000</i>"
            )
            await message.answer(prompt_text, reply_markup=cancel_kb)
            return
        else:
            await message.answer("❌ <b>Ishchi topilmadi yoki aktiv emas</b>")
            return
    
    # Ism orqali qidirish
    workers = await db.search_worker_by_name(search_text)
    
    if not workers:
        await message.answer("❌ <b>Hech qanday ishchi topilmadi</b>")
        return
    
    if len(workers) == 1:
        worker = workers[0]
        await state.update_data(worker_id=worker['id'], worker_name=worker['name'])
        await state.set_state(AdminAdvance.enter_amount)
        
        prompt_text = (
            f"✅ <b>Topildi:</b> {worker['name']}\n"
            f"📍 <b>Joyi:</b> {worker.get('location', 'Umumiy')}\n\n"
            f"💸 <b>Qancha avans bermoqchisiz?</b>"
        )
        await message.answer(prompt_text, reply_markup=cancel_kb)
    else:
        # Bir nechta ishchi topilgan
        workers_text = "⚠️ <b>Bir nechta ishchi topildi. ID raqamini tanlang:</b>\n\n"
        for worker in workers:
            workers_text += f"🆔 <code>{worker['id']}</code> - {worker['name']} ({worker.get('location', 'Umumiy')})\n"
        
        workers_text += "\n<b>ID raqamini kiriting:</b>"
        await message.answer(workers_text, reply_markup=cancel_kb)

@router.message(AdminAdvance.enter_amount)
async def process_advance_amount(message: Message, state: FSMContext):
    """Avans miqdorini qabul qilish"""
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            await message.answer("⚠️ <b>Iltimos, 0 dan katta raqam kiriting</b>")
            return
        
        data = await state.get_data()
        success = await db.add_advance(data['worker_id'], amount)
        
        if success:
            success_text = (
                f"✅ {format_bold('AVANS YOZILDI')}\n"
                f"────────────────\n\n"
                f"👤 <b>Ishchi:</b> {data['worker_name']}\n"
                f"💰 <b>Miqdor:</b> {amount:,.0f} so'm\n"
                f"📅 <b>Sana:</b> {datetime.now().strftime('%d.%m.%Y')}"
            )
            
            # Ishchiga xabar yuborish (agar telegram_id bo'lsa)
            worker = await db.get_worker_by_id(data['worker_id'])
            if worker and worker['telegram_id']:
                try:
                    worker_notification = (
                        f"💰 {format_bold('AVANS YOZILDI')}\n"
                        f"────────────────\n\n"
                        f"Sizga <b>{amount:,.0f} so'm</b> avans yozildi.\n"
                        f"📅 {datetime.now().strftime('%d.%m.%Y')}"
                    )
                    await message.bot.send_message(worker['telegram_id'], worker_notification)
                except Exception as e:
                    logging.error(f"Ishchiga xabar yuborishda xato: {e}")
            
            await message.answer(success_text, reply_markup=admin_main_kb())
        else:
            await message.answer("❌ <b>Avans yozishda xatolik</b>")
        
        await state.clear()
        
    except ValueError:
        await message.answer("⚠️ <b>Iltimos, faqat raqam kiriting!</b>")

# --- CALLBACK QUERY HANDLERS ---
@router.callback_query(F.data.startswith("approve_adv_"))
async def approve_advance_request(call: CallbackQuery):
    """Avans so'rovini tasdiqlash"""
    try:
        parts = call.data.split("_")
        worker_id = int(parts[2])
        amount = float(parts[3])
        
        success = await db.add_advance(worker_id, amount, True)
        
        if success:
            await call.message.edit_text(
                f"✅ {format_bold('AVANS TASDIQLANDI')}\n\n"
                f"👤 Ishchi ID: {worker_id}\n"
                f"💰 Summa: {amount:,.0f} so'm"
            )
            
            # Ishchiga xabar yuborish
            worker = await db.get_worker_by_id(worker_id)
            if worker and worker['telegram_id']:
                try:
                    notification = (
                        f"✅ {format_bold('AVANS TASDIQLANDI')}\n"
                        f"────────────────\n\n"
                        f"Sizning <b>{amount:,.0f} so'm</b> lik avans so'rovingiz tasdiqlandi!\n"
                        f"💳 Muvaffaqiyatli hisobingizga yozildi."
                    )
                    await call.bot.send_message(worker['telegram_id'], notification)
                except Exception as e:
                    logging.error(f"Ishchiga xabar yuborishda xato: {e}")
        else:
            await call.message.edit_text("❌ <b>Avans tasdiqlashda xatolik</b>")
            
    except Exception as e:
        logging.error(f"Avans tasdiqlash xatosi: {e}")
        await call.message.edit_text("❌ <b>Xatolik yuz berdi</b>")

@router.callback_query(F.data.startswith("reject_adv_"))
async def reject_advance_request(call: CallbackQuery):
    """Avans so'rovini rad etish"""
    try:
        worker_id = int(call.data.split("_")[2])
        await call.message.edit_text("❌ <b>Avans so'rovi rad etildi</b>")
        
        # Ishchiga xabar yuborish
        worker = await db.get_worker_by_id(worker_id)
        if worker and worker['telegram_id']:
            try:
                notification = (
                    f"❌ {format_bold('AVANS RAD ETILDI')}\n"
                    f"────────────────\n\n"
                    f"Sizning avans so'rovingiz rad etildi.\n"
                    f"ℹ️ Tafsilotlar uchun admin bilan bog'laning."
                )
                await call.bot.send_message(worker['telegram_id'], notification)
            except Exception as e:
                logging.error(f"Ishchiga xabar yuborishda xato: {e}")
                
    except Exception as e:
        logging.error(f"Avans rad etish xatosi: {e}")