from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

admin_main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Bugungi hisobot"), KeyboardButton(text="📊 Joriy holat")],
        [KeyboardButton(text="👥 Ishchilar"), KeyboardButton(text="💰 Avans yozish")],
        [KeyboardButton(text="📥 Excel (Oy yakuni)"), KeyboardButton(text="⚙️ Sozlamalar")]
    ], 
    resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Bekor qilish")]], 
    resize_keyboard=True
)

worker_main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Mening hisobim")],
        [KeyboardButton(text="📞 Bog'lanish"), KeyboardButton(text="ℹ️ Yordam")]
    ], 
    resize_keyboard=True
)

start_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔑 Kirish kodi")],
        [KeyboardButton(text="📞 Bog'lanish"), KeyboardButton(text="ℹ️ Yordam")]
    ], 
    resize_keyboard=True,
    one_time_keyboard=True
)