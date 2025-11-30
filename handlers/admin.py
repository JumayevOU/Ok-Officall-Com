from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from utils.states import AddWorker, EditWorker, DeleteWorker, DailyReport, AdminAdvance
from utils.keyboards import admin_main_kb, cancel_kb, settings_kb, edit_options_kb, approval_kb, remove_kb
from database import requests as db
from utils.excel_gen import generate_report
import os
import random
import logging
from datetime import datetime
from typing import Dict, Any
import asyncpg

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
    await message.answer(menu_text, reply_markup=settings_kb)

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
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Amal bekor qilindi", reply_markup=admin_main_kb())
        return
    
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
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Amal bekor qilindi", reply_markup=admin_main_kb())
        return
    
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
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Amal bekor qilindi", reply_markup=admin_main_kb())
        return
    
    location = message.text.strip() or "Umumiy"
    data = await state.get_data()
    
    try:
        # Takrorlanmas kod generatsiya qilish
        code = generate_unique_code()
        
        # Database ga yozish
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        await conn.execute(
            "INSERT INTO workers (name, rate, code, location, active) VALUES ($1, $2, $3, $4, $5)", 
            data['name'], data['rate'], code, location, True
        )
        await conn.close()
        
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
        
    except Exception as e:
        logging.error(f"Ishchi qo'shish xatosi: {e}")
        
        error_text = (
            f"❌ {format_bold('XATOLIK')}\n"
            f"────────────────\n\n"
            f"<b>Ishchi qo'shishda xatolik yuz berdi.</b>\n\n"
            f"📋 <i>Xato tafsilotlari:</i>\n"
            f"<code>{str(e)}</code>\n\n"
            f"🔄 <b>Iltimos, qayta urinib ko'ring.</b>"
        )
        await message.answer(error_text, reply_markup=admin_main_kb())
    
    await state.clear()

# --- ISHCHI TAHRIRLASH ---
@router.callback_query(F.data == "edit_worker")
async def start_edit_worker(call: CallbackQuery, state: FSMContext):
    """Ishchi tahrirlashni boshlash"""
    await call.message.delete()
    await state.set_state(EditWorker.waiting_id)
    
    prompt_text = (
        f"✏️ {format_bold('ISHCHI MA\'LUMOTLARINI TAHRIRLASH')}\n"
        f"────────────────\n\n"
        f"🆔 <b>Tahrirlash uchun ishchining ID raqamini kiriting:</b>\n\n"
        f"<i>ID raqamni 'Ishchilar' bo'limidan ko'rishingiz mumkin.</i>"
    )
    await call.message.answer(prompt_text, reply_markup=cancel_kb)

