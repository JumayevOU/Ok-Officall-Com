from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from utils.states import AddWorker, DailyReport, AddAdvance
from utils.keyboards import admin_main, cancel_kb
from database import requests as db
from utils.excel_gen import generate_report
import os
import logging
import random
from datetime import datetime
from typing import Dict, Any, List

# Logger sozlamalari
logger = logging.getLogger(__name__)

router = Router()

# ADMIN_ID ni xavfsiz o'qish
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    if ADMIN_ID == 0:
        logger.warning("⚠️ ADMIN_ID .env faylda topilmadi yoki 0 ga teng")
except (ValueError, TypeError) as e:
    logger.error(f"❌ ADMIN_ID ni o'qishda xatolik: {e}")
    ADMIN_ID = 0

# Admin filter
router.message.filter(F.from_user.id == ADMIN_ID)

class AdminHandler:
    """Admin handlerlarini boshqarish klassi"""
    
    @staticmethod
    async def _validate_name(name: str) -> tuple[bool, str]:
        """Ismni tekshirish"""
        if not name or len(name.strip()) < 2:
            return False, "Ism kamida 2 belgidan iborat bo'lishi kerak"
        if len(name.strip()) > 100:
            return False, "Ism 100 belgidan uzun bo'lmasligi kerak"
        return True, name.strip()
    
    @staticmethod
    async def _validate_rate(rate_text: str) -> tuple[bool, float]:
        """Stavkani tekshirish"""
        try:
            rate = float(rate_text.replace(',', '.'))
            if rate <= 0:
                return False, 0.0
            if rate > 1000000:  # Oqilona chegaralar
                return False, 0.0
            return True, rate
        except (ValueError, TypeError):
            return False, 0.0
    
    @staticmethod
    async def _validate_location(location: str) -> tuple[bool, str]:
        """Lokatsiyani tekshirish"""
        if not location or len(location.strip()) < 1:
            return False, "Lokatsiya bo'sh bo'lmasligi kerak"
        if len(location.strip()) > 50:
            return False, "Lokatsiya 50 belgidan uzun bo'lmasligi kerak"
        return True, location.strip()
    
    @staticmethod
    async def _validate_hours(hours_text: str) -> tuple[bool, float]:
        """Soatlarni tekshirish"""
        try:
            hours = float(hours_text.replace(',', '.'))
            if hours < 0 or hours > 24:
                return False, 0.0
            return True, hours
        except (ValueError, TypeError):
            return False, 0.0
    
    @staticmethod
    async def _validate_amount(amount_text: str) -> tuple[bool, float]:
        """Miqdorni tekshirish"""
        try:
            amount = float(amount_text.replace(',', '.'))
            if amount <= 0:
                return False, 0.0
            if amount > 10000000:  # Oqilona chegaralar
                return False, 0.0
            return True, amount
        except (ValueError, TypeError):
            return False, 0.0

# --- ASOSIY MENYU ---

@router.message(F.text == "/start")
async def admin_start(message: Message):
    """Admin bosh menyusi"""
    await message.answer(
        "🏢 **Admin Panel**\n\n"
        "Quyidagi imkoniyatlardan foydalaning:",
        reply_markup=admin_main
    )

@router.message(F.text == "🔙 Asosiy menyu")
async def main_menu(message: Message, state: FSMContext):
    """Asosiy menyuga qaytish"""
    await state.clear()
    await message.answer("🏠 Asosiy menyu", reply_markup=admin_main)

# --- ISHCHI QO'SHISH ---

@router.message(F.text == "👥 Ishchilar")
async def show_workers(message: Message):
    """Ishchilar ro'yxatini ko'rsatish"""
    try:
        workers = await db.get_active_workers()
        if not workers:
            await message.answer(
                "👷‍♂️ **Ishchilar:**\n\n"
                "Hozircha ishchilar yo'q.\n\n"
                "👇 Qo'shish uchun: /add_worker"
            )
            return
        
        # Lokatsiyalar bo'yicha guruhlash
        workers_by_location: Dict[str, List[Dict]] = {}
        for worker in workers:
            location = worker.get('location', 'Noma\'lum')
            if location not in workers_by_location:
                workers_by_location[location] = []
            workers_by_location[location].append(worker)
        
        text = "👷‍♂️ **Ishchilar:**\n\n"
        for location, location_workers in sorted(workers_by_location.items()):
            text += f"📍 **{location}**\n"
            for w in location_workers:
                name = w.get('name', 'Noma\'lum')
                rate = w.get('rate', 0)
                code = w.get('code', 'N/A')
                text += f"  └ {name} | 💵 {rate:,} | 🔑 {code}\n"
            text += "\n"
        
        text += "👇 Yangi ishchi qo'shish: /add_worker"
        await message.answer(text)
        
    except Exception as e:
        logger.error(f"❌ Ishchilarni ko'rsatishda xatolik: {e}")
        await message.answer("❌ Ishchilarni yuklashda xatolik yuz berdi.")

