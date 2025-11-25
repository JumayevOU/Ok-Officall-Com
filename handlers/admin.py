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

# --- SOZLAMALAR ---
@router.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(message: Message):
    header = to_bold("BOSHQARUV MARKAZI")
    await message.answer(f"⚙️ {header}\n➖➖➖➖➖➖➖➖➖➖\n<i>Quyidagi amallardan birini tanlang:</i>", reply_markup=settings_kb)

# --- ADD WORKER ---
@router.callback_query(F.data == "set_add")
async def btn_add(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.set_state(AddWorker.name)
    await call.message.answer("✍️ <b>Yangi xodimning to'liq Ism Familiyasini kiriting:</b>\n\n<i>Masalan: Aliyev Vali</i>", reply_markup=cancel_kb)

@router.message(AddWorker.name)
async def add_n(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); await message.answer("Bekor qilindi", reply_markup=admin_main); return
    await state.update_data(name=message.text)
    await state.set_state(AddWorker.rate)
    await message.answer("💸 <b>Xodimning bir soatlik ish haqi qancha?</b>\n\n<i>Faqat raqam kiriting (so'mda). Masalan: 25000</i>", reply_markup=cancel_kb)

@router.message(AddWorker.rate)
async def add_r(message: Message, state: FSMContext):
    try:
        await state.update_data(rate=float(message.text))
        await state.set_state(AddWorker.location)
        await message.answer("📍 <b>Xodim qaysi Blokda ishlaydi?</b>\n\n<i>Masalan: A Blok, H Blok...</i>", reply_markup=cancel_kb)
    except:
        await message.answer("⚠️ <i>Iltimos, faqat raqam yozing!</i>")

@router.message(AddWorker.location)
async def add_l(message: Message, state: FSMContext):
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
        "<i>Bu kodni xodimga bering, u botga kirishi uchun kerak.</i>"
    )
    await message.answer(msg, reply_markup=admin_main)

