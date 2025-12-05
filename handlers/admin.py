from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from utils.states import AddWorker, EditWorker, DeleteWorker, DailyReport, AdminAdvance
from utils.keyboards import admin_main_kb, cancel_kb, settings_kb, edit_options_kb, approval_kb, remove_kb, report_kb
from database import requests as db
from utils.excel_gen import generate_report
import os
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

router = Router()

# --- ADMINLAR RO'YXATINI OLISH (MULTI-ADMIN) ---
ADMIN_LIST: List[int] = []
try:
    env_admins = os.getenv("ADMIN_ID", "")
    ADMIN_LIST = [int(id_str.strip()) for id_str in env_admins.split(",") if id_str.strip()]
except (ValueError, TypeError):
    logging.critical("❌ ADMIN_ID .env faylida noto'g'ri ko'rsatilgan! Format: ID1,ID2,ID3")

# FSM ma'lumotlari
fsm_data: Dict[int, Dict[str, Any]] = {}

# Oylar tarjimasi
MONTHS = {
    1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
    5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
    9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr"
}

def format_bold(text: str) -> str:
    """Matnni qalin qilish"""
    return f"<b>{text}</b>"

def generate_unique_code() -> int:
    return random.randint(1000, 9999)

def get_current_time():
    """O'zbekiston vaqtini olish (UTC+5)"""
    return datetime.utcnow() + timedelta(hours=5)

# --- TEKSHIRUV FUNKSIYASI (MULTI-ADMIN) ---
async def is_admin(user_id: int, message: Message = None):
    # Agar user_id ADMIN_LIST ichida bo'lsa, ruxsat beramiz
    if user_id in ADMIN_LIST:
        return True
    
    if message:
        await message.answer(
            f"⚠️ <b>Ruxsat yo'q!</b>\n\n"
            f"Sizning ID: <code>{user_id}</code>\n"
            f"<i>Ushbu ID adminlar ro'yxatida yo'q.</i>"
        )
    return False

# --- ASOSIY MENYU HANDLERLARI ---

@router.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id, message): return
    await state.clear()
    
    menu_text = (
        f"⚙️ {format_bold('BOSHQARUV MARKAZI')}\n"
        f"────────────────\n\n"
        f"🛠️ <b>Tizim sozlamalari</b>\n"
        f"Quyidagi amallardan birini tanlang:"
    )
    await message.answer(menu_text, reply_markup=settings_kb)

@router.message(F.text == "👥 Ishchilar")
async def show_workers_list(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id, message): return
    await state.clear()
    
    try:
        workers = await db.get_active_workers()
        
        header = (
            f"📋 {format_bold('ISHCHILAR ROYXATI')}\n"
            f"────────────────\n\n"
        )
        
        if not workers:
            await message.answer(header + "<i>🤷 Hozircha ishchilar ro'yxati bo'sh</i>", reply_markup=admin_main_kb())
            return

        # --- Xabarni bo'laklash (Chunking) ---
        current_text = header
        
        for worker in workers:
            # Login qilganmi yoki yo'q (telegram_id borligiga qarab)
            status_icon = "🟢" if worker.get('telegram_id') else "⚪️"
            
            worker_info = (
                f"{status_icon} 🆔 <b>ID:</b> <code>{worker['id']}</code>\n"
                f"👤 <b>Ism:</b> {worker['name']}\n"
                f"💰 <b>Stavka:</b> {worker['rate']:,.0f} so'm/soat\n"
                f"🔑 <b>KOD:</b> <code>{worker['code']}</code>\n"
                f"➖➖➖➖➖➖➖➖➖➖➖\n"
            )
            
            # Agar xabar uzunligi 4000 belgidan oshsa, jo'natamiz va yangisini boshlaymiz
            if len(current_text) + len(worker_info) > 4000:
                await message.answer(current_text)
                current_text = "" # Bo'shatish
            
            current_text += worker_info
        
        # Oxirgi qismni va footer ni qo'shib jo'natamiz
        footer = "\n👇 <i>O'zgartirish kiritish uchun 'Sozlamalar' menyusidan foydalaning</i>\n🟢 - Botga ulangan\n⚪️ - Hali kirmagan"
        
        if len(current_text) + len(footer) > 4000:
             await message.answer(current_text)
             await message.answer(footer, reply_markup=admin_main_kb())
        else:
             current_text += footer
             await message.answer(current_text, reply_markup=admin_main_kb())

    except Exception as e:
        logging.error(f"Ishchilar ro'yxatida xato: {e}")
        await message.answer("❌ <b>Ma'lumotlar bazasidan o'qishda xatolik bo'ldi.</b>")

