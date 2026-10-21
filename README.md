# 💰 Shaxsiy va Jamoaviy Moliya (Hisob-kitob) Telegram Boti

Ushbu Telegram bot ham **shaxsiy moliya**, ham **Telegram guruhlarida** umumiy sarf-xarajatlarni birgalikda qayd qilib borish uchun mo'ljallangan.

---

## 👥 Guruhlarda Ishlatish (Jamoaviy / Oila / Do'stlar xarajatlari)

Botni guruhga qo'shib, umumiy xarajatlarni oson boshqarishingiz mumkin:
1. **Tezkor harajat kiritish:** Guruhda har kim o'z sarflagan pulini oddiy matn ko'rinishida yozadi:
   - `50000 tushlik`
   - `taksi 25000`
   - `benzin 120k`
   - `1.5 mln arenda`
   - `-45000 dorilar`
   - yoki `/harajat 70000 bozorlik`
2. **Avtomatik hisob-kitob:** Bot harajatni umumiy xarajatlar ro'yxatiga qo'shadi, toifani avtomatik aniqlaydi va guruhning yangilangan umumiy harajatini darhol ko'rsatadi.
3. **Guruh buyruqlari:**
   - `/hisobot` yoki `/balans` — Guruhning umumiy sarf-harajatlari, bugungi, shu oylik ko'rsatkichlar hamda kim qancha sarflagani (foizlarda).
   - `/tarix` — Guruhdagi oxirgi 7 ta xarajat ro'yxati.
   - `/bekor` — Xato kiritilgan oxirgi harajatni o'chirish.
   - `/yordam` — Guruhda foydalanish bo'yicha to'liq qo'llanma.

> 💡 **MUHIM ESLATMA (Guruhda xabarlarni o'qish uchun):**
> Telegram xavfsizlik qoidalariga ko'ra botlar guruhdagi oddiy xabarlarni ko'rishi uchun:
> 1. Botni guruhda **Admin** qiling, **YOKI**
> 2. [@BotFather](https://t.me/BotFather) ga kirib: `/setprivacy` -> botingizni tanlang -> **Disable** qiling.

---

## 👤 Shaxsiy Chatdagi Funksiyalar:

1. **➕ Daromad qo'shish**: Summa, toifa va izohni ketma-ket kiritish.
2. **➖ Harajat qo'shish**: Harajatni toifasi bilan qayd qilish.
3. **💰 Balans**: Shaxsiy hamyon balansi, jami tushum va xarajatlar.
4. **📊 Hisobot**: Bugun, Shu oy va Barcha davr bo'yicha toifalar kesimidagi hisobot.
5. **🕒 Oxirgi amallar**: So'nggi amallar tarixi.
6. **⚙️ Sozlamalar**: Oxirgi amalni bekor qilish yoki barcha ma'lumotlarni tozalash.

---

## 📁 Loyiha Tuzilishi:

- [bot.py](file:///c:/Users/Shahriyor/OneDrive/Desktop/tgbot/bot.py) — Botning asosiy kodi (guruh va shaxsiy chat ishlovchilari)
- [database.py](file:///c:/Users/Shahriyor/OneDrive/Desktop/tgbot/database.py) — SQLite ma'lumotlar bazasi (guruhlar, foydalanuvchilar va tranzaksiyalar)
- [keyboards.py](file:///c:/Users/Shahriyor/OneDrive/Desktop/tgbot/keyboards.py) — Reply va Inline menyular
- [config.py](file:///c:/Users/Shahriyor/OneDrive/Desktop/tgbot/config.py) — Konfiguratsiya va bot tokeni
- [run.bat](file:///c:/Users/Shahriyor/OneDrive/Desktop/tgbot/run.bat) — Windows uchun bitta bosishda ishga tushirish skripti
- `.env` — Bot tokeni saqlanadigan maxfiy fayl

---

## 🚀 Ishga Tushirish:

Terminalda quyidagi buyruq orqali yoki `run.bat` faylini ikki marta bosib ishga tushirishingiz mumkin:
```bash
python bot.py
```
