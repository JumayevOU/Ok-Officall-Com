from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def admin_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👥 Ishchilar"), KeyboardButton(text="📊 Joriy holat")],
        [KeyboardButton(text="💰 Avans yozish"), KeyboardButton(text="📝 Bugungi hisobot")],
        [KeyboardButton(text="📥 Excel hisobot"), KeyboardButton(text="⚙️ Sozlamalar")]
    ], resize_keyboard=True)

def worker_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💰 Mening hisobim")],
        [KeyboardButton(text="💸 Avans so'rash")]
    ], resize_keyboard=True)


cancel_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="❌ Bekor qilish")]
], resize_keyboard=True, one_time_keyboard=True)

report_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="➡️ O'tkazib yuborish")],
    [KeyboardButton(text="❌ Bekor qilish")]
], resize_keyboard=True)

remove_kb = ReplyKeyboardRemove() # Import qilish kerak: from aiogram.types import ReplyKeyboardRemove


settings_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="➕ Yangi ishchi qo'shish")],
    [KeyboardButton(text="🗑 Ishchini o'chirish"), KeyboardButton(text="✏️ Tahrirlash")],
    [KeyboardButton(text="❌ Bekor qilish")]
], resize_keyboard=True)

# --- INLINE TUGMALAR ---

edit_options_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👤 Ismni o'zgartirish", callback_data="edit_name")],
    [InlineKeyboardButton(text="💰 Stavkani o'zgartirish", callback_data="edit_rate")],
    [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_edit")]
])

def approval_kb(worker_id, amount):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_adv_{worker_id}_{amount}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_adv_{worker_id}_{amount}")
        ]
    ])
