import asyncio
import logging
import re
import sys

# Windows konsolida emojilar to'g'ri chiqishi uchun UTF-8 sozlamasi
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

import config
import database as db
import keyboards as kb

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Bot va Dispetcher
if not config.BOT_TOKEN:
    print("\n❌ XATOLIK: .env faylida BOT_TOKEN ko'rsatilmagan!")
    print("Iltimos, BotFather'dan olingan tokenni .env fayliga kiriting va qayta ishga tushiring.\n")
    sys.exit(1)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


# FSM Holatlari (Ketma-ket ma'lumot kiritish uchun)
class IncomeState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_comment = State()


class ExpenseState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_comment = State()


# Pul miqdorini formatlash funksiyasi (Masalan: 100 000 so'm)
def format_money(amount: float) -> str:
    if amount == int(amount):
        formatted = f"{int(amount):,}".replace(",", " ")
    else:
        formatted = f"{amount:,.2f}".replace(",", " ")
    return f"{formatted} so'm"


# Foydalanuvchi kiritgan summani tozalash va songa o'tkazish
def parse_amount(text: str) -> float | None:
    cleaned = text.replace(" ", "").replace(",", ".").replace("'", "").replace("`", "")
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


# Toifalar lug'ati (Avtomatik toifani aniqlash uchun)
CATEGORY_KEYWORDS = {
    "🛒 Oziq-ovqat": [
        "ovqat", "tushlik", "nonushta", "kechki", "osh", "somsa", "shashlik", 
        "non", "bozor", "bozorlik", "go'sht", "gosht", "choy", "suv", "ichimlik",
        "meva", "sabzavot", "supermarket", "korzinka", "makro", "havas", "lavash", 
        "burger", "pizza", "doner", "sut", "qatiq", "kartoshka", "piyoz"
    ],
    "🚕 Transport": [
        "taxi", "taksi", "yandex", "benzin", "metan", "propan", "zapravka", 
        "moy", "moyka", "avto", "mashina", "avtoservis", "yo'l", "yol", "avtobus", 
        "metro", "bilet", "samolyot", "poyezd", "parking", "jarima"
    ],
    "🏠 Kommunal/Uy": [
        "uy", "ijara", "arenda", "kvartira", "svet", "gaz", "suv", "elektr", 
        "musor", "kommunal", "wifi", "internet", "remont", "usta"
    ],
    "💊 Sog'liq/Dorixona": [
        "dori", "apteka", "dorixona", "shifoxona", "klinika", "doktor", "vrach", "tish", "analiz", "davolanish"
    ],
    "☕️ Kafe/Dam olish": [
        "kafe", "restoran", "choyxona", "kofe", "coffee", "muzqaymoq", "kino", "dam", "sayr", "bilyard", "playstation", "ps"
    ],
    "📚 Ta'lim/Kitob": [
        "kitob", "kurs", "dars", "kontrakt", "maktab", "o'qish", "oqish", "bog'cha", "repetitor", "daftar", "ruchka"
    ],
    "🛍 Xaridlar": [
        "kiyim", "poyafzal", "shim", "ko'ylak", "xarid", "magazin", "telefon", "naushnik", "texnika", "soat"
    ]
}


def detect_category(text: str) -> str:
    """Matndan toifani aniqlash"""
    if not text:
        return "🔄 Boshqa xarajat"
    lower = text.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return cat
    return "🔄 Boshqa xarajat"


