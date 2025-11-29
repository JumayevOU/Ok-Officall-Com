from aiogram import Router, F
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.states import AddWorker, DailyReport, AddAdvance, DeleteWorker, EditWorker, SetLocation
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

# --- GLOBAL CANCEL ---
@router.message(F.text == "Bekor qilish")
async def global_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ <b>Bekor qilindi.</b>", reply_markup=admin_main)

# --- SETTINGS MENU ---
@router.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(message: Message):
    header = to_bold("BOSHQARUV MARKAZI")
    await message.answer(f"⚙️ {header}\n➖➖➖➖➖➖➖➖➖➖\n<i>Quyidagilardan birini tanlang:</i>", reply_markup=settings_kb)

# --- ADD WORKER ---
@router.callback_query(F.data == "set_add")
async def btn_add(call: CallbackQuery, state: FSMContext):
    await call.message.delete(); await state.set_state(AddWorker.name)
    await call.message.answer("✍️ <b>Yangi xodimning to'liq Ism Familiyasini kiriting:</b>", reply_markup=cancel_kb)

@router.message(AddWorker.name)
async def add_n(message: Message, state: FSMContext):
    await state.update_data(name=message.text); await state.set_state(AddWorker.rate)
    await message.answer("💸 <b>Soatlik ish haqi qancha? (So'mda)</b>", reply_markup=cancel_kb)

@router.message(AddWorker.rate)
async def add_r(message: Message, state: FSMContext):
    try: await state.update_data(rate=float(message.text)); await state.set_state(AddWorker.location); await message.answer("📍 <b>Xodim qaysi Blokda ishlaydi?</b>", reply_markup=cancel_kb)
    except: await message.answer("⚠️ Raqam yozing!")

@router.message(AddWorker.location)
async def add_l(message: Message, state: FSMContext):
    d = await state.get_data(); code = random.randint(100, 999)
    await db.add_worker(d['name'], d['rate'], code, message.text); await state.clear()
    await message.answer(f"✅ <b>Qo'shildi!</b>\n👤 {d['name']}\n🔑 Kod: <code>{code}</code>", reply_markup=admin_main)

# --- LOCATION ---
@router.callback_query(F.data == "set_gps")
async def btn_gps(call: CallbackQuery, state: FSMContext):
    await call.message.delete(); await state.set_state(SetLocation.waiting_loc)
    await call.message.answer("📍 <b>Obyektning lokatsiyasini yuboring:</b>\n<i>(Pastdagi 📎 -> Location ni bosing)</i>", reply_markup=cancel_kb)

@router.message(SetLocation.waiting_loc, F.location)
async def gps_save(message: Message, state: FSMContext):
    await db.set_work_location(message.location.latitude, message.location.longitude); await state.clear()
    await message.answer("✅ <b>Lokatsiya saqlandi!</b>", reply_markup=admin_main)

# --- EDIT WORKER ---
@router.callback_query(F.data == "set_edit")
async def btn_edit(call: CallbackQuery, state: FSMContext):
    await call.message.delete(); await state.set_state(EditWorker.waiting_id)
    await call.message.answer("✏️ <b>ID raqamni yozing:</b>", reply_markup=cancel_kb)

@router.message(EditWorker.waiting_id)
async def edit_id(message: Message, state: FSMContext):
    if not message.text.isdigit(): await message.answer("ID kerak"); return
    await state.update_data(wid=int(message.text)); await state.set_state(EditWorker.waiting_field)
    await message.answer("Nimani o'zgartiramiz?", reply_markup=edit_options)

@router.callback_query(EditWorker.waiting_field)
async def edit_f(call: CallbackQuery, state: FSMContext):
    fm = {'edit_name': 'name', 'edit_rate': 'rate', 'edit_loc': 'location'}
    await state.update_data(field=fm[call.data]); await state.set_state(EditWorker.waiting_value)
    await call.message.edit_text("✍️ <b>Yangi qiymatni yozing:</b>")

@router.message(EditWorker.waiting_value)
async def edit_v(message: Message, state: FSMContext):
    d = await state.get_data(); val = message.text
    if d['field']=='rate':
        try: val=float(val)
        except: await message.answer("Raqam kerak"); return
    await db.update_worker_field(d['wid'], d['field'], val); await state.clear()
    await message.answer("✅ <b>O'zgardi!</b>", reply_markup=admin_main)

# --- DELETE WORKER ---
@router.callback_query(F.data == "set_del")
async def btn_del(call: CallbackQuery, state: FSMContext):
    await call.message.delete(); await state.set_state(DeleteWorker.waiting_id)
    await call.message.answer("🗑 <b>ID raqamni yozing:</b>", reply_markup=cancel_kb)

@router.message(DeleteWorker.waiting_id)
async def del_confirm(message: Message, state: FSMContext):
    if not message.text.isdigit(): await message.answer("ID kerak"); return
    await db.archive_worker_date(int(message.text)); await state.clear()
    await message.answer("✅ <b>Arxivlandi!</b>", reply_markup=admin_main)

# --- REPORT (DAVOMAT) ---
@router.message(F.text == "📝 Bugungi hisobot")
async def rep_start(message: Message, state: FSMContext):
    w = await db.get_active_workers()
    if not w: await message.answer("Ishchi yo'q"); return
    await state.set_state(DailyReport.entering_hours); await state.update_data(queue=w, index=0)
    await message.answer(f"👤 <b>{w[0]['name']}</b>\nNecha soat?", reply_markup=cancel_kb)

