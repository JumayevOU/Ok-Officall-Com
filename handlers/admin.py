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
try: ADMIN_ID = int(os.getenv("ADMIN_ID"))
except: ADMIN_ID = 0
router.message.filter(F.from_user.id == ADMIN_ID)

def to_bold(text):
    trans = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳")
    return text.translate(trans)

# SOZLAMALAR
@router.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(message: Message):
    header = to_bold("BOSHQARUV MARKAZI")
    await message.answer(f"⚙️ {header}\n➖➖➖➖➖➖➖➖➖➖\n<i>Tanlang:</i>", reply_markup=settings_kb)

# ADD
@router.callback_query(F.data == "set_add")
async def btn_add(call: CallbackQuery, state: FSMContext):
    await call.message.delete(); await state.set_state(AddWorker.name)
    await call.message.answer("✍️ <b>Yangi ism:</b>", reply_markup=cancel_kb)

@router.message(AddWorker.name)
async def add_n(m: Message, s: FSMContext):
    if m.text=="Bekor qilish": await s.clear(); await m.answer("Bekor", reply_markup=admin_main); return
    await s.update_data(name=m.text); await s.set_state(AddWorker.rate)
    await m.answer("💸 <b>Soatlik narx:</b>", reply_markup=cancel_kb)

@router.message(AddWorker.rate)
async def add_r(m: Message, s: FSMContext):
    try: await s.update_data(rate=float(m.text)); await s.set_state(AddWorker.location); await m.answer("📍 <b>Blok nomi:</b>", reply_markup=cancel_kb)
    except: await m.answer("Raqam yozing")

@router.message(AddWorker.location)
async def add_l(m: Message, s: FSMContext):
    if m.text=="Bekor qilish": await s.clear(); return
    d = await s.get_data(); code = random.randint(100, 999)
    await db.add_worker(d['name'], d['rate'], code, m.text); await s.clear()
    await m.answer(f"✅ <b>Qo'shildi!</b>\n👤 {d['name']}\n🔑 Kod: <code>{code}</code>", reply_markup=admin_main)

# EDIT
@router.callback_query(F.data == "set_edit")
async def btn_edit(call: CallbackQuery, state: FSMContext):
    await call.message.delete(); await state.set_state(EditWorker.waiting_id)
    await call.message.answer("✏️ <b>ID raqamni yozing:</b>", reply_markup=cancel_kb)

@router.message(EditWorker.waiting_id)
async def edit_id(m: Message, s: FSMContext):
    if m.text=="Bekor qilish": await s.clear(); await m.answer("Bekor", reply_markup=admin_main); return
    if not m.text.isdigit(): await m.answer("ID kerak"); return
    await s.update_data(wid=int(m.text)); await s.set_state(EditWorker.waiting_field)
    await m.answer("Nimani o'zgartiramiz?", reply_markup=edit_options)

@router.callback_query(EditWorker.waiting_field)
async def edit_f(call: CallbackQuery, s: FSMContext):
    fm = {'edit_name': 'name', 'edit_rate': 'rate', 'edit_loc': 'location'}
    await s.update_data(field=fm[call.data]); await s.set_state(EditWorker.waiting_value)
    await call.message.edit_text("✍️ <b>Yangi qiymatni yozing:</b>")

@router.message(EditWorker.waiting_value)
async def edit_v(m: Message, s: FSMContext):
    d = await s.get_data(); val = m.text
    if d['field']=='rate':
        try: val=float(val)
        except: await m.answer("Raqam kerak"); return
    await db.update_worker_field(d['wid'], d['field'], val); await s.clear()
    await m.answer("✅ <b>O'zgardi!</b>", reply_markup=admin_main)

# DELETE
@router.callback_query(F.data == "set_del")
async def btn_del(call: CallbackQuery, state: FSMContext):
    await call.message.delete(); await state.set_state(DeleteWorker.waiting_id)
    await call.message.answer("🗑 <b>O'chirish uchun ID:</b>", reply_markup=cancel_kb)

@router.message(DeleteWorker.waiting_id)
async def del_confirm(m: Message, s: FSMContext):
    if m.text=="Bekor qilish": await s.clear(); await m.answer("Bekor", reply_markup=admin_main); return
    if not m.text.isdigit(): await m.answer("ID kerak"); return
    await db.archive_worker_date(int(m.text)); await s.clear()
    await m.answer("✅ <b>Arxivlandi!</b>", reply_markup=admin_main)

# LIST
@router.message(F.text == "👥 Ishchilar")
async def show_list(m: Message):
    workers = await db.get_active_workers()
    head = to_bold("ISHCHILAR")
    text = f"📋 {head}\n➖➖➖➖➖➖➖➖➖➖\n"
    if not workers: text+="Bo'sh"
    else:
        for w in workers:
            text += f"🆔 <code>{w['id']}</code> | <b>{w['name']}</b>\n📍 {w.get('location','-')} | 💵 {w['rate']:,}\n───────────────\n"
    await m.answer(text)

