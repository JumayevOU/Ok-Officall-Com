from aiogram import Router, F
from aiogram.types import Message
from utils.keyboards import worker_main, cancel_kb, approval_kb
from utils.states import RequestAdvance
from database import requests as db
from aiogram.fsm.context import FSMContext
import os
from datetime import datetime

router = Router()
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
except:
    ADMIN_ID = 0

def to_bold(text):
    trans = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳"
    )
    return text.translate(trans)

@router.message(F.text == "💰 Mening hisobim")
async def my_stats(message: Message):
    stats = await db.get_worker_stats(message.from_user.id)
    if not stats: await message.answer("⚠️ <i>Ma'lumot topilmadi.</i>"); return
    
    salary = stats['hours'] * stats['rate']
    final = salary - stats['advance']
    now = datetime.now()
    
    header = to_bold("SHAXSIY HISOB")
    text = (
        f"🧾 {header}\n"
        f"🗓 <i>{now.strftime('%B %Y')}</i>\n"
        "➖➖➖➖➖➖➖➖➖➖\n\n"
        f"👤 <b>{stats['name']}</b>\n"
        f"💎 Tarif: <code>{stats['rate']:,} so'm/soat</code>\n\n"
        f"⏱ Ishlangan vaqt: <b>{stats['hours']} soat</b>\n"
        f"💵 Hisoblangan: <b>{salary:,.0f} so'm</b>\n"
        f"💸 Avanslar: <b>-{stats['advance']:,.0f} so'm</b>\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        f"💰 𝐐𝐎'𝐋𝐆𝐀 𝐓𝐄𝐆𝐀𝐃𝐈:\n"
        f"👉 <b>{final:,.0f} SO'M</b>"
    )
    await message.answer(text, reply_markup=worker_main)

@router.message(F.text == "💸 Avans so'rash")
async def req_adv_start(message: Message, state: FSMContext):
    await state.set_state(RequestAdvance.amount)
    header = to_bold("AVANS SO'RASH")
    await message.answer(f"💸 {header}\n\nQancha summa kerak? (So'mda):", reply_markup=cancel_kb)

@router.message(RequestAdvance.amount)
async def req_adv_send(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); await message.answer("Bekor", reply_markup=worker_main); return
    try:
        amount = float(message.text)
        conn = await db.get_db()
        w_row = await conn.fetchrow("SELECT id, name FROM workers WHERE telegram_id=$1", message.from_user.id)
        await conn.close()
        
        if w_row:
            header = to_bold("YANGI AVANS SO'ROVI")
            admin_msg = (
                f"🔔 {header}\n\n"
                f"👤 Xodim: <b>{w_row['name']}</b>\n"
                f"💰 So'ralgan summa: <b>{amount:,.0f} so'm</b>\n\n"
                "<i>Tasdiqlaysizmi?</i>"
            )
            await message.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=approval_kb(w_row['id'], amount))
            await message.answer("✅ <b>Adminga yuborildi!</b>\n<i>Javobni kuting.</i>", reply_markup=worker_main)
        else:
            await message.answer("⚠️ Profil topilmadi.")
        await state.clear()
    except:
        await message.answer("⚠️ Faqat raqam yozing!")