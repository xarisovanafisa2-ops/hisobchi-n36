from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# 1. Asosiy Menyu (Doimiy pastdagi tugmalar)
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="➕ Daromad"),
            KeyboardButton(text="➖ Harajat")
        ],
        [
            KeyboardButton(text="💰 Balans"),
            KeyboardButton(text="📊 Hisobot")
        ],
        [
            KeyboardButton(text="🕒 Oxirgi amallar"),
            KeyboardButton(text="⚙️ Sozlamalar")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# 2. Bekor qilish / O'tkazib yuborish uchun yordamchi tugmalar
def skip_or_cancel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="⏩ O'tkazib yuborish")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="❌ Bekor qilish")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# 3. Daromad toifalari (Inline)
def income_categories_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="💼 Oylik maosh", callback_data="inc_cat:Oylik"),
            InlineKeyboardButton(text="🏢 Biznes/Savdo", callback_data="inc_cat:Biznes")
        ],
        [
            InlineKeyboardButton(text="🎁 Sovg'a / Mukofot", callback_data="inc_cat:Sovg'a"),
            InlineKeyboardButton(text="📈 Investitsiya", callback_data="inc_cat:Investitsiya")
        ],
        [
            InlineKeyboardButton(text="🔄 Boshqa daromad", callback_data="inc_cat:Boshqa")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# 4. Harajat toifalari (Inline)
def expense_categories_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="🛒 Oziq-ovqat", callback_data="exp_cat:Oziq-ovqat"),
            InlineKeyboardButton(text="🚕 Transport", callback_data="exp_cat:Transport")
        ],
        [
            InlineKeyboardButton(text="🏠 Kommunal/Uy", callback_data="exp_cat:Kommunal"),
            InlineKeyboardButton(text="🛍 Xaridlar", callback_data="exp_cat:Xaridlar")
        ],
        [
            InlineKeyboardButton(text="💊 Sog'liq/Dorixona", callback_data="exp_cat:Sog'liq"),
            InlineKeyboardButton(text="☕️ Kafe/Dam olish", callback_data="exp_cat:Kafe")
        ],
        [
            InlineKeyboardButton(text="📚 Ta'lim/Kitob", callback_data="exp_cat:Ta'lim"),
            InlineKeyboardButton(text="🔄 Boshqa xarajat", callback_data="exp_cat:Boshqa")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# 5. Hisobot davri tanlash (Inline)
def period_stats_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="📅 Bugun", callback_data="stat_period:today"),
            InlineKeyboardButton(text="🗓 Shu oy", callback_data="stat_period:month"),
            InlineKeyboardButton(text="📈 Barchasi", callback_data="stat_period:all")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# 6. Sozlamalar / Boshqaruv tugmalari (Inline)
def settings_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="↩️ Oxirgi amalni bekor qilish", callback_data="undo_last")
        ],
        [
            InlineKeyboardButton(text="🗑 Barcha ma'lumotlarni tozalash", callback_data="confirm_clear_all")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# 7. Tozalashni tasdiqlash
def confirm_clear_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Ha, barchasini tozalash", callback_data="do_clear_all"),
            InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
