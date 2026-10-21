import sqlite3
from typing import Dict, List, Optional, Tuple

DB_PATH = "finance.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Ma'lumotlar bazasi va jadvallarni yaratish va yangilash"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Foydalanuvchilar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Guruhlar / Chatlar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                chat_type TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Daromad va xarajatlar tranzaksiyalari jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER,
                type TEXT NOT NULL,           -- 'income' (daromad) yoki 'expense' (xarajat)
                amount REAL NOT NULL,          -- summa
                category TEXT NOT NULL,        -- toifa (masalan: Oziq-ovqat, Oylik)
                comment TEXT,                  -- ixtiyoriy izoh
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Eskirgan bazalar uchun chat_id ustunini tekshirish va qo'shish
        cursor.execute("PRAGMA table_info(transactions)")
        cols = [col[1] for col in cursor.fetchall()]
        if "chat_id" not in cols:
            cursor.execute("ALTER TABLE transactions ADD COLUMN chat_id INTEGER")
            cursor.execute("UPDATE transactions SET chat_id = user_id WHERE chat_id IS NULL")
            
        conn.commit()


def register_user(user_id: int, full_name: str, username: Optional[str] = None):
    """Foydalanuvchini bazaga qo'shish yoki yangilash"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, full_name, username)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = excluded.username
        """, (user_id, full_name, username))
        conn.commit()


def register_chat(chat_id: int, title: str, chat_type: str):
    """Guruh yoki chatni bazaga qo'shish yoki yangilash"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chats (chat_id, title, chat_type)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                chat_type = excluded.chat_type
        """, (chat_id, title, chat_type))
        conn.commit()


def add_transaction(
    user_id: int, 
    trans_type: str, 
    amount: float, 
    category: str, 
    comment: Optional[str] = None,
    chat_id: Optional[int] = None
) -> int:
    """Yangi daromad yoki xarajat yozuvini kiritish"""
    target_chat = chat_id if chat_id is not None else user_id
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (user_id, chat_id, type, amount, category, comment)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, target_chat, trans_type, amount, category, comment))
        conn.commit()
        return cursor.lastrowid


def get_balance(user_id: int, chat_id: Optional[int] = None) -> Dict[str, float]:
    """Umumiy balans va daromad/xarajatlarni olish"""
    target_chat = chat_id if chat_id is not None else user_id
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS total_expense
            FROM transactions
            WHERE chat_id = ?
        """, (target_chat,))
        
        row = cursor.fetchone()
        total_income = row[0]
        total_expense = row[1]
        balance = total_income - total_expense
        
        return {
            "income": total_income,
            "expense": total_expense,
            "balance": balance
        }


def get_period_stats(user_id: int, period: str = "today", chat_id: Optional[int] = None) -> Dict:
    """
    Davrlar bo'yicha statistika:
    period: 'today' (bugun), 'month' (shu oy), 'all' (barcha davr)
    """
    target_chat = chat_id if chat_id is not None else user_id
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if period == "today":
            date_filter = "date(created_at, 'localtime') = date('now', 'localtime')"
        elif period == "month":
            date_filter = "strftime('%Y-%m', created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')"
        else: # 'all'
            date_filter = "1=1"
            
        cursor.execute(f"""
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS total_expense
            FROM transactions
            WHERE chat_id = ? AND {date_filter}
        """, (target_chat,))
        row = cursor.fetchone()
        total_income = row[0]
        total_expense = row[1]
        
        cursor.execute(f"""
            SELECT category, SUM(amount) as cat_amount
            FROM transactions
            WHERE chat_id = ? AND type = 'expense' AND {date_filter}
            GROUP BY category
            ORDER BY cat_amount DESC
        """, (target_chat,))
        expense_by_cat = cursor.fetchall()

        cursor.execute(f"""
            SELECT category, SUM(amount) as cat_amount
            FROM transactions
            WHERE chat_id = ? AND type = 'income' AND {date_filter}
            GROUP BY category
            ORDER BY cat_amount DESC
        """, (target_chat,))
        income_by_cat = cursor.fetchall()
        
        return {
            "income": total_income,
            "expense": total_expense,
            "balance": total_income - total_expense,
            "expense_by_cat": expense_by_cat,
            "income_by_cat": income_by_cat
        }


def get_recent_transactions(user_id: int, limit: int = 7, chat_id: Optional[int] = None) -> List[Dict]:
    """Oxirgi tranzaksiyalar ro'yxatini olish"""
    target_chat = chat_id if chat_id is not None else user_id
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, type, amount, category, comment, datetime(created_at, 'localtime')
            FROM transactions
            WHERE chat_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (target_chat, limit))
        
        rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r[0],
                "type": r[1],
                "amount": r[2],
                "category": r[3],
                "comment": r[4],
                "date": r[5]
            })
        return result


def delete_last_transaction(user_id: int, chat_id: Optional[int] = None) -> Optional[Dict]:
    """Eng oxirgi kiritilgan tranzaksiyani bekor qilish / o'chirish"""
    target_chat = chat_id if chat_id is not None else user_id
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, type, amount, category
            FROM transactions
            WHERE chat_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (target_chat,))
        row = cursor.fetchone()
        
        if not row:
            return None
            
        trans_id, trans_type, amount, category = row
        cursor.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
        conn.commit()
        
        return {
            "id": trans_id,
            "type": trans_type,
            "amount": amount,
            "category": category
        }