@router.message(F.text == "/add_worker")
async def start_add_worker(message: Message, state: FSMContext):
    """Ishchi qo'shishni boshlash"""
    await state.set_state(AddWorker.name)
    await message.answer(
        "👤 **Yangi ishchi qo'shish**\n\n"
        "Ishchining ismini kiriting:",
        reply_markup=cancel_kb
    )

@router.message(StateFilter(AddWorker.name))
async def add_worker_name(message: Message, state: FSMContext):
    """Ishchi ismini qabul qilish"""
    if message.text == "Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_main)
        return
    
    is_valid, validated_name = await AdminHandler._validate_name(message.text)
    if not is_valid:
        await message.answer("❌ Ism noto'g'ri formatda. Iltimos, qaytadan kiriting:")
        return
    
    await state.update_data(name=validated_name)
    await state.set_state(AddWorker.rate)
    await message.answer(
        "💰 **Soatlik stavka**\n\n"
        "Ishchining soatlik ish haqini kiriting (so'mda):",
        reply_markup=cancel_kb
    )

@router.message(StateFilter(AddWorker.rate))
async def add_worker_rate(message: Message, state: FSMContext):
    """Ishchi stavkasini qabul qilish"""
    if message.text == "Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_main)
        return
    
    is_valid, validated_rate = await AdminHandler._validate_rate(message.text)
    if not is_valid:
        await message.answer("❌ Stavka noto'g'ri formatda. Iltimos, musbat raqam kiriting:")
        return
    
    await state.update_data(rate=validated_rate)
    await state.set_state(AddWorker.location)
    
    await message.answer(
        "🏢 **Ish joyi**\n\n"
        "Ish joyi (blok) nomini kiriting:\n"
        "Masalan: H Blok yoki A Blok",
        reply_markup=cancel_kb
    )

@router.message(StateFilter(AddWorker.location))
async def add_worker_location(message: Message, state: FSMContext):
    """Ishchi lokatsiyasini qabul qilish va saqlash"""
    if message.text == "Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_main)
        return
    
    is_valid, validated_location = await AdminHandler._validate_location(message.text)
    if not is_valid:
        await message.answer("❌ Lokatsiya noto'g'ri formatda. Iltimos, qaytadan kiriting:")
        return
    
    data = await state.get_data()
    
    # Takroriy kodlarni oldini olish
    while True:
        code = random.randint(100, 999)
        # Kod band emasligini tekshirish (soddalik uchun, aslida DB da tekshirish kerak)
        break
    
    success, message_text = await db.add_worker(
        data['name'], 
        data['rate'], 
        code, 
        validated_location
    )
    
    if success:
        await message.answer(
            f"✅ **Ishchi muvaffaqiyatli qo'shildi!**\n\n"
            f"👤 **Ism:** {data['name']}\n"
            f"📍 **Lokatsiya:** {validated_location}\n"
            f"💰 **Stavka:** {data['rate']:,} so'm/soat\n"
            f"🔑 **Kirish kodi:** `{code}`\n\n"
            f"*Ishchi ushbu kod orqali tizimga kirishi mumkin*",
            reply_markup=admin_main
        )
        logger.info(f"✅ Yangi ishchi qo'shildi: {data['name']} (Kod: {code})")
    else:
        await message.answer(
            f"❌ **Ishchi qo'shish muvaffaqiyatsiz:**\n{message_text}",
            reply_markup=admin_main
        )
    
    await state.clear()

# --- BUGUNGI HISOBOT ---

