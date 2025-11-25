from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

admin_main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Bugungi hisobot"), KeyboardButton(text="📊 Joriy holat")],
        [KeyboardButton(text="👥 Ishchilar"), KeyboardButton(text="💰 Avans yozish")],
        [KeyboardButton(text="📥 Excel (Oy yakuni)"), KeyboardButton(text="⚙️ Sozlamalar")]
    ], resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Bekor qilish")]], resize_keyboard=True)

settings_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi xodim qo'shish", callback_data="set_add")],
        [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="set_edit"), InlineKeyboardButton(text="🗑 O'chirish", callback_data="set_del")]
    ]
)

edit_options = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="👤 Ismni o'zgartirish", callback_data="edit_name")],
        [InlineKeyboardButton(text="💵 Narxni o'zgartirish", callback_data="edit_rate")],
        [InlineKeyboardButton(text="📍 Blokni o'zgartirish", callback_data="edit_loc")],
    ]
)

def approval_kb(worker_id, amount):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Berilsin", callback_data=f"app_adv_{worker_id}_{amount}"),
             InlineKeyboardButton(text="🚫 Rad etilsin", callback_data=f"rej_adv_{worker_id}")]
        ]
    )

worker_main = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="💰 Mening hisobim"), KeyboardButton(text="💸 Avans so'rash")]], resize_keyboard=True
)