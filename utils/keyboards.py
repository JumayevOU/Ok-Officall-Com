from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardRemove
)

def admin_main_kb():
    """Admin asosiy menyusi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Bugungi hisobot"), KeyboardButton(text="📊 Joriy holat")],
            [KeyboardButton(text="👥 Ishchilar"), KeyboardButton(text="💰 Avans yozish")],
            [KeyboardButton(text="📥 Excel hisobot"), KeyboardButton(text="⚙️ Sozlamalar")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Quyidagi menyulardan birini tanlang..."
    )

def worker_main_kb():
    """Ishchi asosiy menyusi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Mening hisobim"), KeyboardButton(text="💸 Avans so'rash")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Amalni tanlang..."
    )

# --- YORDAMCHI KLAVISHATURALAR ---
cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
    resize_keyboard=True,
    one_time_keyboard=True
)

# YANGI: Hisobot paytida chiqadigan tugmalar
report_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➡️ O'tkazib yuborish")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ], 
    resize_keyboard=True
)

remove_kb = ReplyKeyboardRemove()

# --- INLINE KLAVISHATURALAR (SOZLAMALAR) ---
settings_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi ishchi qo'shish", callback_data="add_worker")],
        [
            InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="edit_worker"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data="delete_worker")
        ],
        # Statistika tugmasi kerak bo'lsa:
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")]
    ]
)

edit_options_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="👤 Ism", callback_data="edit_name")],
        [InlineKeyboardButton(text="💰 Soatlik narx", callback_data="edit_rate")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_edit")]
    ]
)

def approval_kb(worker_id: int, amount: float):
    """Avans tasdiqlash"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_adv_{worker_id}_{amount}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_adv_{worker_id}_{amount}")
            ]
        ]
    )
