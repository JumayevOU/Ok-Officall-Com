from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from utils.keyboards import admin_main, worker_main
from utils.states import WorkerLogin
from database import requests as db
import os

router = Router()
try: ADMIN_ID = int(os.getenv("ADMIN_ID"))
except: ADMIN_ID = 0

def to_bold(text):
    trans = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳")
    return text.translate(trans)

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        header = to_bold("XO'JAYIN PANELI")
        await message.answer(f"👋 <b>Xush kelibsiz!</b>\n\n👑 {header}\n<i>Boshqaruv paneliga marhamat.</i>", reply_markup=admin_main)
    else:
        header = to_bold("TIZIMGA KIRISH")
        msg = (
            f"🔐 {header}\n"
            "➖➖➖➖➖➖➖➖➖➖\n\n"
            "👋 Assalomu alaykum!\n"
            "🆔 Iltimos, <b>ID KOD</b>ingizni kiriting:"
        )
        await message.answer(msg)
        await state.set_state(WorkerLogin.waiting_code)

@router.message(WorkerLogin.waiting_code)
async def process_login(message: Message, state: FSMContext):
    if not message.text.isdigit(): await message.answer("⚠️ <i>Faqat raqam yozing!</i>"); return
    
    success, msg = await db.verify_login(message.text, message.from_user.id)
    if success:
        header = to_bold("MUVAFFAQIYATLI")
        await message.answer(f"✅ {header}\n\nXush kelibsiz, <b>{msg}</b>!", reply_markup=worker_main)
        await state.clear()
    else:
        await message.answer(f"🚫 <b>{msg}</b>\n<i>Qaytadan urinib ko'ring:</i>")