@router.message(EditWorker.waiting_id)
async def process_edit_worker_id(message: Message, state: FSMContext):
    """Tahrirlash uchun ishchi ID sini qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Amal bekor qilindi", reply_markup=admin_main_kb())
        return
    
    if not message.text.isdigit():
        await message.answer("⚠️ <b>Iltimos, faqat raqam kiriting!</b>")
        return
    
    worker_id = int(message.text)
    worker = await db.get_worker_by_id(worker_id)
    
    if not worker:
        await message.answer("❌ <b>Ishchi topilmadi!</b>\n\nIltimos, to'g'ri ID kiriting:")
        return
    
    if not worker['active']:
        await message.answer("❌ <b>Bu ishchi aktiv emas (arxivlangan)!</b>\n\nBoshqa ID kiriting:")
        return
    
    await state.update_data(worker_id=worker_id, worker_name=worker['name'])
    await state.set_state(EditWorker.waiting_field)
    
    prompt_text = (
        f"✏️ <b>Tahrirlash:</b> {worker['name']}\n"
        f"🆔 <b>ID:</b> {worker_id}\n\n"
        f"📝 <b>Qaysi ma'lumotni o'zgartirmoqchisiz?</b>"
    )
    await message.answer(prompt_text, reply_markup=edit_options_kb)

@router.callback_query(EditWorker.waiting_field, F.data.startswith("edit_"))
async def process_edit_field(call: CallbackQuery, state: FSMContext):
    """Tahrirlash maydonini qabul qilish"""
    field_map = {
        "edit_name": "name",
        "edit_rate": "rate", 
        "edit_location": "location"
    }
    
    field = field_map.get(call.data)
    if not field:
        await call.answer("❌ Xato!")
        return
    
    await state.update_data(edit_field=field)
    await state.set_state(EditWorker.waiting_value)
    
    prompts = {
        "name": "✍️ <b>Yangi ismni kiriting:</b>",
        "rate": "💵 <b>Yangi soatlik narxni kiriting (faqat raqam):</b>",
        "location": "📍 <b>Yangi ish joyini kiriting:</b>"
    }
    
    await call.message.edit_text(prompts[field])

@router.message(EditWorker.waiting_value)
async def process_edit_value(message: Message, state: FSMContext):
    """Tahrirlash qiymatini qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Amal bekor qilindi", reply_markup=admin_main_kb())
        return
    
    data = await state.get_data()
    field = data['edit_field']
    worker_id = data['worker_id']
    value = message.text.strip()
    
    try:
        if field == 'rate':
            value = float(value)
            if value <= 0:
                await message.answer("⚠️ <b>Iltimos, 0 dan katta raqam kiriting!</b>")
                return
        
        success = await db.update_worker_field(worker_id, field, value)
        
        if success:
            success_text = (
                f"✅ {format_bold('MA\'LUMOT MUVAFFAQIYATLI YANGILANDI')}\n"
                f"────────────────\n\n"
                f"👤 <b>Ishchi:</b> {data['worker_name']}\n"
                f"🆔 <b>ID:</b> {worker_id}\n"
                f"📝 <b>Yangilangan maydon:</b> {field}\n"
                f"💎 <b>Yangi qiymat:</b> {value}"
            )
            await message.answer(success_text, reply_markup=admin_main_kb())
        else:
            await message.answer("❌ <b>Ma'lumotni yangilashda xatolik!</b>", reply_markup=admin_main_kb())
        
        await state.clear()
        
    except ValueError:
        await message.answer("⚠️ <b>Iltimos, faqat raqam kiriting!</b>")

# --- ISHCHI O'CHIRISH ---
@router.callback_query(F.data == "delete_worker")
async def start_delete_worker(call: CallbackQuery, state: FSMContext):
    """Ishchi o'chirishni boshlash"""
    await call.message.delete()
    await state.set_state(DeleteWorker.waiting_id)
    
    prompt_text = (
        f"🗑 {format_bold('ISHCHINI O\'CHIRISH')}\n"
        f"────────────────\n\n"
        f"🆔 <b>O'chirish uchun ishchining ID raqamini kiriting:</b>\n\n"
        f"<i>Eslatma: Ishchi butunlay o'chirilmaydi, faqat arxivlanadi.</i>"
    )
    await call.message.answer(prompt_text, reply_markup=cancel_kb)