def parse_group_expense(text: str):
    """
    Xabardan harajat summasi va izohini ajratib olish.
    Qo'llab-quvvatlanadigan formatlar:
    - 50000 tushlik
    - tushlik 50 000
    - benzin 120k
    - 200 ming bozorlik
    - 1.5 mln arenda
    - /harajat 35000 non va choy
    - -45000 dorilar
    - 50000
    """
    if not text:
        return None
    text = text.strip()
    
    # Harajat bo'lmagan buyruqlarni o'tkazib yuborish
    if text.startswith('/') and not re.match(r'^/(harajat|xarajat|chiqim|rasxod|rashod|expense)\b', text, re.I):
        return None
        
    # Komanda prefiksini tozalash
    text = re.sub(r'^/(harajat|xarajat|chiqim|rasxod|rashod|expense)(@\w+)?\s*', '', text, flags=re.I)
    
    # 'harajat:', 'xarajat:', '-' kabi so'zlarni tozalash
    text = re.sub(r'^(harajat|xarajat|chiqim|rasxod|rashod)\s*[:\-]?\s*', '', text, flags=re.I)
    text = re.sub(r'^\-\s*', '', text)
    
    # Telefon raqamlari yoki sanalarni chetlab o'tish
    if re.search(r'(\+?998\d{9}|\b\d{2}\s*\d{3}\s*\d{2}\s*\d{2}\b)', text):
        return None
    if re.search(r'\b\d{4}[-/. ]\d{1,2}[-/. ]\d{1,2}\b', text) or re.search(r'\b\d{1,2}[-/. ]\d{1,2}[-/. ]\d{4}\b', text):
        return None
        
    patterns = [
        # Summa boshida: 50 000 tushlik, 50k benzin, 100000
        r'^(?P<num>\d+(?:[\s.,]\d{3})*(?:[.,]\d+)?)\s*(?P<unit>k|ming|mln|m|million|so[\'\`\ʼ]?m|som|sum|uzs|\$)?\s*(?P<rest>.*)$',
        # Summa oxirida: tushlik 50 000, benzinga 120k
        r'^(?P<rest>.*?)\s+(?P<num>\d+(?:[\s.,]\d{3})*(?:[.,]\d+)?)\s*(?P<unit>k|ming|mln|m|million|so[\'\`\ʼ]?m|som|sum|uzs|\$)?\s*$'
    ]
    
    for pat in patterns:
        m = re.match(pat, text, re.I)
        if m:
            num_raw = m.group('num').replace(' ', '').replace(',', '.')
            if num_raw.count('.') > 1:
                num_raw = num_raw.replace('.', '')
            elif num_raw.count('.') == 1:
                parts = num_raw.split('.')
                if len(parts[1]) == 3 and not (m.group('unit') or '').lower() in ('mln', 'm', 'million'):
                    num_raw = parts[0] + parts[1]
            try:
                val = float(num_raw)
            except ValueError:
                continue
                
            unit = (m.group('unit') or '').lower()
            rest = m.group('rest').strip()
            rest = re.sub(r'^[:\-\s]+|[:\-\s]+$', '', rest)
            
            if unit in ('k', 'ming'):
                val *= 1000
            elif unit in ('mln', 'm', 'million'):
                val *= 1000000
                
            # Kichik sonlar va yillarni filtrlash
            if not unit and not rest:
                if val < 500 or (1990 <= val <= 2040):
                    continue
            if not unit and val < 500:
                continue
                
            return val, rest
            
    return None


# ==================== 👥 GURUH UCHUN HANDLERLAR ====================

