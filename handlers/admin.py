from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from utils.states import AddWorker, DailyReport, AddAdvance
from utils.keyboards import admin_main, cancel_kb
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

# --- 1. ISHCHI QO'SHISH ---
@router.message(F.text == "👥 Ishchilar")
async def show_workers(message: Message):
    workers = await db.get_active_workers()
    text = "👷‍♂️ **Korxona Ishchilari:**\n\n"
    if not workers:
        text += "❌ Hozircha ishchilar yo'q."
    else:
        for w in workers:
            loc = w.get('location', 'Umumiy')
            text += f"📍 **{loc}** | {w['name']} | 💵 {w['rate']:,} so'm\n"
            
    text += "\n👇 Yangi ishchi qo'shish uchun bosing: /add_worker"
    await message.answer(text)

@router.message(F.text == "/add_worker")
async def start_add(message: Message, state: FSMContext):
    await state.set_state(AddWorker.name)
    await message.answer("📝 Yangi ishchining **Ism Familiyasini** kiriting:", reply_markup=cancel_kb)

@router.message(AddWorker.name)
async def add_name(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); await message.answer("Bekor qilindi", reply_markup=admin_main); return
    await state.update_data(name=message.text)
    await state.set_state(AddWorker.rate)
    await message.answer("💵 **Soatlik narxi** qancha? (So'mda yozing)\nMasalan: 25000", reply_markup=cancel_kb)

@router.message(AddWorker.rate)
async def add_rate(message: Message, state: FSMContext):
    try:
        val = float(message.text)
        await state.update_data(rate=val)
        await state.set_state(AddWorker.location)
        await message.answer("🏗 Ishchi qaysi **Blokda** ishlaydi?\n(Masalan: A Blok, H Blok)", reply_markup=cancel_kb)
    except:
        await message.answer("⚠️ Iltimos, faqat raqam yozing!")

@router.message(AddWorker.location)
async def add_loc(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); return
    
    data = await state.get_data()
    code = random.randint(100, 999)
    location = message.text
    
    await db.add_worker(data['name'], data['rate'], code, location)
    await state.clear()
    
    text = (
        f"✅ **Yangi ishchi qo'shildi!**\n\n"
        f"👤 Ismi: {data['name']}\n"
        f"📍 Joyi: {location}\n"
        f"🔑 **KIRISH KODI:** `{code}`\n"
        f"(Bu kodni ishchiga bering, u botga kirishi uchun kerak)"
    )
    await message.answer(text, reply_markup=admin_main)

# --- 2. BUGUNGI HISOBOT ---
@router.message(F.text == "📝 Bugungi hisobot")
async def start_rep(message: Message, state: FSMContext):
    workers = await db.get_active_workers()
    if not workers: 
        await message.answer("⚠️ Avval ishchi qo'shing!")
        return
    
    await state.set_state(DailyReport.entering_hours)
    await state.update_data(queue=workers, index=0)
    
    w = workers[0]
    await message.answer(f"👤 **{w['name']}** ({w['location']})\nBugun necha soat ishladi?", reply_markup=cancel_kb)

@router.message(DailyReport.entering_hours)
async def process_rep(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); await message.answer("To'xtatildi", reply_markup=admin_main); return
    
    try:
        hours = float(message.text)
        data = await state.get_data()
        idx = data['index']
        worker = data['queue'][idx]
        
        status = "Keldi" if hours > 0 else "Kelmadi"
        await db.add_attendance(worker['id'], hours, status)
        
        if idx + 1 < len(data['queue']):
            next_w = data['queue'][idx+1]
            await state.update_data(index=idx+1)
            await message.answer(f"👤 **{next_w['name']}** ({next_w['location']})\nBugun necha soat?", reply_markup=cancel_kb)
        else:
            await state.clear()
            await message.answer("✅ **Barcha hisobotlar muvaffaqiyatli saqlandi!**", reply_markup=admin_main)
    except ValueError:
        await message.answer("⚠️ Faqat raqam yozing (Masalan: 8, 10, 0)")

# --- 3. JORIY HOLAT ---
@router.message(F.text == "📊 Joriy holat")
async def current_status(message: Message):
    now = datetime.now()
    workers = await db.get_active_workers()
    attendance = await db.get_month_attendance(now.year, now.month)
    advances = await db.get_month_advances(now.year, now.month)
    
    att_map = {}
    for row in attendance:
        wid = row['worker_id']
        att_map[wid] = att_map.get(wid, 0) + row['hours']

    adv_map = {row['worker_id']: row['total'] for row in advances}

    text = f"📅 **{now.strftime('%B')} oyi uchun holat:**\n\n"
    total_payroll = 0 
    
    if not workers:
        text += "Ma'lumot yo'q."
    else:
        for w in workers:
            wid = w['id']
            hours = att_map.get(wid, 0)
            adv = adv_map.get(wid, 0)
            
            salary = hours * w['rate']
            final = salary - adv
            total_payroll += final
            
            text += f"👤 **{w['name']}**\n"
            text += f"⏳ {hours} soat | 💸 Avans: {adv:,.0f}\n"
            text += f"💰 Qo'lga: **{final:,.0f} so'm**\n"
            text += "➖" * 8 + "\n"
            
    text += f"\n💵 **JAMI KASSA:** {total_payroll:,.0f} so'm"
    await message.answer(text)

# --- 4. EXCEL ---
@router.message(F.text == "📥 Excel (Oy yakuni)")
async def download_excel(message: Message):
    await message.answer("⏳ Hisobot tayyorlanmoqda...")
    now = datetime.now()
    
    workers = await db.get_active_workers() # Location bilan oladi
    attendance = await db.get_month_attendance(now.year, now.month)
    advances = await db.get_month_advances(now.year, now.month)
    
    att_dict = {(row['worker_id'], row['date_str']): row['hours'] for row in attendance}
    adv_dict = {row['worker_id']: row['total'] for row in advances}
    
    try:
        filename = generate_report(now.year, now.month, workers, att_dict, adv_dict)
        await message.answer_document(FSInputFile(filename), caption=f"📊 **{now.strftime('%B')} oyi hisoboti**")
        os.remove(filename)
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

# --- 5. AVANS ---
@router.message(F.text == "💰 Avans yozish")
async def start_avans(message: Message, state: FSMContext):
    await state.set_state(AddAdvance.worker_select)
    await message.answer("🆔 Ishchining ID raqamini kiriting:", reply_markup=cancel_kb)

@router.message(AddAdvance.worker_select)
async def avans_worker(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); return
    if not message.text.isdigit(): await message.answer("⚠️ ID raqam bo'lishi kerak!"); return

    await state.update_data(wid=int(message.text))
    await state.set_state(AddAdvance.amount)
    await message.answer("💸 Summani kiriting:", reply_markup=cancel_kb)

@router.message(AddAdvance.amount)
async def avans_amount(message: Message, state: FSMContext):
    try:
        val = float(message.text)
        data = await state.get_data()
        await db.add_advance_money(data['wid'], val)
        await state.clear()
        await message.answer("✅ **Avans muvaffaqiyatli yozildi!**", reply_markup=admin_main)
    except:
        await message.answer("⚠️ Summa noto'g'ri!")

# --- 6. SOZLAMALAR ---
@router.message(F.text == "⚙️ Sozlamalar")
async def settings(message: Message):
    text = (
        f"⚙️ **Tizim Sozlamalari**\n\n"
        f"👑 Admin ID: `{message.from_user.id}`\n"
        f"📅 Bugun: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"🛡 Versiya: 3.0 Stable"
    )
    await message.answer(text)