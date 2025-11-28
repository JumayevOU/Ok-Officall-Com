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
        head = to_bold("XO'JAYIN PANELI")
        await message.answer(f"👑 {head}\nXush kelibsiz!", reply_markup=admin_main)
    else:
        head = to_bold("TIZIMGA KIRISH")
        await message.answer(f"🔐 {head}\n🆔 <b>ID KODni yozing:</b>")
        await state.set_state(WorkerLogin.waiting_code)

@router.message(WorkerLogin.waiting_code)
async def login(message: Message, state: FSMContext):
    if not message.text.isdigit(): return
    suc, msg = await db.verify_login(message.text, message.from_user.id)
    if suc:
        head = to_bold("MUVAFFAQIYATLI")
        await message.answer(f"✅ {head}\nSalom, <b>{msg}</b>!", reply_markup=worker_main); await state.clear()
    else: await message.answer(msg)