@dp.message(F.chat.type.in_({"group", "supergroup"}), CommandStart())
async def cmd_start_group(message: Message):
    db.register_chat(message.chat.id, message.chat.title or "Guruh", message.chat.type)
    total_exp = db.get_group_total_expense(message.chat.id)
    text = (
        f"👋 Assalomu alaykum! Men <b>{message.chat.title}</b> guruhidagi <b>umumiy harajatlarni</b> hisoblab boruvchi botman.\n\n"
        "Guruhda kimdir harajat qilsa, shunchaki xabar yozing:\n"
        "👉 <code>50000 tushlik</code>\n"
        "👉 <code>taksi 25000</code>\n"
        "👉 <code>benzin 120k</code>\n\n"
        f"📊 Hozirgi umumiy harajat: <b>{format_money(total_exp)}</b>\n\n"
        "Buyruqlar: <code>/hisobot</code>, <code>/tarix</code>, <code>/bekor</code>, <code>/yordam</code>"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(F.chat.type.in_({"group", "supergroup"}), F.new_chat_members)
async def bot_added_to_group(message: Message):
    bot_user = await bot.get_me()
    for member in message.new_chat_members:
        if member.id == bot_user.id:
            db.register_chat(message.chat.id, message.chat.title or "Guruh", message.chat.type)
            text = (
                f"🎉 Assalomu alaykum! Men ushbu guruhdagi barcha <b>umumiy harajatlarni</b> yuritishga tayyorman!\n\n"
                "Harajat kiritish uchun guruhga xabar yozishingiz kifoya:\n"
                "• <code>50000 tushlik</code>\n"
                "• <code>taksi 25000</code>\n"
                "• <code>benzin 120k</code>\n\n"
                "📊 Guruh hisoboti: <code>/hisobot</code>\n"
                "ℹ️ Qo'llanma: <code>/yordam</code>\n\n"
                "<i>💡 Eslatma: Bot barcha xabarlarni ko'rishi uchun uni Admin qiling yoki @BotFather da 'Group Privacy' ni o'chiring!</i>"
            )
            await message.answer(text, parse_mode="HTML")
            break


@dp.message(F.chat.type.in_({"group", "supergroup"}), Command("help", "yordam"))
async def cmd_group_help(message: Message):
    help_text = (
        "📖 <b>Guruhda botdan foydalanish qo'llanmasi:</b>\n\n"
        "Guruhda harajat kiritish juda oddiy, shunchaki xabar yuboring:\n"
        "• <code>50000 tushlik</code>\n"
        "• <code>taksi 25000</code>\n"
        "• <code>benzin 120k</code>\n"
        "• <code>1.5 mln arenda</code>\n"
        "• yoki <code>/harajat 70000 bozorlik</code>\n\n"
        "<b>Guruh buyruqlari:</b>\n"
        "📊 <code>/hisobot</code> yoki <code>/balans</code> — Guruhning umumiy harajatlari va kim qancha sarflagani\n"
        "🕒 <code>/tarix</code> — Oxirgi 7 ta harajatlar ro'yxati\n"
        "↩️ <code>/bekor</code> — Siz kiritgan oxirgi harajatni bekor qilish\n"
        "ℹ️ <code>/yordam</code> — Ushbu qo'llanma\n\n"
        "<i>💡 Eslatma: Bot barcha xabarlarni ko'rishi uchun uni guruhda <b>Admin</b> qiling yoki @BotFather orqali 'Group Privacy' rejimini o'chiring (Disable).</i>"
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message(F.chat.type.in_({"group", "supergroup"}), Command("hisobot", "balans", "xarajatlar", "stat"))
async def cmd_group_report(message: Message):
    stats = db.get_group_stats(message.chat.id, "all")
    title = message.chat.title or "Guruh"
    
    text = (
        f"📊 <b>GURUHNING UMUMIY HARAJATLARI</b>\n"
        f"👥 Guruh: <b>{title}</b>\n"
        "────────────────────\n"
        f"📅 <b>Bugungi harajat:</b> {format_money(stats['today_expense'])}\n"
        f"🗓 <b>Shu oylik harajat:</b> {format_money(stats['month_expense'])}\n"
        f"📈 <b>Jami umumiy harajat:</b> {format_money(stats['total_expense'])}\n"
        "────────────────────\n"
    )
    
    # Kim qancha sarfladi
    if stats["user_breakdown"]:
        text += "👥 <b>Kim qancha kiritdi:</b>\n"
        total = stats["total_expense"]
        for idx, (full_name, username, user_amt, _) in enumerate(stats["user_breakdown"], start=1):
            pct = (user_amt / total * 100) if total > 0 else 0
            u_name = f" (@{username})" if username else ""
            text += f"{idx}. 👤 <b>{full_name}</b>{u_name}: {format_money(user_amt)} (<i>{pct:.1f}%</i>)\n"
        text += "────────────────────\n"
    else:
        text += "<i>Hali hech kim harajat kiritmagan.</i>\n────────────────────\n"
        
    # Toifalar bo'yicha
    if stats["category_breakdown"]:
        text += "📉 <b>Toifalar bo'yicha:</b>\n"
        for cat, cat_amt in stats["category_breakdown"]:
            text += f" • {cat}: <b>{format_money(cat_amt)}</b>\n"
        text += "────────────────────\n"
        
    text += "<i>Yangi harajat kiritish: masalan <code>50000 tushlik</code></i>"
    await message.answer(text, parse_mode="HTML")


@dp.message(F.chat.type.in_({"group", "supergroup"}), Command("tarix", "oxirgi"))
async def cmd_group_history(message: Message):
    txs = db.get_group_recent_transactions(message.chat.id, limit=7)
    if not txs:
        await message.answer("ℹ️ Guruhda hali hech qanday harajat kiritilmagan.", parse_mode="HTML")
        return
        
    text = "🕒 <b>GURUHNING SO'NGGI HARAJATLARI:</b>\n────────────────────\n"
    for tx in txs:
        comm = f" (<i>{tx['comment']}</i>)" if tx["comment"] else ""
        text += f"➖ <b>{format_money(tx['amount'])}</b> — {tx['category']}{comm}\n"
        text += f"   👤 {tx['full_name']} | 📅 <code>{tx['date']}</code>\n"
        text += "────────────────────\n"
        
    text += f"📊 Jami umumiy harajat: <b>{format_money(db.get_group_total_expense(message.chat.id))}</b>"
    await message.answer(text, parse_mode="HTML")


@dp.message(F.chat.type.in_({"group", "supergroup"}), Command("bekor", "undo"))
async def cmd_group_undo(message: Message):
    deleted = db.delete_last_group_transaction(message.chat.id, user_id=message.from_user.id)
    if deleted:
        total_exp = db.get_group_total_expense(message.chat.id)
        text = (
            "↩️ <b>Oxirgi harajat bekor qilindi!</b>\n\n"
            f"👤 Kim: <b>{deleted['full_name']}</b>\n"
            f"🗑 O'chirildi: <b>-{format_money(deleted['amount'])}</b> ({deleted['category']})\n"
        )
        if deleted.get("comment"):
            text += f"💬 Izoh: <i>{deleted['comment']}</i>\n"
        text += f"────────────────────\n📊 Yangi umumiy harajat: <b>{format_money(total_exp)}</b>"
    else:
        text = "ℹ️ Siz kiritgan bekor qilinadigan harajat topilmadi."
        
    await message.answer(text, parse_mode="HTML")


@dp.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def process_group_expense_message(message: Message):
    parsed = parse_group_expense(message.text)
    if not parsed:
        return
        
    amount, comment = parsed
    category = detect_category(comment)
    
    db.register_chat(message.chat.id, message.chat.title or "Guruh", message.chat.type)
    db.register_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    
    db.add_transaction(
        user_id=message.from_user.id,
        trans_type="expense",
        amount=amount,
        category=category,
        comment=comment if comment else None,
        chat_id=message.chat.id
    )
    
    today_expense = db.get_group_today_expense(message.chat.id)
    total_expense = db.get_group_total_expense(message.chat.id)
    
    user_display = message.from_user.mention_html(message.from_user.full_name)
    
    response = (
        "✅ <b>Harajat umumiy hisobga qo'shildi!</b>\n\n"
        f"👤 <b>Kim:</b> {user_display}\n"
        f"💸 <b>Summa:</b> -{format_money(amount)}\n"
        f"🏷 <b>Toifa:</b> {category}\n"
    )
    if comment:
        response += f"💬 <b>Izoh:</b> <i>{comment}</i>\n"
        
    response += (
        "────────────────────\n"
        f"📅 <b>Bugungi guruh harajati:</b> {format_money(today_expense)}\n"
        f"📊 <b>Guruhning umumiy harajati:</b> {format_money(total_expense)}\n\n"
        "<i>Bekor qilish: /bekor</i>"
    )
    
    await message.reply(response, parse_mode="HTML")


# ==================== 👤 SHAXSIY CHAT HANDLERLARI ====================

@dp.message(F.chat.type == "private", CommandStart())
async def cmd_start_private(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    db.register_user(user.id, user.full_name, user.username)
    
    welcome_text = (
        f"Assalomu alaykum, <b>{user.full_name}</b>!\n\n"
        "Men sizning shaxsiy va guruhdagi <b>Hisob-kitob (Moliya)</b> botingizman.\n"
        "Meni guruhlarga qo'shib, umumiy xarajatlarni ham yuritishingiz mumkin.\n\n"
        "Quyidagi tugmalardan birini tanlang yoki to'g'ridan-to'g'ri yozing (masalan: <code>50000 tushlik</code>):"
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())


@dp.message(F.chat.type == "private", Command("help"))
@dp.message(F.chat.type == "private", F.text == "ℹ️ Yordam")
async def cmd_help_private(message: Message):
    help_text = (
        "<b>Botdan qanday foydalaniladi?</b>\n\n"
        "➕ <b>Daromad:</b> Tushgan pullarni kiritish (masalan: oylik, savdo).\n"
        "➖ <b>Harajat:</b> Sarflangan xarajatlarni toifasi bilan kiritish.\n"
        "💰 <b>Balans:</b> Joriy qoldiq pul, jami daromad va jami xarajat.\n"
        "📊 <b>Hisobot:</b> Bugungi, oylik va umumiy sarf-xarajatlar statistikasi.\n"
        "🕒 <b>Oxirgi amallar:</b> So'nggi 7 ta kiritilgan yozuvlar tarixi.\n"
        "⚙️ <b>Sozlamalar:</b> Yanglish kiritilgan amalni o'chirish yoki bazani tozalash.\n\n"
        "👥 <b>Guruhda foydalanish:</b> Botni guruhga qo'shib, kimdir <code>50000 tushlik</code> yoki <code>taksi 20000</code> deb yozsa, bot uni guruhning umumiy harajatiga avtomatik qo'shib hisoblaydi!\n\n"
        "<i>Har bir amalni bekor qilish uchun '❌ Bekor qilish' tugmasini bosishingiz mumkin.</i>"
    )
    await message.answer(help_text, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())


@dp.message(F.chat.type == "private", F.text == "❌ Bekor qilish")
async def process_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    await message.answer("Amal bekor qilindi.", reply_markup=kb.main_menu_keyboard())


@dp.callback_query(F.data == "cancel_action")
async def process_cancel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    if callback.message.chat.type == "private":
        await callback.message.answer("Amal bekor qilindi.", reply_markup=kb.main_menu_keyboard())
    else:
        await callback.message.answer("Amal bekor qilindi.")
    await callback.answer()


# ==================== ➕ DAROMAD QO'SHISH ====================

@dp.message(F.chat.type == "private", F.text == "➕ Daromad")
async def start_add_income(message: Message, state: FSMContext):
    await state.set_state(IncomeState.waiting_for_amount)
    await message.answer(
        "💵 <b>Daromad summasini kiriting:</b>\n<i>Masalan: 500000 yoki 1 200 000</i>",
        parse_mode="HTML",
        reply_markup=kb.cancel_keyboard()
    )


@dp.message(IncomeState.waiting_for_amount)
async def process_income_amount(message: Message, state: FSMContext):
    amount = parse_amount(message.text)
    if not amount:
        await message.answer("⚠️ Iltimos, faqat musbat son kiriting (masalan: 150000):")
        return
    
    await state.update_data(amount=amount)
    await state.set_state(IncomeState.waiting_for_category)
    await message.answer(
        f"Kiritilgan summa: <b>{format_money(amount)}</b>\n\n"
        "Endi daromad <b>toifasini (kategoriyasini)</b> tanlang:",
        parse_mode="HTML",
        reply_markup=kb.income_categories_keyboard()
    )


@dp.callback_query(IncomeState.waiting_for_category, F.data.startswith("inc_cat:"))
async def process_income_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(IncomeState.waiting_for_comment)
    
    await callback.message.edit_text(f"Tanlangan toifa: <b>{category}</b>", parse_mode="HTML")
    await callback.message.answer(
        "📝 Ushbu daromadga izoh qoldirasizmi? (ixtiyoriy):\n"
        "<i>Agar izoh kerak bo'lmasa, 'O'tkazib yuborish' tugmasini bosing.</i>",
        parse_mode="HTML",
        reply_markup=kb.skip_or_cancel_keyboard()
    )
    await callback.answer()


@dp.message(IncomeState.waiting_for_comment)
async def process_income_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data["amount"]
    category = data["category"]
    
    comment = None
    if message.text != "⏩ O'tkazib yuborish":
        comment = message.text
        
    db.add_transaction(
        user_id=message.from_user.id,
        trans_type="income",
        amount=amount,
        category=category,
        comment=comment,
        chat_id=message.chat.id
    )
    
    await state.clear()
    
    response = (
        "✅ <b>Daromad muvaffaqiyatli saqlandi!</b>\n\n"
        f"💰 Summa: <b>+{format_money(amount)}</b>\n"
        f"🏷 Toifa: <b>{category}</b>\n"
    )
    if comment:
        response += f"💬 Izoh: <i>{comment}</i>\n"
        
    balance_info = db.get_balance(message.from_user.id, chat_id=message.chat.id)
    response += f"\n💳 Joriy balans: <b>{format_money(balance_info['balance'])}</b>"
    
    await message.answer(response, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())


# ==================== ➖ HARAJAT QO'SHISH ====================

@dp.message(F.chat.type == "private", F.text == "➖ Harajat")
async def start_add_expense(message: Message, state: FSMContext):
    await state.set_state(ExpenseState.waiting_for_amount)
    await message.answer(
        "💸 <b>Harajat summasini kiriting:</b>\n<i>Masalan: 35000 yoki 120 000</i>",
        parse_mode="HTML",
        reply_markup=kb.cancel_keyboard()
    )


@dp.message(ExpenseState.waiting_for_amount)
async def process_expense_amount(message: Message, state: FSMContext):
    amount = parse_amount(message.text)
    if not amount:
        await message.answer("⚠️ Iltimos, to'g'ri son kiriting (masalan: 45000):")
        return
    
    await state.update_data(amount=amount)
    await state.set_state(ExpenseState.waiting_for_category)
    await message.answer(
        f"Kiritilgan summa: <b>{format_money(amount)}</b>\n\n"
        "Harajat <b>toifasini (kategoriyasini)</b> tanlang:",
        parse_mode="HTML",
        reply_markup=kb.expense_categories_keyboard()
    )


@dp.callback_query(ExpenseState.waiting_for_category, F.data.startswith("exp_cat:"))
async def process_expense_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(ExpenseState.waiting_for_comment)
    
    await callback.message.edit_text(f"Tanlangan toifa: <b>{category}</b>", parse_mode="HTML")
    await callback.message.answer(
        "📝 Ushbu harajatga izoh qoldirasizmi? (ixtiyoriy):\n"
        "<i>Agar izoh kerak bo'lmasa, 'O'tkazib yuborish' tugmasini bosing.</i>",
        parse_mode="HTML",
        reply_markup=kb.skip_or_cancel_keyboard()
    )
    await callback.answer()


@dp.message(ExpenseState.waiting_for_comment)
async def process_expense_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data["amount"]
    category = data["category"]
    
    comment = None
    if message.text != "⏩ O'tkazib yuborish":
        comment = message.text
        
    db.add_transaction(
        user_id=message.from_user.id,
        trans_type="expense",
        amount=amount,
        category=category,
        comment=comment,
        chat_id=message.chat.id
    )
    
    await state.clear()
    
    response = (
        "✅ <b>Harajat muvaffaqiyatli saqlandi!</b>\n\n"
        f"💸 Summa: <b>-{format_money(amount)}</b>\n"
        f"🏷 Toifa: <b>{category}</b>\n"
    )
    if comment:
        response += f"💬 Izoh: <i>{comment}</i>\n"
        
    balance_info = db.get_balance(message.from_user.id, chat_id=message.chat.id)
    response += f"\n💳 Joriy balans: <b>{format_money(balance_info['balance'])}</b>"
    
    await message.answer(response, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())


# ==================== 💰 BALANS ====================

@dp.message(F.chat.type == "private", F.text == "💰 Balans")
async def show_balance(message: Message):
    bal = db.get_balance(message.from_user.id, chat_id=message.chat.id)
    
    icon = "🟢" if bal["balance"] >= 0 else "🔴"
    text = (
        "💰 <b>SIZNING HAMYONINGIZ:</b>\n"
        "────────────────────\n"
        f"📈 Jami daromad: <b>+{format_money(bal['income'])}</b>\n"
        f"📉 Jami harajat: <b>-{format_money(bal['expense'])}</b>\n"
        "────────────────────\n"
        f"{icon} Joriy qoldiq: <b>{format_money(bal['balance'])}</b>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())


# ==================== 📊 HISOBOT VA STATISTIKA ====================

def generate_report_text(stats: dict, title: str) -> str:
    text = (
        f"📊 <b>{title.upper()} HISOBOTI:</b>\n"
        "────────────────────\n"
        f"📈 Daromad: <b>+{format_money(stats['income'])}</b>\n"
        f"📉 Harajat: <b>-{format_money(stats['expense'])}</b>\n"
        f"💵 Qoldiq: <b>{format_money(stats['balance'])}</b>\n"
        "────────────────────\n"
    )
    
    if stats["expense_by_cat"]:
        text += "\n📉 <b>Harajatlar toifalar bo'yicha:</b>\n"
        total_exp = stats["expense"]
        for cat, amt in stats["expense_by_cat"]:
            percent = (amt / total_exp * 100) if total_exp > 0 else 0
            text += f" • {cat}: <b>{format_money(amt)}</b> (<i>{percent:.1f}%</i>)\n"
    else:
        text += "\n<i>Ushbu davrda hech qanday harajat bo'lmagan.</i>\n"

    if stats["income_by_cat"]:
        text += "\n📈 <b>Daromadlar toifalar bo'yicha:</b>\n"
        for cat, amt in stats["income_by_cat"]:
            text += f" • {cat}: <b>{format_money(amt)}</b>\n"

    return text


@dp.message(F.chat.type == "private", F.text == "📊 Hisobot")
async def show_report_menu(message: Message):
    stats = db.get_period_stats(message.from_user.id, "today", chat_id=message.chat.id)
    text = generate_report_text(stats, "Bugungi")
    text += "\n<i>Davrni o'zgartirish uchun quyidagi tugmalardan birini bosing:</i>"
    await message.answer(text, parse_mode="HTML", reply_markup=kb.period_stats_keyboard())


@dp.callback_query(F.data.startswith("stat_period:"))
async def process_stat_period(callback: CallbackQuery):
    period = callback.data.split(":")[1]
    title_map = {
        "today": "Bugungi",
        "month": "Shu oy",
        "all": "Barcha davr"
    }
    title = title_map.get(period, "Umumiy")
    stats = db.get_period_stats(callback.from_user.id, period, chat_id=callback.message.chat.id)
    text = generate_report_text(stats, title)
    text += "\n<i>Davrni o'zgartirish uchun quyidagi tugmalardan birini bosing:</i>"
    
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.period_stats_keyboard())
    except Exception:
        pass
    await callback.answer()


# ==================== 🕒 OXIRGI AMALLAR TARIXI ====================

@dp.message(F.chat.type == "private", F.text == "🕒 Oxirgi amallar")
async def show_recent_transactions(message: Message):
    txs = db.get_recent_transactions(message.from_user.id, limit=7, chat_id=message.chat.id)
    if not txs:
        await message.answer("ℹ️ Sizda hali hech qanday amallar kiritilmagan.", reply_markup=kb.main_menu_keyboard())
        return
        
    text = "🕒 <b>OXIRGI 7 TA AMAL:</b>\n────────────────────\n"
    for tx in txs:
        sign = "➕" if tx["type"] == "income" else "➖"
        comm = f" (<i>{tx['comment']}</i>)" if tx["comment"] else ""
        text += f"{sign} <b>{format_money(tx['amount'])}</b> — {tx['category']}{comm}\n"
        text += f"   📅 <code>{tx['date']}</code>\n"
        text += "────────────────────\n"
        
    await message.answer(text, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())


# ==================== ⚙️ SOZLAMALAR VA BOSHQARUV ====================

@dp.message(F.chat.type == "private", F.text == "⚙️ Sozlamalar")
async def show_settings(message: Message):
    text = (
        "⚙️ <b>SOZLAMALAR VA BOSHQARUV:</b>\n\n"
        "• <b>Oxirgi amalni bekor qilish:</b> Adashib xato summa kiritgan bo'lsangiz, eng so'nggi amalni o'chiradi.\n"
        "• <b>Tozalash:</b> Barcha daromad va xarajatlar tarixini o'chiradi."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=kb.settings_keyboard())


@dp.callback_query(F.data == "undo_last")
async def undo_last_callback(callback: CallbackQuery):
    deleted = db.delete_last_transaction(callback.from_user.id, chat_id=callback.message.chat.id)
    if deleted:
        sign = "Daromad" if deleted["type"] == "income" else "Harajat"
        msg = f"✅ Oxirgi {sign} (<b>{format_money(deleted['amount'])}</b> - {deleted['category']}) bekor qilindi va o'chirildi."
    else:
        msg = "ℹ️ Bekor qilish uchun hech qanday amal topilmadi."
        
    await callback.message.edit_text(msg, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "confirm_clear_all")
async def confirm_clear_callback(callback: CallbackQuery):
    text = "⚠️ <b>DIQQAT!</b>\nHaqiqatan ham barcha daromad va harajatlaringizni o'chirib tashlamoqchimisiz? Bu amalni ortga qaytarib bo'lmaydi!"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.confirm_clear_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "do_clear_all")
async def do_clear_all_callback(callback: CallbackQuery):
    db.clear_all_transactions(callback.from_user.id, chat_id=callback.message.chat.id)
    await callback.message.edit_text("🗑 Barcha hisobot va amallar tarixi tozalandi.", parse_mode="HTML")
    await callback.answer()


# Shaxsiy chatda tezkor harajat yozilganda (masalan: 50000 tushlik)
@dp.message(F.chat.type == "private", F.text)
async def process_private_quick_expense(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        return
        
    parsed = parse_group_expense(message.text)
    if not parsed:
        return
        
    amount, comment = parsed
    category = detect_category(comment)
    
    db.register_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    db.add_transaction(
        user_id=message.from_user.id,
        trans_type="expense",
        amount=amount,
        category=category,
        comment=comment if comment else None,
        chat_id=message.chat.id
    )
    
    balance_info = db.get_balance(message.from_user.id, chat_id=message.chat.id)
    response = (
        "✅ <b>Harajat muvaffaqiyatli saqlandi!</b>\n\n"
        f"💸 Summa: <b>-{format_money(amount)}</b>\n"
        f"🏷 Toifa: <b>{category}</b>\n"
    )
    if comment:
        response += f"💬 Izoh: <i>{comment}</i>\n"
        
    response += f"\n💳 Joriy balans: <b>{format_money(balance_info['balance'])}</b>"
    await message.answer(response, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())


# ==================== ASOSIY ISHGA TUSHIRISH (MAIN) ====================

async def main():
    db.init_db()
    print("🚀 Baza ishga tushirildi.")
    print("🤖 Bot ishga tushmoqda... To'xtatish uchun Ctrl+C bosing.")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Bot to'xtatildi.")
