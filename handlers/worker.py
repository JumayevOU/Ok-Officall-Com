from aiogram import Router, F
from aiogram.types import Message
from utils.keyboards import worker_main, cancel_kb, approval_kb
from utils.states import RequestAdvance
from database import requests as db
from aiogram.fsm.context import FSMContext
import os
from datetime import datetime

router = Router()
try: ADMIN_ID = int(os.getenv("ADMIN_ID"))
except: ADMIN_ID = 0

def to_bold(text):
    trans = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳")
    return text.translate(trans)

@router.message(F.text == "💰 Mening hisobim")
async def my_stats(message: Message):
    stats = await db.get_worker_stats(message.from_user.id)
    if not stats: await message.answer("⚠️ Ma'lumot yo'q"); return
    
    sal = stats['hours'] * stats['rate']; fin = sal - stats['advance']
    head = to_bold("SHAXSIY HISOB")
    text = (
        f"🧾 {head}\n🗓 <i>{datetime.now().strftime('%B %Y')}</i>\n➖➖➖➖➖➖➖➖➖➖\n"
        f"👤 <b>{stats['name']}</b>\n⏱ {stats['hours']} soat | 💸 -{stats['advance']:,.0f}\n"
        f"💰 <b>Qo'lga: {fin:,.0f} so'm</b>"
    )
    await message.answer(text, reply_markup=worker_main)

@router.message(F.text == "💸 Avans so'rash")
async def req_s(m: Message, s: FSMContext):
    await s.set_state(RequestAdvance.amount); await m.answer("💸 <b>Summa:</b>", reply_markup=cancel_kb)

@router.message(RequestAdvance.amount)
async def req_d(m: Message, s: FSMContext):
    if m.text=="Bekor qilish": await s.clear(); await m.answer("Bekor", reply_markup=worker_main); return
    try:
        amt = float(m.text)
        conn = await db.get_db()
        row = await conn.fetchrow("SELECT id, name FROM workers WHERE telegram_id=$1", m.from_user.id)
        await conn.close()
        if row:
            head = to_bold("AVANS SO'ROVI")
            txt = f"🔔 {head}\n👤 {row['name']}\n💰 {amt:,.0f}"
            await m.bot.send_message(ADMIN_ID, txt, reply_markup=approval_kb(row['id'], amt))
            await m.answer("✅ <b>Yuborildi!</b>", reply_markup=worker_main)
        else: await m.answer("Xato")
        await s.clear()
    except: await m.answer("Raqam yozing")