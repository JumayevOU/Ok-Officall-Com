from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from utils.states import AddWorker, DailyReport, AddAdvance
from utils.keyboards import admin_main, cancel_kb
from database import requests as db
from openpyxl import Workbook
import os
from datetime import datetime

router = Router()
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Filter: Faqat admin uchun
router.message.filter(F.from_user.id == ADMIN_ID)

# --- ISHCHI QO'SHISH ---
@router.message(F.text == "👥 Ishchilar")
async def show_workers(message: Message):
    workers = await db.get_active_workers()
    text = "👷‍♂️ **Ishchilar:**\n"
    for w in workers:
        text += f"🆔 {w['id']} | {w['name']} | {w['rate']}\n"
    text += "\nYangi ishchi qo'shish uchun: /add_worker\nO'chirish uchun: /del_worker ID"
    await message.answer(text)

@router.message(F.text == "/add_worker")
async def start_add(message: Message, state: FSMContext):
    await state.set_state(AddWorker.name)
    await message.answer("Ishchi Ismi:", reply_markup=cancel_kb)

@router.message(AddWorker.name)
async def add_name(message: Message, state: FSMContext):
    if message.text == "Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi", reply_markup=admin_main)
        return
    await state.update_data(name=message.text)
    await state.set_state(AddWorker.rate)
    await message.answer("Soatlik narxi (so'mda):", reply_markup=cancel_kb)

@router.message(AddWorker.rate)
async def add_rate(message: Message, state: FSMContext):
    try:
        rate = float(message.text)
        data = await state.get_data()
        # Random code generatsiya qilish o'rniga oddiy input qilsak ham bo'ladi
        # Hozircha soddalik uchun timestamp ishlatamiz yoki qo'lda kiritish
        import random
        code = random.randint(100, 999) 
        
        await db.add_worker(data['name'], rate, code)
        await state.clear()
        await message.answer(f"✅ {data['name']} qo'shildi!\n🔑 Kirish kodi: {code}", reply_markup=admin_main)
    except:
        await message.answer("Raqam kiriting!")

# --- BUGUNGI HISOBOT (CYCLE) ---
@router.message(F.text == "📝 Bugungi hisobot")
async def start_report(message: Message, state: FSMContext):
    workers = await db.get_active_workers()
    if not workers:
        await message.answer("Ishchilar yo'q!")
        return
    
    await state.set_state(DailyReport.entering_hours)
    await state.update_data(queue=workers, index=0)
    
    first = workers[0]
    await message.answer(f"👤 **{first['name']}** necha soat ishladi?\n(0 - kelmadi)", reply_markup=cancel_kb)

@router.message(DailyReport.entering_hours)
async def process_hours(message: Message, state: FSMContext):
    if message.text == "Bekor qilish":
        await state.clear()
        await message.answer("To'xtatildi", reply_markup=admin_main)
        return
        
    try:
        hours = float(message.text)
        data = await state.get_data()
        workers = data['queue']
        idx = data['index']
        
        current_worker = workers[idx]
        status = "Keldi" if hours > 0 else "Kelmadi"
        
        await db.add_attendance(current_worker['id'], hours, status)
        
        next_idx = idx + 1
        if next_idx < len(workers):
            await state.update_data(index=next_idx)
            next_worker = workers[next_idx]
            await message.answer(f"👤 **{next_worker['name']}** necha soat?", reply_markup=cancel_kb)
        else:
            await state.clear()
            await message.answer("✅ Hisobot tugadi!", reply_markup=admin_main)
    except ValueError:
        await message.answer("Faqat raqam yozing!")

# --- EXCEL YUKLASH ---
@router.message(F.text == "📥 Excel (Oy yakuni)")
async def download_excel(message: Message):
    data = await db.get_monthly_report_data()
    
    wb = Workbook()
    ws = wb.active
    ws.append(["Ism", "Soatlik Narx", "Jami Soat", "Avans", "Hisoblangan Oylik", "Qo'lga Tegadi"])
    
    for row in data:
        name = row['name']
        rate = row['rate']
        hours = row['total_hours']
        adv = row['total_advance']
        salary = hours * rate
        final = salary - adv
        ws.append([name, rate, hours, adv, salary, final])
        
    filename = "oylik_hisobot.xlsx"
    wb.save(filename)
    
    await message.answer_document(FSInputFile(filename), caption="📊 Oylik hisobot")
    os.remove(filename)