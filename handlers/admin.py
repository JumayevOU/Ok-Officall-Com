from aiogram import Router, F
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.states import AddWorker, DailyReport, AddAdvance, DeleteWorker, EditWorker
from utils.keyboards import admin_main, cancel_kb, settings_kb, edit_options
from database import requests as db
from utils.excel_gen import generate_report
import os
import random
from datetime import datetime

router = Router()
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
except:
    ADMIN_ID = 0

router.message.filter(F.from_user.id == ADMIN_ID)

# --- DIZAYN UCHUN YORDAMCHI FUNKSIYA ---
def to_bold(text):
    # Oddiy harflarni Unicode Bold harflarga aylantiradi
    trans = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳"
    )
    return text.translate(trans)

# --- 1. SOZLAMALAR (BOSHQARUV MARKAZI) ---
@router.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(message: Message):
    header = to_bold("BOSHQARUV MARKAZI")
    text = (
        f"⚙️ {header}\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        "<i>Quyidagi amallardan birini tanlang:</i>"
    )
    await message.answer(text, reply_markup=settings_kb)

# --- YANGI QO'SHISH ---
@router.callback_query(F.data == "set_add")
async def btn_add_worker(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.set_state(AddWorker.name)
    await call.message.answer("✍️ <b>Yangi xodimning ismi nima?</b>\n\n<i>Masalan: Aliyev Vali</i>", reply_markup=cancel_kb)

@router.message(AddWorker.name)
async def add_name(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); await message.answer("❌ Bekor qilindi", reply_markup=admin_main); return
    await state.update_data(name=message.text)
    await state.set_state(AddWorker.rate)
    await message.answer("💸 <b>Soatlik ish haqi qancha?</b>\n\n<i>Faqat raqam yozing (so'mda)</i>", reply_markup=cancel_kb)

@router.message(AddWorker.rate)
async def add_rate(message: Message, state: FSMContext):
    try:
        await state.update_data(rate=float(message.text))
        await state.set_state(AddWorker.location)
        await message.answer("📍 <b>Qaysi blokda ishlaydi?</b>\n(A Blok, H Blok...)", reply_markup=cancel_kb)
    except:
        await message.answer("⚠️ <i>Raqam yozing!</i>")

@router.message(AddWorker.location)
async def add_loc(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); return
    data = await state.get_data()
    code = random.randint(100, 999)
    await db.add_worker(data['name'], data['rate'], code, message.text)
    await state.clear()
    
    header = to_bold("MUVAFFAQIYATLI QO'SHILDI")
    msg = (
        f"✅ {header}\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        f"👤 Xodim: <b>{data['name']}</b>\n"
        f"📍 Joyi: <b>{message.text}</b>\n"
        f"🔑 𝐊𝐈𝐑𝐈𝐒𝐇 𝐊𝐎𝐃𝐈: <code>{code}</code>\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        "<i>Bu kodni xodimga bering.</i>"
    )
    await message.answer(msg, reply_markup=admin_main)

# --- TAHRIRLASH (EDIT) ---
@router.callback_query(F.data == "set_edit")
async def btn_edit_worker(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.set_state(EditWorker.waiting_id)
    header = to_bold("TAHRIRLASH")
    await call.message.answer(f"✏️ {header}\n\n🆔 <b>Xodimning ID raqamini yozing:</b>\n<i>(Ro'yxatdan ko'rib oling)</i>", reply_markup=cancel_kb)

@router.message(EditWorker.waiting_id)
async def edit_ask_field(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); await message.answer("Bekor", reply_markup=admin_main); return
    if not message.text.isdigit(): await message.answer("⚠️ ID raqam bo'lishi kerak"); return
    
    await state.update_data(wid=int(message.text))
    await state.set_state(EditWorker.waiting_field)
    await message.answer("Nimani o'zgartiramiz?", reply_markup=edit_options)

@router.callback_query(EditWorker.waiting_field)
async def edit_field_handler(call: CallbackQuery, state: FSMContext):
    field_map = {'edit_name': 'name', 'edit_rate': 'rate', 'edit_loc': 'location'}
    selected = field_map[call.data]
    await state.update_data(field=selected)
    await state.set_state(EditWorker.waiting_value)
    
    msgs = {
        'name': "✍️ <b>Yangi ismni kiriting:</b>", 
        'rate': "💸 <b>Yangi narxni kiriting:</b>", 
        'location': "📍 <b>Yangi blok nomini kiriting:</b>"
    }
    await call.message.edit_text(msgs[selected])

@router.message(EditWorker.waiting_value)
async def edit_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    val = message.text
    if data['field'] == 'rate':
        try: val = float(val)
        except: await message.answer("⚠️ Raqam yozing!"); return
    await db.update_worker_field(data['wid'], data['field'], val)
    await state.clear()
    await message.answer("✅ <b>Muvaffaqiyatli o'zgartirildi!</b>", reply_markup=admin_main)

# --- O'CHIRISH (DELETE) ---
@router.callback_query(F.data == "set_del")
async def btn_del_worker(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.set_state(DeleteWorker.waiting_id)
    header = to_bold("O'CHIRISH")
    await call.message.answer(f"🗑 {header}\n\n🆔 <b>Xodimning ID raqamini yozing:</b>", reply_markup=cancel_kb)

@router.message(DeleteWorker.waiting_id)
async def delete_confirm(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); await message.answer("Bekor", reply_markup=admin_main); return
    if not message.text.isdigit(): await message.answer("⚠️ ID raqam bo'lishi kerak"); return
    
    w_id = int(message.text)
    await db.archive_worker_date(w_id)
    await state.clear()
    await message.answer(f"✅ <b>{w_id}-xodim arxivlandi!</b>\n<i>Endi ro'yxatda ko'rinmaydi.</i>", reply_markup=admin_main)

# --- 2. ISHCHILAR RO'YXATI ---
@router.message(F.text == "👥 Ishchilar")
async def show_workers(message: Message):
    workers = await db.get_active_workers()
    header = to_bold("ISHCHILAR RO'YXATI")
    text = f"📋 {header}\n➖➖➖➖➖➖➖➖➖➖\n\n"
    
    if not workers: text += "<i>Ro'yxat bo'm-bo'sh.</i>"
    else:
        for w in workers:
            loc = w.get('location', 'Umumiy')
            text += f"🆔 <code>{w['id']}</code>  👤 <b>{w['name']}</b>\n"
            text += f"📍 <i>{loc}</i>  |  💵 {w['rate']:,}\n"
            text += "───────────────\n"
            
    text += "\n👇 <i>O'zgartirish uchun 'Sozlamalar'ga kiring.</i>"
    await message.answer(text)

# --- 3. HISOBOT ---
@router.message(F.text == "📝 Bugungi hisobot")
async def start_rep(message: Message, state: FSMContext):
    workers = await db.get_active_workers()
    if not workers: await message.answer("⚠️ Ishchi yo'q"); return
    await state.set_state(DailyReport.entering_hours)
    await state.update_data(queue=workers, index=0)
    w = workers[0]
    
    header = to_bold("DAVOMAT")
    msg = (
        f"📝 {header}\n➖➖➖➖➖➖➖➖\n"
        f"👤 <b>{w['name']}</b>\n"
        f"📍 <i>{w['location']}</i>\n\n"
        "👉 <b>Bugun necha soat ishladi?</b>"
    )
    await message.answer(msg, reply_markup=cancel_kb)

@router.message(DailyReport.entering_hours)
async def process_rep(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); await message.answer("⏹ To'xtatildi", reply_markup=admin_main); return
    try:
        hours = float(message.text)
        data = await state.get_data()
        idx = data['index']
        worker = data['queue'][idx]
        await db.add_attendance(worker['id'], hours, "Keldi" if hours > 0 else "Kelmadi")
        
        if idx + 1 < len(data['queue']):
            next_w = data['queue'][idx+1]
            await state.update_data(index=idx+1)
            msg = (
                f"👤 <b>{next_w['name']}</b>\n"
                f"📍 <i>{next_w['location']}</i>\n\n"
                "👉 <b>Necha soat?</b>"
            )
            await message.answer(msg, reply_markup=cancel_kb)
        else:
            await state.clear()
            header = to_bold("YAKUNLANDI")
            await message.answer(f"✅ {header}\n<i>Barcha ma'lumotlar saqlandi!</i>", reply_markup=admin_main)
    except:
        await message.answer("⚠️ <i>Faqat raqam yozing!</i>")

# --- 4. JORIY HOLAT ---
@router.message(F.text == "📊 Joriy holat")
async def current_status(message: Message):
    now = datetime.now()
    workers = await db.get_active_workers()
    attendance = await db.get_month_attendance(now.year, now.month)
    advances = await db.get_month_advances(now.year, now.month)
    att_map = {}
    for row in attendance: att_map[row['worker_id']] = att_map.get(row['worker_id'], 0) + row['hours']
    adv_map = {row['worker_id']: row['total'] for row in advances}

    header = to_bold(f"JORIY HOLAT ({now.strftime('%B')})")
    text = f"📊 {header}\n➖➖➖➖➖➖➖➖➖➖\n\n"
    
    total = 0
    if not workers: text += "<i>Ma'lumot yo'q.</i>"
    else:
        for w in workers:
            hours = att_map.get(w['id'], 0)
            adv = adv_map.get(w['id'], 0)
            final = (hours * w['rate']) - adv
            total += final
            
            text += f"👤 <b>{w['name']}</b>\n"
            text += f"⏱ <code>{hours} soat</code>  |  💸 Avans: <code>{adv:,.0f}</code>\n"
            text += f"💰 <b>{final:,.0f} so'm</b>\n"
            text += "───────────────\n"
            
    text += f"\n💵 𝐉𝐀𝐌𝐈 𝐊𝐀𝐒𝐒𝐀: <code>{total:,.0f} so'm</code>"
    await message.answer(text)

# --- 5. EXCEL ---
@router.message(F.text == "📥 Excel (Oy yakuni)")
async def download_excel(message: Message):
    msg = await message.answer("⏳ <i>Hisobot shakllantirilmoqda...</i>")
    now = datetime.now()
    workers = await db.get_workers_for_report(now.year, now.month)
    att = await db.get_month_attendance(now.year, now.month)
    adv = await db.get_month_advances(now.year, now.month)
    att_dict = {(row['worker_id'], row['date_str']): row['hours'] for row in att}
    adv_dict = {row['worker_id']: row['total'] for row in adv}
    try:
        filename = generate_report(now.year, now.month, workers, att_dict, adv_dict)
        await msg.delete()
        caption = to_bold(f"{now.strftime('%B')} OYI HISOBOTI")
        await message.answer_document(FSInputFile(filename), caption=f"📊 {caption}")
        os.remove(filename)
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")

# --- 6. AVANS (ADMIN) ---
@router.message(F.text == "💰 Avans yozish")
async def start_avans(message: Message, state: FSMContext):
    await state.set_state(AddAdvance.worker_select)
    await message.answer("🆔 <b>Xodimning ID raqamini yozing:</b>", reply_markup=cancel_kb)

@router.message(AddAdvance.worker_select)
async def avans_worker(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); return
    if not message.text.isdigit(): await message.answer("⚠️ ID bo'lishi kerak"); return
    await state.update_data(wid=int(message.text))
    await state.set_state(AddAdvance.amount)
    await message.answer("💸 <b>Summani kiriting:</b>", reply_markup=cancel_kb)

@router.message(AddAdvance.amount)
async def avans_amount(message: Message, state: FSMContext):
    try:
        await db.add_advance_money((await state.get_data())['wid'], float(message.text))
        await state.clear()
        await message.answer("✅ <b>Avans yozildi!</b>", reply_markup=admin_main)
    except:
        await message.answer("Xato summa")

# --- AVANS TASDIQLASH (CALLBACK) ---
@router.callback_query(F.data.startswith("app_adv_"))
async def approve_advance(call: CallbackQuery):
    parts = call.data.split("_")
    wid = int(parts[2])
    amount = float(parts[3])
    await db.add_advance_money(wid, amount)
    header = to_bold("AVANS TASDIQLANDI")
    await call.message.edit_text(f"✅ {header}\n\n🆔 ID: {wid}\n💰 {amount:,.0f} so'm")

@router.callback_query(F.data.startswith("rej_adv_"))
async def reject_advance(call: CallbackQuery):
    await call.message.edit_text("🚫 <b>Avans rad etildi.</b>")