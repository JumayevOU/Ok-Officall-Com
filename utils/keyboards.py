from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- ADMIN KEYBOARDS ---
admin_main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Bugungi hisobot"), KeyboardButton(text="📊 Joriy holat")],
        [KeyboardButton(text="👥 Ishchilar"), KeyboardButton(text="💰 Avans yozish")],
        [KeyboardButton(text="📥 Excel (Oy yakuni)"), KeyboardButton(text="⚙️ Sozlamalar")]
    ], resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Bekor qilish")]], 
    resize_keyboard=True
)

# --- ISHCHI KEYBOARDS ---
worker_main = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="💰 Mening hisobim")]], 
    resize_keyboard=True
)