from aiogram import Router, F
from aiogram.types import Message
from utils.keyboards import worker_main
from database import requests as db

router = Router()

@router.message(F.text == "💰 Mening hisobim")
async def my_stats(message: Message):
    stats = await db.get_worker_stats(message.from_user.id)
    if not stats:
        await message.answer("⚠️ Sizning hisobingizda ma'lumot topilmadi.\n(Balki Admin hali davomat qilmagandir)")
        return
    
    salary = stats['hours'] * stats['rate']
    final = salary - stats['advance']
    
    text = (
        f"👋 Assalomu alaykum, **{stats['name']}**!\n"
        f"📅 Shu oygi hisobingiz:\n\n"
        f"⏳ Ishlagan vaqtingiz: **{stats['hours']} soat**\n"
        f"💸 Olgan avanslaringiz: **{stats['advance']:,.0f} so'm**\n"
        f"💵 Jami hisoblangan: **{salary:,.0f} so'm**\n"
        f"──────────────────\n"
        f"💰 **QO'LGA TEGADI: {final:,.0f} so'm**"
    )
    await message.answer(text, reply_markup=worker_main)