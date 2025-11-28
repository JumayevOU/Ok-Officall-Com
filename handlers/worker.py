from aiogram import Router, F
from aiogram.types import Message
from utils.keyboards import worker_main, cancel_kb, approval_kb, location_kb
from utils.states import RequestAdvance
from database import requests as db
from aiogram.fsm.context import FSMContext
from utils.geo import calculate_distance
from datetime import datetime, timezone, timedelta
import os

router = Router()
try: ADMIN_ID = int(os.getenv("ADMIN_ID"))
except: ADMIN_ID = 0

def to_bold(text):
    trans = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳")
    return text.translate(trans)

# LIVE LOCATION CHECK
@router.message(F.text == "🏢 Keldim")
async def check_in_start(message: Message, state: FSMContext):
    conn = await db.get_db()
    row = await conn.fetchrow("SELECT id FROM workers WHERE telegram_id=$1", message.from_user.id)
    await conn.close()
    if not row: return
    
    if await db.is_checked_in(row['id']):
        await message.answer("⚠️ <b>Siz allaqachon ishdasiz!</b>", reply_markup=worker_main); return

    await state.set_state("check_in_loc")
    await message.answer("🛡 <b>Iltimos, JONLI LOKATSIYA (Live Location) yuboring.</b>\n<i>Oddiy lokatsiya qabul qilinmaydi.</i>", reply_markup=cancel_kb)

@router.message(F.location, F.state == "check_in_loc") 
async def check_in_verify(message: Message, state: FSMContext):
    if message.location.live_period is None:
        await message.answer("🚫 <b>Faqat Jonli Lokatsiya!</b>"); return

    wl = await db.get_work_location()
    if not wl: await message.answer("⚠️ Lokatsiya o'rnatilmagan"); await state.clear(); return
        
    dist = calculate_distance(message.location.latitude, message.location.longitude, wl[0], wl[1])
    if dist <= 50:
        conn = await db.get_db(); wid = await conn.fetchval("SELECT id FROM workers WHERE telegram_id=$1", message.from_user.id); await conn.close()
        await db.check_in_worker(wid)
        t = datetime.now(timezone(timedelta(hours=5))).strftime("%H:%M")
        head = to_bold("XUSH KELIBSIZ")
        await message.answer(f"✅ {head}\n🕒 {t}\n📍 {int(dist)}m", reply_markup=worker_main)
        await state.clear()
    else:
        await message.answer(f"🚫 <b>Uzoqdasiz: {int(dist)}m</b>\n<i>Yaqinroq keling.</i>")

@router.message(F.text == "🏠 Ketdim")
async def check_out_start(message: Message, state: FSMContext):
    await state.set_state("check_out_loc")
    await message.answer("📍 <b>Ketish uchun ham Jonli Lokatsiya yuboring:</b>", reply_markup=cancel_kb)

@router.message(F.location, F.state == "check_out_loc")
async def check_out_verify(message: Message, state: FSMContext):
    if message.location.live_period is None: await message.answer("🚫 <b>Jonli Lokatsiya kerak!</b>"); return
    
    wl = await db.get_work_location()
    dist = calculate_distance(message.location.latitude, message.location.longitude, wl[0], wl[1])
    
    if dist <= 100:
        conn = await db.get_db(); wid = await conn.fetchval("SELECT id FROM workers WHERE telegram_id=$1", message.from_user.id); await conn.close()
        suc, h = await db.check_out_worker(wid)
        if suc:
            head = to_bold("YAKUNLANDI")
            await message.answer(f"✅ {head}\n⏱ {h} soat", reply_markup=worker_main)
        else: await message.answer(f"⚠️ {h}", reply_markup=worker_main)
        await state.clear()
    else: await message.answer(f"🚫 <b>Uzoqdasiz: {int(dist)}m</b>")

# STATS & ADVANCE
@router.message(F.text == "💰 Mening hisobim")
async def my_stats(message: Message):
    stats = await db.get_worker_stats(message.from_user.id)
    if not stats: await message.answer("⚠️ Ma'lumot yo'q"); return
    sal = stats['hours'] * stats['rate']; fin = sal - stats['advance']
    head = to_bold("SHAXSIY HISOB")
    text = f"🧾 {head}\n👤 <b>{stats['name']}</b>\n⏱ {stats['hours']} soat | 💸 -{stats['advance']:,.0f}\n💰 <b>Qo'lga: {fin:,.0f} so'm</b>"
    await message.answer(text, reply_markup=worker_main)

@router.message(F.text == "💸 Avans so'rash")
async def req_s(message: Message, state: FSMContext):
    await state.set_state(RequestAdvance.amount); await message.answer("💸 <b>Summa:</b>", reply_markup=cancel_kb)

@router.message(RequestAdvance.amount)
async def req_d(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); await message.answer("Bekor", reply_markup=worker_main); return
    try:
        amt = float(message.text)
        conn = await db.get_db(); row = await conn.fetchrow("SELECT id, name FROM workers WHERE telegram_id=$1", message.from_user.id); await conn.close()
        if row:
            head = to_bold("AVANS SO'ROVI")
            await message.bot.send_message(ADMIN_ID, f"🔔 {head}\n👤 {row['name']}\n💰 {amt:,.0f}", reply_markup=approval_kb(row['id'], amt))
            await message.answer("✅ <b>Yuborildi!</b>", reply_markup=worker_main)
        else: await message.answer("⚠️ Profil yo'q")
        await state.clear()
    except: await message.answer("Raqam yozing")