@router.message(DeleteWorker.waiting_id)
async def process_delete_worker(message: Message, state: FSMContext):
    """Ishchi o'chirishni tasdiqlash"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Amal bekor qilindi", reply_markup=admin_main_kb())
        return
    
    if not message.text.isdigit():
        await message.answer("⚠️ <b>Iltimos, faqat raqam kiriting!</b>")
        return
    
    worker_id = int(message.text)
    worker = await db.get_worker_by_id(worker_id)
    
    if not worker:
        await message.answer("❌ <b>Ishchi topilmadi!</b>\n\nIltimos, to'g'ri ID kiriting:")
        return
    
    if not worker['active']:
        await message.answer("❌ <b>Bu ishchi allaqachon arxivlangan!</b>", reply_markup=admin_main_kb())
        await state.clear()
        return
    
    # Ishchini arxivlash
    success = await db.archive_worker(worker_id)
    
    if success:
        success_text = (
            f"✅ {format_bold('ISHCHI ARXIVLANDI')}\n"
            f"────────────────\n\n"
            f"👤 <b>Ishchi:</b> {worker['name']}\n"
            f"🆔 <b>ID:</b> {worker_id}\n"
            f"📅 <b>Sana:</b> {datetime.now().strftime('%d.%m.%Y')}\n\n"
            f"<i>Ishchi joriy oy hisobotida qoladi, keyingi oylarda ko'rinmaydi.</i>"
        )
        await message.answer(success_text, reply_markup=admin_main_kb())
    else:
        await message.answer("❌ <b>Ishchini arxivlashda xatolik!</b>", reply_markup=admin_main_kb())
    
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

# --- KUNLIK HISOBOT ---
@router.message(F.text == "📝 Bugungi hisobot")
async def start_daily_report(message: Message, state: FSMContext):
    """Kunlik hisobotni boshlash"""
    if message.from_user.id != ADMIN_ID:
        return
    
    workers = await db.get_active_workers()
    if not workers:
        await message.answer("⚠️ <b>Hozircha ishchilar ro'yxati bo'sh</b>", reply_markup=admin_main_kb())
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
        
        # FSM ma'lumotlarini tozalash
        if message.from_user.id in fsm_data:
            del fsm_data[message.from_user.id]
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
    if message.text == "❌ Bekor qilish":
        await state.clear()
        if message.from_user.id in fsm_data:
            del fsm_data[message.from_user.id]
        await message.answer("⏹️ Jarayon to'xtatildi", reply_markup=admin_main_kb())
        return
    
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
    attendance_dict = {}
    for record in attendance:
        worker_id = record['worker_id']
        date_str = record['date_str']
        hours = record['hours']
        
        if worker_id not in attendance_dict:
            attendance_dict[worker_id] = 0
        attendance_dict[worker_id] += hours
    
    advances_dict = {}
    for record in advances:
        worker_id = record['worker_id']
        total = record['total']
        advances_dict[worker_id] = total
    
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
            total_hours = attendance_dict.get(worker['id'], 0)
            
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
            await message.answer("⚠️ <b>Hisobot uchun ma'lumot topilmadi</b>", reply_markup=admin_main_kb())
            return
        
        # Ma'lumotlarni tayyorlash
        attendance_dict = {}
        for record in attendance:
            key = (record['worker_id'], record['date_str'])
            attendance_dict[key] = record['hours']
        
        advances_dict = {}
        for record in advances:
            advances_dict[record['worker_id']] = record['total']
        
        # Excel yaratish
        filename = generate_report(now.year, now.month, workers, attendance_dict, advances_dict)
        
        await processing_msg.delete()
        
        # Faylni yuborish
        month_year = now.strftime("%B %Y")
        caption = (
            f"📊 {format_bold(month_year + ' OYI HISOBOTI')}\n"
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
        os.remove(filename)
        
    except Exception as e:
        await processing_msg.delete()
        error_text = (
            f"❌ {format_bold('XATOLIK')}\n"
            f"────────────────\n\n"
            f"<b>Hisobot yaratishda xatolik:</b>\n"
            f"<code>{str(e)}</code>"
        )
        await message.answer(error_text, reply_markup=admin_main_kb())
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
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Amal bekor qilindi", reply_markup=admin_main_kb())
        return
    
    search_text = message.text.strip()
    
    if search_text.isdigit():
        # ID orqali qidirish
        worker_id = int(search_text)
        worker = await db.get_worker_by_id(worker_id)
        
        if worker and worker['active']:
            await state.update_data(
                worker_id=worker['id'], 
                worker_name=worker['name'],
                worker_location=worker.get('location', 'Umumiy')
            )
            await state.set_state(AdminAdvance.enter_amount)
            
            prompt_text = (
                f"✅ <b>Ishchi topildi:</b>\n"
                f"👤 {worker['name']}\n"
                f"📍 {worker.get('location', 'Umumiy')}\n\n"
                f"💸 <b>Qancha avans bermoqchisiz?</b>\n\n"
                f"<i>Faqat raqam kiriting (so'mda). Masalan: 500000</i>"
            )
            await message.answer(prompt_text, reply_markup=cancel_kb)
            return
        else:
            await message.answer(
                "❌ <b>Ishchi topilmadi yoki aktiv emas</b>\n\n"
                "🆔 Iltimos, to'g'ri ID raqamini kiriting yoki ism bilan qidiring:",
                reply_markup=cancel_kb
            )
            return
    
    # Ism orqali qidirish
    workers = await db.search_worker_by_name(search_text)
    
    if not workers:
        await message.answer(
            "❌ <b>Hech qanday ishchi topilmadi</b>\n\n"
            "🔍 Iltimos, qaytadan urinib ko'ring:\n"
            "• ID raqamini yozing\n"
            "• Ismni to'g'ri yozing",
            reply_markup=cancel_kb
        )
        return
    
    if len(workers) == 1:
        worker = workers[0]
        await state.update_data(
            worker_id=worker['id'], 
            worker_name=worker['name'],
            worker_location=worker.get('location', 'Umumiy')
        )
        await state.set_state(AdminAdvance.enter_amount)
        
        prompt_text = (
            f"✅ <b>Ishchi topildi:</b>\n"
            f"👤 {worker['name']}\n"
            f"📍 {worker.get('location', 'Umumiy')}\n\n"
            f"💸 <b>Qancha avans bermoqchisiz?</b>"
        )
        await message.answer(prompt_text, reply_markup=cancel_kb)
    else:
        # Bir nechta ishchi topilgan
        workers_text = (
            f"🔍 <b>Bir nechta ishchi topildi:</b>\n\n"
        )
        for worker in workers:
            workers_text += f"🆔 <code>{worker['id']}</code> - {worker['name']} ({worker.get('location', 'Umumiy')})\n"
        
        workers_text += (
            f"\n📝 <b>Iltimos, kerakli ishchining ID raqamini kiriting:</b>"
        )
        await message.answer(workers_text, reply_markup=cancel_kb)

@router.message(AdminAdvance.enter_amount)
async def process_advance_amount(message: Message, state: FSMContext):
    """Avans miqdorini qabul qilish"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Amal bekor qilindi", reply_markup=admin_main_kb())
        return
    
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            await message.answer(
                "⚠️ <b>Noto'g'ri miqdor!</b>\n\n"
                "Iltimos, 0 dan katta raqam kiriting:",
                reply_markup=cancel_kb
            )
            return
        
        data = await state.get_data()
        success = await db.add_advance(data['worker_id'], amount)
        
        if success:
            success_text = (
                f"✅ {format_bold('AVANS MUVAFFAQIYATLI YOZILDI')}\n"
                f"────────────────\n\n"
                f"👤 <b>Ishchi:</b> {data['worker_name']}\n"
                f"📍 <b>Joyi:</b> {data.get('worker_location', 'Umumiy')}\n"
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
                        f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
                        f"ℹ️ <i>Ma'lumotlarni 'Mening hisobim' bo'limida ko'rishingiz mumkin.</i>"
                    )
                    await message.bot.send_message(worker['telegram_id'], worker_notification)
                except Exception as e:
                    logging.error(f"Ishchiga xabar yuborishda xato: {e}")
            
            await message.answer(success_text, reply_markup=admin_main_kb())
        else:
            error_text = (
                f"❌ {format_bold('AVANS YOZISHDA XATOLIK')}\n"
                f"────────────────\n\n"
                f"<b>Avans yozish amalga oshirilmadi.</b>\n"
                f"Iltimos, qaytadan urinib ko'ring."
            )
            await message.answer(error_text, reply_markup=admin_main_kb())
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "⚠️ <b>Noto'g'ri format!</b>\n\n"
            "Iltimos, faqat raqam kiriting:\n"
            "<i>Masalan: 500000</i>",
            reply_markup=cancel_kb
        )
    except Exception as e:
        logging.error(f"Avans yozishda xato: {e}")
        error_text = (
            f"❌ {format_bold('TIZIM XATOSI')}\n"
            f"────────────────\n\n"
            f"<b>Avans yozishda xatolik yuz berdi.</b>\n"
            f"Iltimos, keyinroq qayta urinib ko'ring."
        )
        await message.answer(error_text, reply_markup=admin_main_kb())
        await state.clear()

# --- AVANS TASDIQLASH CALLBACK HANDLERLARI ---
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

# --- STATISTIKA CALLBACK HANDLER ---
@router.callback_query(F.data == "stats")
async def show_stats(call: CallbackQuery):
    """Statistika ko'rsatish"""
    await call.message.delete()
    
    stats_text = (
        f"📊 {format_bold('TIZIM STATISTIKASI')}\n"
        f"────────────────\n\n"
        f"🔄 Statistika funksiyasi tez orada qo'shiladi...\n\n"
        f"<i>Hozircha 'Joriy holat' bo'limidan foydalaning.</i>"
    )
    await call.message.answer(stats_text, reply_markup=admin_main_kb())