# --- EDIT WORKER ---
@router.callback_query(F.data == "set_edit")
async def btn_edit(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.set_state(EditWorker.waiting_id)
    await call.message.answer("✏️ <b>Tahrirlash uchun xodimning ID raqamini yozing:</b>\n\n<i>ID raqamni 'Ishchilar' bo'limidan ko'rishingiz mumkin.</i>", reply_markup=cancel_kb)

@router.message(EditWorker.waiting_id)
async def edit_id(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); await message.answer("Bekor", reply_markup=admin_main); return
    if not message.text.isdigit(): await message.answer("⚠️ <i>Faqat raqam yozing!</i>"); return
    await state.update_data(wid=int(message.text))
    await state.set_state(EditWorker.waiting_field)
    await message.answer("Nimani o'zgartiramiz?", reply_markup=edit_options)

@router.callback_query(EditWorker.waiting_field)
async def edit_f(call: CallbackQuery, state: FSMContext):
    fm = {'edit_name': 'name', 'edit_rate': 'rate', 'edit_loc': 'location'}
    await state.update_data(field=fm[call.data])
    await state.set_state(EditWorker.waiting_value)
    msgs = {
        'name': "✍️ <b>Yangi ismni kiriting:</b>",
        'rate': "💸 <b>Yangi narxni kiriting (faqat raqam):</b>",
        'location': "📍 <b>Yangi blok nomini kiriting:</b>"
    }
    await call.message.edit_text(msgs[fm[call.data]])

@router.message(EditWorker.waiting_value)
async def edit_v(message: Message, state: FSMContext):
    data = await state.get_data()
    val = message.text
    if data['field'] == 'rate':
        try: val = float(val)
        except: await message.answer("⚠️ <i>Raqam yozing!</i>"); return
    await db.update_worker_field(data['wid'], data['field'], val)
    await state.clear()
    await message.answer("✅ <b>Ma'lumot muvaffaqiyatli yangilandi!</b>", reply_markup=admin_main)

# --- DELETE WORKER ---
@router.callback_query(F.data == "set_del")
async def btn_del(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await state.set_state(DeleteWorker.waiting_id)
    await call.message.answer("🗑 <b>O'chirish uchun xodimning ID raqamini yozing:</b>", reply_markup=cancel_kb)

@router.message(DeleteWorker.waiting_id)
async def del_confirm(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); await message.answer("Bekor", reply_markup=admin_main); return
    if not message.text.isdigit(): await message.answer("⚠️ <i>ID raqam bo'lishi kerak!</i>"); return
    
    w_id = int(message.text)
    await db.archive_worker_date(w_id)
    await state.clear()
    await message.answer(f"✅ <b>{w_id}-raqamli xodim arxivlandi!</b>\n\n<i>Uning ma'lumotlari joriy oy hisobotida qoladi, keyingi oydan chiqmaydi.</i>", reply_markup=admin_main)

# --- SHOW LIST ---
@router.message(F.text == "👥 Ishchilar")
async def show_list(message: Message):
    workers = await db.get_active_workers()
    head = to_bold("ISHCHILAR RO'YXATI")
    text = f"📋 {head}\n➖➖➖➖➖➖➖➖➖➖\n"
    if not workers: text += "<i>Hozircha ro'yxat bo'sh.</i>"
    else:
        for w in workers:
            loc = w.get('location', 'Umumiy')
            text += f"🆔 <code>{w['id']}</code>  👤 <b>{w['name']}</b>\n📍 <i>{loc}</i>  |  💵 {w['rate']:,}\n───────────────\n"
            
    text += "\n👇 <i>O'zgartirish kiritish uchun 'Sozlamalar' menyusiga kiring.</i>"
    await message.answer(text)

# --- REPORT ---
@router.message(F.text == "📝 Bugungi hisobot")
async def rep_start(message: Message, state: FSMContext):
    w = await db.get_active_workers()
    if not w: await message.answer("⚠️ Ro'yxatda xodimlar yo'q."); return
    await state.set_state(DailyReport.entering_hours)
    await state.update_data(queue=w, index=0)
    
    header = to_bold("DAVOMAT")
    msg = (
        f"📝 {header}\n➖➖➖➖➖➖➖➖\n"
        f"👤 <b>{w[0]['name']}</b>\n"
        f"📍 <i>{w[0]['location']}</i>\n\n"
        "👉 <b>Bugun necha soat ishladi?</b>"
    )
    await message.answer(msg, reply_markup=cancel_kb)

@router.message(DailyReport.entering_hours)
async def rep_proc(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); await message.answer("⏹ Jarayon to'xtatildi", reply_markup=admin_main); return
    try:
        h = float(message.text)
        data = await state.get_data()
        idx = data['index']
        await db.add_attendance(data['queue'][idx]['id'], h, "Keldi" if h > 0 else "Kelmadi")
        
        if idx + 1 < len(data['queue']):
            nw = data['queue'][idx+1]
            await state.update_data(index=idx+1)
            msg = (
                f"👤 <b>{nw['name']}</b>\n"
                f"📍 <i>{nw['location']}</i>\n\n"
                "👉 <b>Necha soat?</b>"
            )
            await message.answer(msg, reply_markup=cancel_kb)
        else:
            await state.clear()
            header = to_bold("YAKUNLANDI")
            await message.answer(f"✅ {header}\n\n<i>Barcha hisobotlar muvaffaqiyatli saqlandi!</i>", reply_markup=admin_main)
    except:
        await message.answer("⚠️ <i>Iltimos, faqat raqam kiriting!</i>")

# --- STATUS ---
@router.message(F.text == "📊 Joriy holat")
async def status(message: Message):
    now = datetime.now()
    w = await db.get_active_workers()
    att = await db.get_month_attendance(now.year, now.month)
    adv = await db.get_month_advances(now.year, now.month)
    
    am = {r['worker_id']: r.get('total', 0) for r in adv}
    tm = {}
    for r in att: tm[r['worker_id']] = tm.get(r['worker_id'], 0) + r['hours']
    
    head = to_bold(f"JORIY HOLAT ({now.strftime('%B')})")
    txt = f"📊 {head}\n➖➖➖➖➖➖➖➖➖➖\n\n"
    tot = 0
    if not w: txt += "<i>Ma'lumot yo'q.</i>"
    
    for wk in w:
        h = tm.get(wk['id'], 0)
        a = am.get(wk['id'], 0)
        f = (h * wk['rate']) - a
        tot += f
        txt += f"👤 <b>{wk['name']}</b>\n⏱ <code>{h} soat</code>  |  💸 Avans: <code>{a:,.0f}</code>\n💰 <b>{f:,.0f} so'm</b>\n───────────────\n"
    
    txt += f"\n💵 𝐉𝐀𝐌𝐈 𝐊𝐀𝐒𝐒𝐀: <code>{tot:,.0f} so'm</code>"
    await message.answer(txt)

# --- EXCEL ---
@router.message(F.text == "📥 Excel (Oy yakuni)")
async def excel(message: Message):
    msg = await message.answer("⏳ <i>Hisobot tayyorlanmoqda...</i>")
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
        await message.answer_document(FSInputFile(fname), caption=f"📊 {caption}")
        os.remove(fname)
    except Exception as e:
        await msg.delete()
        await message.answer(f"❌ <b>Xatolik yuz berdi:</b>\n<code>{str(e)}</code>")

# --- AVANS (ADMIN: QIDIRUV BILAN) ---
@router.message(F.text == "💰 Avans yozish")
async def av_s(message: Message, state: FSMContext):
    await state.set_state(AddAdvance.worker_select)
    await message.answer("🔎 <b>Xodimni topish uchun uning ID raqamini yoki Ismini yozing:</b>", reply_markup=cancel_kb)

@router.message(AddAdvance.worker_select)
async def av_w(message: Message, state: FSMContext):
    if message.text == "Bekor qilish": await state.clear(); return
    
    text = message.text.strip()
    worker_id = None
    
    # 1. Agar raqam bo'lsa, ID bo'yicha tekshiramiz
    if text.isdigit():
        worker_id = int(text)
    
    # 2. Agar matn bo'lsa, Ism bo'yicha qidiramiz
    else:
        results = await db.search_worker_by_name(text)
        if not results:
            await message.answer("🚫 <b>Xodim topilmadi.</b>\n<i>Iltimos, ID raqamni yoki to'g'ri ismni yozing.</i>")
            return
        elif len(results) == 1:
            worker_id = results[0]['id']
            await message.answer(f"✅ <b>Topildi:</b> {results[0]['name']}")
        else:
            # Ko'p odam chiqsa
            msg = "⚠️ <b>Bir nechta xodim topildi. Iltimos, ID raqamini yozing:</b>\n\n"
            for r in results:
                msg += f"🆔 <code>{r['id']}</code> - {r['name']} ({r['location']})\n"
            await message.answer(msg)
            return # State o'zgarmaydi, ID kiritishni kutadi

    if worker_id:
        await state.update_data(wid=worker_id)
        await state.set_state(AddAdvance.amount)
        await message.answer("💸 <b>Qancha avans bermoqchisiz?</b>\n\n<i>Summani so'mda yozing (masalan: 500000)</i>", reply_markup=cancel_kb)

@router.message(AddAdvance.amount)
async def av_a(message: Message, state: FSMContext):
    try:
        val = float(message.text)
        data = await state.get_data()
        await db.add_advance_money(data['wid'], val)
        
        # Ishchiga xabar yuborish
        tg_id = await db.get_worker_tg_id(data['wid'])
        if tg_id:
            try:
                head_w = to_bold("AVANS BERILDI")
                await message.bot.send_message(tg_id, f"✅ {head_w}\n\n💰 <b>Sizga {val:,.0f} so'm avans yozildi.</b>")
            except: pass # Agar botni bloklagan bo'lsa
            
        await state.clear()
        await message.answer("✅ <b>Avans muvaffaqiyatli yozildi!</b>", reply_markup=admin_main)
    except:
        await message.answer("⚠️ <i>Iltimos, faqat raqam yozing!</i>")

# --- CALLBACKS (AVANS TASDIQLASH BILAN) ---
@router.callback_query(F.data.startswith("app_adv_"))
async def app_av(call: CallbackQuery):
    parts = call.data.split("_")
    wid = int(parts[2])
    amount = float(parts[3])
    await db.add_advance_money(wid, amount)
    
    # Xabar matnini o'zgartirish
    header = to_bold("AVANS TASDIQLANDI")
    await call.message.edit_text(f"✅ {header}\n\n🆔 Xodim ID: {wid}\n💰 Summa: {amount:,.0f} so'm")
    
    # Ishchiga xabar yuborish
    tg_id = await db.get_worker_tg_id(wid)
    if tg_id:
        try:
            head_w = to_bold("AVANS QABUL QILINDI")
            await call.bot.send_message(tg_id, f"✅ {head_w}\n\n💰 <b>Siz so'ragan {amount:,.0f} so'm avans tasdiqlandi va hisobingizga yozildi.</b>")
        except: pass

@router.callback_query(F.data.startswith("rej_adv_"))
async def rej_av(call: CallbackQuery):
    parts = call.data.split("_")
    wid = int(parts[2])
    
    await call.message.edit_text("🚫 <b>Avans so'rovi rad etildi.</b>")
    
    # Ishchiga xabar yuborish
    tg_id = await db.get_worker_tg_id(wid)
    if tg_id:
        try:
            head_w = to_bold("AVANS RAD ETILDI")
            await call.bot.send_message(tg_id, f"🚫 {head_w}\n\n<i>Sizning avans so'rovingiz rad etildi.</i>")
        except: pass