@router.message(F.text == "📊 Joriy holat")
async def show_current_status(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id, message): return
    await state.clear()
    
    try:
        now = get_current_time() # Vaqt to'g'irlandi
        workers = await db.get_active_workers()
        attendance, advances = await db.get_month_data(now.year, now.month)
        
        # Ma'lumotlarni tayyorlash
        attendance_dict = {}
        for record in attendance:
            worker_id = record['worker_id']
            hours = record['hours']
            attendance_dict[worker_id] = attendance_dict.get(worker_id, 0) + hours
        
        advances_dict = {}
        for record in advances:
            worker_id = record['worker_id']
            total = record['total']
            advances_dict[worker_id] = total
        
        # Oyni o'zbekcha chiqarish
        month_name = MONTHS.get(now.month, str(now.month))
        
        header = (
            f"📊 {format_bold('JORIY HOLAT')}\n"
            f"🗓 {month_name} {now.year}\n"
            f"────────────────\n\n"
        )
        
        if not workers:
            await message.answer(header + "<i>🤷 Hozircha ma'lumot yo'q</i>", reply_markup=admin_main_kb())
            return

        # --- Xabarni bo'laklash ---
        current_text = header
        total_salary = 0
        
        for worker in workers:
            total_hours = attendance_dict.get(worker['id'], 0)
            advance = advances_dict.get(worker['id'], 0)
            salary = total_hours * float(worker['rate'])
            net_salary = salary - float(advance)
            
            total_salary += net_salary
            
            worker_info = (
                f"👤 {worker['name']}\n"
                f"⏱ {total_hours} soat | "
                f"💸 {advance:,.0f} so'm avans\n"
                f"💰 <b>{net_salary:,.0f} so'm</b>\n\n"
            )
            
            if len(current_text) + len(worker_info) > 4000:
                await message.answer(current_text)
                current_text = ""
            
            current_text += worker_info
            
        footer = f"💵 <b>JAMI KASSA: {total_salary:,.0f} so'm</b>"
        
        if len(current_text) + len(footer) > 4000:
            await message.answer(current_text)
            final_msg = footer
        else:
            final_msg = current_text + footer
        
        # Agar callback orqali chaqirilgan bo'lsa
        if isinstance(message, CallbackQuery):
             await message.message.answer(final_msg, reply_markup=admin_main_kb())
        else:
             await message.answer(final_msg, reply_markup=admin_main_kb())

    except Exception as e:
        logging.error(f"Status xatosi: {e}")
        if isinstance(message, Message):
            await message.answer(f"❌ Xatolik yuz berdi: {e}")

@router.message(F.text == "📥 Excel hisobot")
async def generate_excel_report(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id, message): return
    await state.clear()
    
    processing_msg = await message.answer("🔄 <i>Hisobot tayyorlanmoqda...</i>")
    
    try:
        now = get_current_time() # Vaqt to'g'irlandi
        
        # Bazadan ma'lumot olish
        workers = await db.get_workers_for_report(now.year, now.month)
        attendance = await db.get_month_attendance(now.year, now.month)
        advances = await db.get_month_advances(now.year, now.month)
        
        if not workers:
            await processing_msg.delete()
            await message.answer("⚠️ <b>Hisobot uchun ma'lumot topilmadi.</b>\nBazada ishchilar borligiga ishonch hosil qiling.", reply_markup=admin_main_kb())
            return
        
        # Ma'lumotlarni tayyorlash
        attendance_dict = {}
        for record in attendance:
            key = (record['worker_id'], record['date_str'])
            attendance_dict[key] = float(record['hours'])
        
        advances_dict = {}
        for record in advances:
            advances_dict[record['worker_id']] = float(record['total'])
        
        # Excel yaratish
        filename = generate_report(now.year, now.month, workers, attendance_dict, advances_dict)
        
        await processing_msg.delete()
        
        # Faylni yuborish (O'zbekcha oy)
        month_name = MONTHS.get(now.month, str(now.month))
        caption = (
            f"📊 {format_bold(f'{month_name} {now.year} OYI HISOBOTI')}\n"
            f"────────────────\n\n"
            f"👥 Ishchilar: {len(workers)} ta\n"
            f"📅 Sana: {now.strftime('%d.%m.%Y %H:%M')}"
        )
        
        await message.answer_document(
            FSInputFile(filename),
            caption=caption
        )
        
        try:
            os.remove(filename)
        except:
            pass
        
    except Exception as e:
        await processing_msg.delete()
        logging.error(f"Excel hisobot xatosi: {e}")
        await message.answer(f"❌ <b>Hisobot yaratishda xatolik:</b>\n\n{str(e)}", reply_markup=admin_main_kb())