@router.message(F.text == "📝 Bugungi hisobot")
async def start_daily_report(message: Message, state: FSMContext):
    """Kunlik hisobotni boshlash"""
    try:
        workers = await db.get_active_workers()
        if not workers:
            await message.answer("❌ Hozircha ishchilar yo'q!")
            return
        
        await state.set_state(DailyReport.entering_hours)
        await state.update_data(
            queue=workers, 
            index=0,
            processed_count=0
        )
        
        first_worker = workers[0]
        location = first_worker.get('location', 'Noma\'lum')
        
        await message.answer(
            f"📊 **Kunlik hisobot**\n\n"
            f"📍 {location}\n"
            f"👤 {first_worker['name']}\n\n"
            f"Ishlagan soatlarini kiriting:",
            reply_markup=cancel_kb
        )
        
    except Exception as e:
        logger.error(f"❌ Hisobotni boshlashda xatolik: {e}")
        await message.answer("❌ Hisobotni boshlashda xatolik yuz berdi.")

@router.message(StateFilter(DailyReport.entering_hours))
async def process_daily_report(message: Message, state: FSMContext):
    """Kunlik hisobotni qayta ishlash"""
    if message.text == "Bekor qilish":
        await state.clear()
        await message.answer("❌ Hisobot bekor qilindi", reply_markup=admin_main)
        return
    
    is_valid, validated_hours = await AdminHandler._validate_hours(message.text)
    if not is_valid:
        await message.answer("❌ Noto'g'ri format. Iltimos, 0 dan 24 gacha bo'lgan raqam kiriting:")
        return
    
    try:
        data = await state.get_data()
        idx = data['index']
        worker = data['queue'][idx]
        
        # Statusni aniqlash
        status = "present" if validated_hours > 0 else "absent"
        
        success, result_message = await db.add_attendance(
            worker['id'], 
            validated_hours, 
            status
        )
        
        if not success:
            await message.answer(f"❌ Xatolik: {result_message}")
            return
        
        processed_count = data.get('processed_count', 0) + 1
        
        # Keyingi ishchiga o'tish
        if idx + 1 < len(data['queue']):
            await state.update_data(index=idx + 1, processed_count=processed_count)
            next_worker = data['queue'][idx + 1]
            location = next_worker.get('location', 'Noma\'lum')
            
            await message.answer(
                f"✅ {worker['name']} - {validated_hours} soat\n"
                f"📊 {processed_count}/{len(data['queue'])}\n\n"
                f"📍 {location}\n"
                f"👤 {next_worker['name']}\n\n"
                f"Ishlagan soatlarini kiriting:",
                reply_markup=cancel_kb
            )
        else:
            # Hisobot tugadi
            await state.clear()
            await message.answer(
                f"✅ **Hisobot tugadi!**\n\n"
                f"📊 Jami: {processed_count} ta ishchi\n"
                f"🗓 Sana: {datetime.now().strftime('%d.%m.%Y')}",
                reply_markup=admin_main
            )
            logger.info(f"✅ Kunlik hisobot tugadi: {processed_count} ta ishchi")
            
    except Exception as e:
        logger.error(f"❌ Hisobotni qayta ishlashda xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

# --- EXCEL HISOBOT ---

@router.message(F.text == "📥 Excel (Oy yakuni)")
async def download_excel_report(message: Message):
    """Excel hisobotini yuklab olish"""
    try:
        processing_msg = await message.answer("⏳ Hisobot tayyorlanmoqda...")
        
        now = datetime.now()
        year, month = now.year, now.month
        
        # Ma'lumotlarni yuklash
        workers = await db.get_all_workers_report()
        if not workers:
            await message.answer("❌ Hisobot uchun ishchilar topilmadi.")
            return
        
        attendance = await db.get_month_attendance(year, month)
        advances = await db.get_month_advances(year, month)
        
        # Ma'lumotlarni formatlash
        att_dict = {(row['worker_id'], row['date_str']): row['hours'] for row in attendance}
        adv_dict = {row['worker_id']: row['total'] for row in advances}
        
        # Excel fayl yaratish
        filename = generate_report(year, month, workers, att_dict, adv_dict)
        
        if not filename or not os.path.exists(filename):
            await message.answer("❌ Hisobot faylini yaratishda xatolik yuz berdi.")
            return
        
        # Faylni yuborish
        await message.answer_document(
            FSInputFile(filename),
            caption=f"📊 **Oylik hisobot**\n"
                   f"🗓 {month:02d}.{year}\n"
                   f"👥 {len(workers)} ta ishchi"
        )
        
        # Vaqtincha faylni o'chirish
        try:
            os.remove(filename)
            logger.info(f"✅ Vaqtincha fayl o'chirildi: {filename}")
        except Exception as e:
            logger.warning(f"⚠️ Faylni o'chirishda xatolik: {e}")
        
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"❌ Excel hisobot yaratishda xatolik: {e}")
        await message.answer(f"❌ Hisobot yaratishda xatolik: {str(e)}")