def clear_all_transactions(user_id: int, chat_id: Optional[int] = None):
    """Barcha yozuvlarni tozalash"""
    target_chat = chat_id if chat_id is not None else user_id
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE chat_id = ?", (target_chat,))
        conn.commit()


# ==================== GURUH UCHUN MAXSUS FUNKSIYALAR ====================

def get_group_total_expense(chat_id: int) -> float:
    """Guruhning jami barcha davrlardagi umumiy harajatini olish"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE chat_id = ? AND type = 'expense'
        """, (chat_id,))
        row = cursor.fetchone()
        return row[0] if row else 0.0


def get_group_today_expense(chat_id: int) -> float:
    """Guruhning bugungi umumiy harajatini olish"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE chat_id = ? AND type = 'expense'
              AND date(created_at, 'localtime') = date('now', 'localtime')
        """, (chat_id,))
        row = cursor.fetchone()
        return row[0] if row else 0.0


def get_group_stats(chat_id: int, period: str = "all") -> Dict:
    """Guruh statistikasi: umumiy harajat, bugungi, oylik va kim qancha sarflagani"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if period == "today":
            date_filter = "date(t.created_at, 'localtime') = date('now', 'localtime')"
        elif period == "month":
            date_filter = "strftime('%Y-%m', t.created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')"
        else:
            date_filter = "1=1"
            
        # Jami xarajat shu davr uchun
        cursor.execute(f"""
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions t
            WHERE t.chat_id = ? AND t.type = 'expense' AND {date_filter}
        """, (chat_id,))
        total_expense = cursor.fetchone()[0]

        # Bugungi xarajat
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE chat_id = ? AND type = 'expense' 
              AND date(created_at, 'localtime') = date('now', 'localtime')
        """, (chat_id,))
        today_expense = cursor.fetchone()[0]

        # Oylik xarajat
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE chat_id = ? AND type = 'expense' 
              AND strftime('%Y-%m', created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')
        """, (chat_id,))
        month_expense = cursor.fetchone()[0]
        
        # Foydalanuvchilar bo'yicha taqsimot (kim qancha kiritgani)
        cursor.execute(f"""
            SELECT 
                COALESCE(u.full_name, 'Foydalanuvchi'),
                u.username,
                SUM(t.amount) AS user_amount,
                t.user_id
            FROM transactions t
            LEFT JOIN users u ON t.user_id = u.user_id
            WHERE t.chat_id = ? AND t.type = 'expense' AND {date_filter}
            GROUP BY t.user_id
            ORDER BY user_amount DESC
        """, (chat_id,))
        user_breakdown = cursor.fetchall()
        
        # Toifalar kesimida taqsimot
        cursor.execute(f"""
            SELECT t.category, SUM(t.amount) as cat_amount
            FROM transactions t
            WHERE t.chat_id = ? AND t.type = 'expense' AND {date_filter}
            GROUP BY t.category
            ORDER BY cat_amount DESC
        """, (chat_id,))
        category_breakdown = cursor.fetchall()
        
        return {
            "total_expense": total_expense,
            "today_expense": today_expense,
            "month_expense": month_expense,
            "user_breakdown": user_breakdown,
            "category_breakdown": category_breakdown
        }


def get_group_recent_transactions(chat_id: int, limit: int = 7) -> List[Dict]:
    """Guruhdagi oxirgi kiritilgan xarajatlar ro'yxati"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                t.id, t.type, t.amount, t.category, t.comment, 
                datetime(t.created_at, 'localtime'),
                COALESCE(u.full_name, 'Foydalanuvchi'), u.username, t.user_id
            FROM transactions t
            LEFT JOIN users u ON t.user_id = u.user_id
            WHERE t.chat_id = ? AND t.type = 'expense'
            ORDER BY t.id DESC
            LIMIT ?
        """, (chat_id, limit))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r[0],
                "type": r[1],
                "amount": r[2],
                "category": r[3],
                "comment": r[4],
                "date": r[5],
                "full_name": r[6],
                "username": r[7],
                "user_id": r[8]
            })
        return result


def delete_last_group_transaction(chat_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
    """Guruhdagi oxirgi xarajatni bekor qilish (user_id ko'rsatilsa faqat shu odamnikini)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("""
                SELECT t.id, t.type, t.amount, t.category, t.comment, COALESCE(u.full_name, 'Foydalanuvchi')
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.user_id
                WHERE t.chat_id = ? AND t.user_id = ? AND t.type = 'expense'
                ORDER BY t.id DESC
                LIMIT 1
            """, (chat_id, user_id))
        else:
            cursor.execute("""
                SELECT t.id, t.type, t.amount, t.category, t.comment, COALESCE(u.full_name, 'Foydalanuvchi')
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.user_id
                WHERE t.chat_id = ? AND t.type = 'expense'
                ORDER BY t.id DESC
                LIMIT 1
            """, (chat_id,))
            
        row = cursor.fetchone()
        if not row:
            return None
            
        trans_id, trans_type, amount, category, comment, full_name = row
        cursor.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
        conn.commit()
        return {
            "id": trans_id,
            "type": trans_type,
            "amount": amount,
            "category": category,
            "comment": comment,
            "full_name": full_name
        }


def clear_group_transactions(chat_id: int):
    """Guruhdagi barcha xarajatlarni tozalash"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE chat_id = ?", (chat_id,))
        conn.commit()