# REPORT
@router.message(F.text == "📝 Bugungi hisobot")
async def rep_start(m: Message, s: FSMContext):
    w = await db.get_active_workers()
    if not w: await m.answer("Ishchi yo'q"); return
    await s.set_state(DailyReport.entering_hours); await s.update_data(queue=w, index=0)
    await m.answer(f"👤 <b>{w[0]['name']}</b>\nNecha soat?", reply_markup=cancel_kb)

@router.message(DailyReport.entering_hours)
async def rep_proc(m: Message, s: FSMContext):
    if m.text=="Bekor qilish": await s.clear(); await m.answer("To'xtadi", reply_markup=admin_main); return
    try:
        h = float(m.text); d = await s.get_data(); idx = d['index']
        await db.add_attendance(d['queue'][idx]['id'], h, "Keldi" if h>0 else "Kelmadi")
        if idx+1 < len(d['queue']):
            nw = d['queue'][idx+1]; await s.update_data(index=idx+1)
            await m.answer(f"👤 <b>{nw['name']}</b>\nNecha soat?", reply_markup=cancel_kb)
        else: await s.clear(); await m.answer("✅ <b>Yakunlandi!</b>", reply_markup=admin_main)
    except: await m.answer("Raqam yozing")

# STATUS
@router.message(F.text == "📊 Joriy holat")
async def status(m: Message):
    now = datetime.now(); w = await db.get_active_workers()
    att = await db.get_month_attendance(now.year, now.month); adv = await db.get_month_advances(now.year, now.month)
    am = {r['worker_id']: r.get('total', 0) for r in adv}
    tm = {}; tot = 0
    for r in att: tm[r['worker_id']] = tm.get(r['worker_id'], 0) + r['hours']
    
    head = to_bold(f"HOLAT ({now.strftime('%B')})")
    txt = f"📊 {head}\n➖➖➖➖➖➖➖➖➖➖\n"
    for wk in w:
        h = tm.get(wk['id'], 0); a = am.get(wk['id'], 0); f = (h*wk['rate']) - a; tot += f
        txt += f"👤 <b>{wk['name']}</b>\n⏱ {h} soat | 💰 <b>{f:,.0f}</b>\n───────────────\n"
    txt += f"\n💵 JAMI: <b>{tot:,.0f} so'm</b>"
    await m.answer(txt)

# EXCEL (FIXED)
@router.message(F.text == "📥 Excel (Oy yakuni)")
async def excel(m: Message):
    msg = await m.answer("⏳ <i>Tayyorlanmoqda...</i>")
    now = datetime.now()
    try:
        w = await db.get_workers_for_report(now.year, now.month)
        att = await db.get_month_attendance(now.year, now.month)
        adv = await db.get_month_advances(now.year, now.month)
        atd = {(r['worker_id'], r['date_str']): r['hours'] for r in att}
        add = {r['worker_id']: r['total'] for r in adv}
        
        fname = generate_report(now.year, now.month, w, atd, add)
        await msg.delete()
        caption = to_bold(f"{now.strftime('%B')} OYI HISOBOTI")
        await m.answer_document(FSInputFile(fname), caption=f"📊 {caption}")
        os.remove(fname)
    except Exception as e:
        await msg.delete()
        # Xatolikni xavfsiz chiqarish
        await m.answer(f"❌ Xatolik: {str(e)}")

# AVANS
@router.message(F.text == "💰 Avans yozish")
async def av_s(m: Message, s: FSMContext):
    await s.set_state(AddAdvance.worker_select); await m.answer("🆔 <b>ID raqam:</b>", reply_markup=cancel_kb)

@router.message(AddAdvance.worker_select)
async def av_w(m: Message, s: FSMContext):
    if m.text=="Bekor qilish": await s.clear(); return
    if not m.text.isdigit(): await m.answer("ID kerak"); return
    await s.update_data(wid=int(m.text)); await s.set_state(AddAdvance.amount); await m.answer("💸 <b>Summa:</b>", reply_markup=cancel_kb)

@router.message(AddAdvance.amount)
async def av_a(m: Message, s: FSMContext):
    try: await db.add_advance_money((await s.get_data())['wid'], float(m.text)); await s.clear(); await m.answer("✅ Yozildi", reply_markup=admin_main)
    except: await m.answer("Xato")

@router.callback_query(F.data.startswith("app_adv_"))
async def app_av(c: CallbackQuery):
    p = c.data.split("_"); await db.add_advance_money(int(p[2]), float(p[3]))
    await c.message.edit_text(f"✅ <b>Tasdiqlandi!</b>\n💰 {float(p[3]):,.0f}")

@router.callback_query(F.data.startswith("rej_adv_"))
async def rej_av(c: CallbackQuery):
    await c.message.edit_text("🚫 <b>Rad etildi.</b>")