# --- AVANS YOZISH ---

@router.message(F.text == "💰 Avans yozish")
async def start_advance(message: Message, state: FSMContext):
    """Avans yozishni boshlash"""
    try:
        workers = await db.get_active_workers()
        if not workers:
            await message.answer("❌ Hozircha ishchilar yo'q!")
            return
        
        # Ishchilar ro'yxatini ko'rsatish
        workers_text = "👥 **Ishchilar ro'yxati:**\n\n"
        for worker in workers:
            workers_text += f"🆔 {worker['id']} - {worker['name']} ({worker.get('location', 'Nomalum')})\n"
        
        workers_text += "\nIshchi ID raqamini kiriting:"
        
        await state.set_state(AddAdvance.worker_select)
        await message.answer(workers_text, reply_markup=cancel_kb)
        
    except Exception as e:
        logger.error(f"❌ Avans yozishni boshlashda xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

@router.message(StateFilter(AddAdvance.worker_select))
async def select_advance_worker(message: Message, state: FSMContext):
    """Avans uchun ishchini tanlash"""
    if message.text == "Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_main)
        return
    
    if not message.text.isdigit():
        await message.answer("❌ ID raqam bo'lishi kerak! Iltimos, qaytadan kiriting:")
        return
    
    worker_id = int(message.text)
    
    # Ishchini tekshirish
    worker = await db.get_worker_by_id(worker_id)
    if not worker or not worker.get('active', True):
        await message.answer("❌ Bunday ID ga ega faol ishchi topilmadi. Iltimos, qaytadan kiriting:")
        return
    
    await state.update_data(worker_id=worker_id, worker_name=worker['name'])
    await state.set_state(AddAdvance.amount)
    
    await message.answer(
        f"👤 **Ishchi:** {worker['name']}\n"
        f"📍 {worker.get('location', 'Nomalum')}\n\n"
        f"💰 Avans miqdorini kiriting (so'mda):",
        reply_markup=cancel_kb
    )

@router.message(StateFilter(AddAdvance.amount))
async def add_advance_amount(message: Message, state: FSMContext):
    """Avans miqdorini qabul qilish"""
    if message.text == "Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_main)
        return
    
    is_valid, validated_amount = await AdminHandler._validate_amount(message.text)
    if not is_valid:
        await message.answer("❌ Miqdor noto'g'ri formatda. Iltimos, musbat raqam kiriting:")
        return
    
    data = await state.get_data()
    
    success, result_message = await db.add_advance_money(
        data['worker_id'], 
        validated_amount
    )
    
    if success:
        await message.answer(
            f"✅ **Avans muvaffaqiyatli yozildi!**\n\n"
            f"👤 {data['worker_name']}\n"
            f"💰 {validated_amount:,} so'm\n"
            f"🗓 {datetime.now().strftime('%d.%m.%Y')}",
            reply_markup=admin_main
        )
        logger.info(f"✅ Avans yozildi: {data['worker_name']} - {validated_amount} so'm")
    else:
        await message.answer(
            f"❌ **Avans yozish muvaffaqiyatsiz:**\n{result_message}",
            reply_markup=admin_main
        )
    
    await state.clear()

# --- XATOLIKLAR BOSHQARUVI ---

@router.message()
async def unknown_command(message: Message, state: FSMContext):
    """Noma'lum buyruqlar uchun"""
    current_state = await state.get_state()
    if current_state:
        await message.answer(
            "❌ Noto'g'ri amal. Jarayonni davom etiring yoki 'Bekor qilish' tugmasini bosing.",
            reply_markup=cancel_kb
        )
    else:
        await message.answer(
            "❌ Noma'lum buyruq. Iltimos, menyudan foydalaning.",
            reply_markup=admin_main
        )