@router.message(DailyReport.entering_hours)
async def rep_proc(message: Message, state: FSMContext):
    try:
        h = float(message.text); d = await state.get_data(); idx = d['index']
        await db.add_attendance_manual(d['queue'][idx]['id'], h, "Keldi" if h>0 else "Kelmadi")
        if idx+1 < len(d['queue']):
            nw = d['queue'][idx+1]; await state.update_data(index=idx+1)
            await message.answer(f"👤 <b>{nw['name']}</b>\nNecha soat?", reply_markup=cancel_kb)
        else: await state.clear(); await message.answer("✅ <b>Yakunlandi!</b>", reply_markup=admin_main)
    except: await message.answer("Raqam yozing")

# --- AVANS (SEARCH & SELECT) ---
@router.message(F.text == "💰 Avans yozish")
async def av_s(message: Message, state: FSMContext):
    await state.set_state(AddAdvance.worker_select)
    await message.answer("🔎 <b>ID raqam yoki Ismni yozing:</b>", reply_markup=cancel_kb)

@router.message(AddAdvance.worker_select)
async def av_w(message: Message, state: FSMContext):
    txt = message.text.strip(); wid = None
    if txt.isdigit(): wid = int(txt)
    else:
        res = await db.search_worker_by_name(txt)
        if not res: await message.answer("🚫 Topilmadi"); return
        elif len(res)==1: wid = res[0]['id']; await message.answer(f"✅ Topildi: {res[0]['name']}")
        else:
            msg = "⚠️ <b>Bir nechta topildi, ID yozing:</b>\n"
            for r in res: msg += f"🆔 {r['id']} - {r['name']}\n"
            await message.answer(msg); return
            
    if wid:
        await state.update_data(wid=wid); await state.set_state(AddAdvance.amount)
        await message.answer("💸 <b>Summa:</b>", reply_markup=cancel_kb)

@router.message(AddAdvance.amount)
async def av_a(message: Message, state: FSMContext):
    try:
        val = float(message.text); d = await state.get_data()
        await db.add_advance_money(d['wid'], val)
        tg = await db.get_worker_tg_id(d['wid'])
        if tg:
            try: await message.bot.send_message(tg, f"✅ <b>Sizga {val:,.0f} so'm avans yozildi.</b>")
            except: pass
        await state.clear(); await message.answer("✅ Yozildi", reply_markup=admin_main)
    except: await message.answer("Xato summa")

# --- LIST & STATUS ---
@router.message(F.text == "👥 Ishchilar")
async def list_w(m: Message):
    w = await db.get_active_workers()
    head = to_bold("ISHCHILAR")
    txt = f"📋 {head}\n➖➖➖➖➖➖➖➖➖➖\n"
    for k in w: txt += f"🆔 <code>{k['id']}</code> | <b>{k['name']}</b>\n📍 {k.get('location','-')} | 💵 {k['rate']:,}\n───────────────\n"
    await m.answer(txt)

@router.message(F.text == "📊 Joriy holat")
async def status(m: Message):
    now = datetime.now()
    w, att, adv = await db.get_active_workers(), await db.get_month_attendance(now.year, now.month), await db.get_month_advances(now.year, now.month)
    am = {r['worker_id']: r.get('total', 0) for r in adv}
    tm = {}
    for r in att: tm[r['worker_id']] = tm.get(r['worker_id'], 0) + r['hours']
    
    head = to_bold(f"HOLAT ({now.strftime('%B')})")
    txt = f"📊 {head}\n➖➖➖➖➖➖➖➖➖➖\n"; tot = 0
    for wk in w:
        h = tm.get(wk['id'], 0); a = am.get(wk['id'], 0); f = (h * wk['rate']) - a; tot += f
        txt += f"👤 <b>{wk['name']}</b>\n⏱ {h} soat | 💰 <b>{f:,.0f}</b>\n───────────────\n"
    txt += f"\n💵 JAMI: <b>{tot:,.0f} so'm</b>"
    await m.answer(txt)

# --- EXCEL ---
@router.message(F.text == "📥 Excel (Oy yakuni)")
async def excel(m: Message):
    msg = await m.answer("⏳ <i>Tayyorlanmoqda...</i>")
    now = datetime.now()
    try:
        w, atd, add = await db.get_report_data_full(now.year, now.month)
        fname = generate_report(now.year, now.month, w, atd, add)
        await msg.delete()
        await m.answer_document(FSInputFile(fname), caption=f"📊 {to_bold(now.strftime('%B'))}")
        os.remove(fname)
    except Exception as e:
        await msg.delete(); await m.answer(f"❌ Xato: {e}")

# --- CALLBACKS (AVANS) ---
@router.callback_query(F.data.startswith("app_adv_"))
async def app_av(call: CallbackQuery):
    p = call.data.split("_"); wid = int(p[2]); amt = float(p[3])
    await db.add_advance_money(wid, amt)
    await call.message.edit_text(f"✅ <b>Tasdiqlandi!</b>\n💰 {amt:,.0f}")
    tg = await db.get_worker_tg_id(wid)
    if tg:
        try: await call.bot.send_message(tg, f"✅ <b>Avansingiz tasdiqlandi: {amt:,.0f} so'm</b>")
        except: pass

@router.callback_query(F.data.startswith("rej_adv_"))
async def rej_av(call: CallbackQuery):
    p = call.data.split("_"); wid = int(p[2])
    await call.message.edit_text("🚫 <b>Rad etildi.</b>")
    tg = await db.get_worker_tg_id(wid)
    if tg:
        try: await call.bot.send_message(tg, "🚫 <b>Avans so'rovingiz rad etildi.</b>")
        except: pass