# --- YANGI ISHCHI QO'SHISH ---
@router.callback_query(F.data == "add_worker")
async def start_add_worker(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.set_state(AddWorker.name)
    
    prompt_text = (
        f"👤 {format_bold('YANGI ISHCHI QOSHISH')}\n"
        f"────────────────\n\n"
        f"✍️ <b>Yangi ishchining to'liq ism-familiyasini kiriting:</b>\n"
        f"<i>Masalan: Aliyev Valijon</i>"
    )
    await call.message.answer(prompt_text, reply_markup=cancel_kb)

@router.message(AddWorker.name)
async def process_worker_name(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Amal bekor qilindi", reply_markup=admin_main_kb())
        return
    
    await state.update_data(name=message.text.strip())
    await state.set_state(AddWorker.rate)
    await message.answer(f"💸 <b>{message.text} uchun soatlik ish haqqini kiriting (so'mda):</b>", reply_markup=cancel_kb)

@router.message(AddWorker.rate)
async def process_worker_rate(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Amal bekor qilindi", reply_markup=admin_main_kb())
        return
    
    try:
        rate = float(message.text.strip())
        data = await state.get_data()
        code = generate_unique_code()
        
        success = await db.add_worker(data['name'], rate, code)
        
        if success:
            await message.answer(
                f"✅ <b>Ishchi qo'shildi!</b>\n\n"
                f"👤 {data['name']}\n"
                f"🔑 Kod: <code>{code}</code>\n\n"
                f"<i>Kodni ishchiga bering.</i>",
                reply_markup=admin_main_kb()
            )
        else:
            await message.answer("❌ Xatolik! Kod takrorlandi yoki baza xatosi.", reply_markup=admin_main_kb())
            
    except ValueError:
        await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
    except Exception as e:
        await message.answer(f"❌ Tizim xatosi: {e}")
    
    await state.clear()

# --- AVANS YOZISH (Admin tomonidan) ---
@router.message(F.text == "💰 Avans yozish")
async def start_admin_advance(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id, message): return
    await state.clear()
    await state.set_state(AdminAdvance.select_worker)
    await message.answer("🔎 <b>Ishchini topish uchun ID raqamini yoki ismini yozing:</b>", reply_markup=cancel_kb)

@router.message(AdminAdvance.select_worker)
async def process_worker_selection(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Bekor qilindi", reply_markup=admin_main_kb())
        return
    
    search = message.text.strip()
    worker = None
    
    if search.isdigit():
        worker = await db.get_worker_by_id(int(search))
        if worker and not worker['active']: worker = None
    else:
        workers = await db.search_worker_by_name(search)
        if len(workers) == 1:
            worker = workers[0]
        elif len(workers) > 1:
            text = "🔍 <b>Bir nechta ishchi topildi, ID sini kiriting:</b>\n\n"
            for w in workers:
                text += f"🆔 <code>{w['id']}</code> - {w['name']}\n"
            await message.answer(text)
            return
    
    if worker:
        await state.update_data(worker_id=worker['id'], worker_name=worker['name'])
        await state.set_state(AdminAdvance.enter_amount)
        await message.answer(f"✅ <b>{worker['name']}</b> topildi.\n💸 Avans summasini kiriting:", reply_markup=cancel_kb)
    else:
        await message.answer("❌ Ishchi topilmadi, qayta urinib ko'ring:", reply_markup=cancel_kb)

@router.message(AdminAdvance.enter_amount)
async def process_advance_amount(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Bekor qilindi", reply_markup=admin_main_kb())
        return

    try:
        amount = float(message.text.strip())
        data = await state.get_data()
        
        success = await db.add_advance(data['worker_id'], amount)
        if success:
            await message.answer(f"✅ <b>{data['worker_name']}</b> ga {amount:,.0f} so'm avans yozildi.", reply_markup=admin_main_kb())
            
            # Ishchiga xabar
            worker = await db.get_worker_by_id(data['worker_id'])
            if worker and worker['telegram_id']:
                try:
                    await message.bot.send_message(worker['telegram_id'], f"💰 Sizga {amount:,.0f} so'm avans yozildi.")
                except: pass
        else:
            await message.answer("❌ Bazaga yozishda xatolik!", reply_markup=admin_main_kb())
            
    except ValueError:
        await message.answer("⚠️ Faqat raqam kiriting!")
    
    await state.clear()

# --- BUGUNGI HISOBOT ---
@router.message(F.text == "📝 Bugungi hisobot")
async def start_daily_report(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id, message): return
    await state.clear()
    
    workers = await db.get_active_workers()
    if not workers:
        await message.answer("⚠️ Ishchilar yo'q", reply_markup=admin_main_kb())
        return
    
    fsm_data[message.from_user.id] = {'queue': workers, 'index': 0}
    await state.set_state(DailyReport.enter_hours)
    await show_report_step(message, state)

async def show_report_step(message: Message, state: FSMContext):
    user_data = fsm_data.get(message.from_user.id)
    if not user_data: return
    
    idx = user_data['index']
    workers = user_data['queue']
    
    if idx >= len(workers):
        await message.answer("✅ <b>Barcha ishchilar kiritildi!</b>", reply_markup=admin_main_kb())
        await state.clear()
        del fsm_data[message.from_user.id]
        return
    
    worker = workers[idx]
    # report_kb ishlatilmoqda (O'tkazib yuborish tugmasi bor)
    await message.answer(
        f"👤 <b>{worker['name']}</b> ({idx+1}/{len(workers)})\n\n"
        f"Bugun necha soat ishladi? (0 = kelmadi)",
        reply_markup=report_kb
    )

# YANGI: O'tkazib yuborish handler
@router.message(DailyReport.enter_hours, F.text == "➡️ O'tkazib yuborish")
async def skip_report_item(message: Message, state: FSMContext):
    user_data = fsm_data.get(message.from_user.id)
    if not user_data: return
    
    # Shunchaki indeksni oshiramiz, bazaga hech narsa yozmaymiz
    user_data['index'] += 1
    await message.answer("⏩ O'tkazib yuborildi.")
    await show_report_step(message, state)

@router.message(DailyReport.enter_hours)
async def process_report_hours(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        if message.from_user.id in fsm_data: del fsm_data[message.from_user.id]
        await message.answer("⏹️ To'xtatildi", reply_markup=admin_main_kb())
        return

    try:
        hours = float(message.text.strip())
        user_data = fsm_data.get(message.from_user.id)
        worker = user_data['queue'][user_data['index']]
        
        status = "Keldi" if hours > 0 else "Kelmadi"
        await db.add_attendance(worker['id'], hours, status)
        
        user_data['index'] += 1
        await show_report_step(message, state)
        
    except ValueError:
        await message.answer("⚠️ Faqat raqam kiriting!")

# --- AVANS SO'ROVINI TASDIQLASH (QAYTARILGAN QISM) ---
@router.callback_query(F.data.startswith("approve_adv_"))
async def approve_advance_request(call: CallbackQuery):
    try:
        # data formati: approve_adv_{worker_id}_{amount}
        parts = call.data.split("_")
        worker_id = int(parts[2])
        amount = float(parts[3])
        
        success = await db.add_advance(worker_id, amount, approved=True)
        
        if success:
            await call.message.edit_text(
                f"{call.message.text}\n\n✅ <b>TASDIQLANDI!</b>\n"
                f"👨‍💼 Tasdiqladi: {call.from_user.full_name}"
            )
            
            # Ishchiga xabar yuborish
            worker = await db.get_worker_by_id(worker_id)
            if worker and worker['telegram_id']:
                try:
                    await call.bot.send_message(
                        worker['telegram_id'], 
                        f"✅ <b>Xushxabar!</b>\nSiz so'ragan {amount:,.0f} so'm avans tasdiqlandi."
                    )
                except: pass
        else:
            await call.answer("❌ Bazaga yozishda xatolik!", show_alert=True)
            
    except Exception as e:
        logging.error(f"Approve advance error: {e}")
        await call.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("reject_adv_"))
async def reject_advance_request(call: CallbackQuery):
    try:
        parts = call.data.split("_")
        worker_id = int(parts[2])
        
        await call.message.edit_text(
            f"{call.message.text}\n\n❌ <b>RAD ETILDI!</b>\n"
            f"👨‍💼 Rad etdi: {call.from_user.full_name}"
        )
        
        # Ishchiga xabar
        worker = await db.get_worker_by_id(worker_id)
        if worker and worker['telegram_id']:
            try:
                await call.bot.send_message(
                    worker['telegram_id'], 
                    "❌ <b>Afsuski</b>, sizning avans so'rovingiz rad etildi."
                )
            except: pass
            
    except Exception as e:
        logging.error(f"Reject advance error: {e}")

# --- SOZLAMALAR MENYUSI HANDLERLARI (YANGILANDI) ---
@router.callback_query(F.data == "stats")
async def show_stats_callback(call: CallbackQuery, state: FSMContext):
    # Yangilangan statistika
    await call.message.delete()
    
    stats = await db.get_general_statistics()
    now = get_current_time()
    month_name = MONTHS.get(now.month, str(now.month))
    
    if not stats:
        await call.message.answer("❌ Statistika ma'lumotlari topilmadi", reply_markup=admin_main_kb())
        return

    top_text = "Hozircha yo'q"
    if stats.get('top_worker'):
        top_text = f"{stats['top_worker']['name']} ({stats['top_worker']['hours']} soat)"

    text = (
        f"📊 {format_bold('UMUMIY STATISTIKA')}\n"
        f"🗓 {month_name} {now.year}\n"
        f"────────────────\n\n"
        f"👥 <b>Jami ishchilar:</b> {stats.get('workers', 0)}\n"
        f"⏱ <b>Jami ishlangan soat:</b> {stats.get('hours', 0)}\n"
        f"💸 <b>To'langan avanslar:</b> {stats.get('advance', 0):,.0f} so'm\n\n"
        f"🏆 <b>Oy ilg'ori (Top ishchi):</b>\n"
        f"⭐️ {top_text}"
    )
    
    await call.message.answer(text, reply_markup=admin_main_kb())

@router.callback_query(F.data == "edit_worker")
async def start_edit_worker(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.set_state(EditWorker.waiting_id)
    await call.message.answer("✏️ Tahrirlash uchun ishchi ID sini kiriting:", reply_markup=cancel_kb)

@router.message(EditWorker.waiting_id)
async def process_edit_id(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Bekor qilindi", reply_markup=admin_main_kb())
        return
    if not message.text.isdigit():
        await message.answer("⚠️ ID raqam bo'lishi kerak")
        return
        
    worker = await db.get_worker_by_id(int(message.text))
    if worker:
        await state.update_data(worker_id=worker['id'], worker_name=worker['name'])
        await state.set_state(EditWorker.waiting_field)
        await message.answer(f"👤 {worker['name']}\nNimani o'zgartiramiz?", reply_markup=edit_options_kb)
    else:
        await message.answer("❌ Ishchi topilmadi", reply_markup=cancel_kb)

@router.callback_query(EditWorker.waiting_field)
async def process_edit_field_choice(call: CallbackQuery, state: FSMContext):
    if call.data == "cancel_edit":
        await state.clear()
        await call.message.delete()
        await call.message.answer("✅ Bekor qilindi", reply_markup=admin_main_kb())
        return
        
    field = "name" if call.data == "edit_name" else "rate"
    await state.update_data(edit_field=field)
    await state.set_state(EditWorker.waiting_value)
    
    txt = "Yangi ismni kiriting:" if field == "name" else "Yangi soatlik narxni kiriting:"
    await call.message.edit_text(txt)

@router.message(EditWorker.waiting_value)
async def process_edit_value(message: Message, state: FSMContext):
    data = await state.get_data()
    val = message.text.strip()
    
    if data['edit_field'] == 'rate':
        try: val = float(val)
        except: 
            await message.answer("⚠️ Raqam kiriting!")
            return
            
    await db.update_worker_field(data['worker_id'], data['edit_field'], val)
    await message.answer("✅ Yangilandi!", reply_markup=admin_main_kb())
    await state.clear()

@router.callback_query(F.data == "delete_worker")
async def start_delete_worker(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.set_state(DeleteWorker.waiting_id)
    await call.message.answer("🗑 O'chirish (arxivlash) uchun ID kiriting:", reply_markup=cancel_kb)

@router.message(DeleteWorker.waiting_id)
async def process_delete(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("✅ Bekor qilindi", reply_markup=admin_main_kb())
        return
    if message.text.isdigit():
        success = await db.archive_worker(int(message.text))
        if success:
            await message.answer("✅ Ishchi arxivlandi", reply_markup=admin_main_kb())
        else:
            await message.answer("❌ Xatolik yoki ishchi topilmadi", reply_markup=admin_main_kb())
    await state.clear()
