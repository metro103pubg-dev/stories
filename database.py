import aiosqlite
import time
import os

DATA_DIR = "/app/data" if os.path.exists("/app/data") else "."
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "bot_database.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Пользователи
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                coins INTEGER DEFAULT 0,
                vip_until INTEGER DEFAULT 0,
                referrer_id INTEGER DEFAULT NULL,
                last_story_id INTEGER DEFAULT NULL,
                last_chapter_num TEXT DEFAULT '1',
                last_active INTEGER DEFAULT 0,
                created_at INTEGER
            )
        """)

        # 2. Жанры
        await db.execute("""
            CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        default_genres = [
            ('🔪 Хоррор & Мистика',),
            ('🕵️ Детектив & Триллер',),
            ('💔 Драма & Жизнь',),
            ('🌲 Выживание & Sci-Fi',)
        ]
        await db.executemany("INSERT OR IGNORE INTO genres (name) VALUES (?)", default_genres)

        # 3. Настройки
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        default_settings = [
            ('timer_hours', '3'),
            ('ref_coins', '20'),
            ('coin_pack_price', '99'),
            ('welcome_msg', 'Добро пожаловать в мир захватывающих историй! 📖')
        ]
        await db.executemany("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", default_settings)

        # 4. Истории
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                genre TEXT DEFAULT '🔪 Хоррор & Мистика',
                description TEXT,
                full_price INTEGER DEFAULT 149,
                rating_sum INTEGER DEFAULT 5,
                rating_count INTEGER DEFAULT 1
            )
        """)

        # 5. Главы с поддержкой буквенных номеров (например: 5а, 5б)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_id INTEGER,
                chapter_num TEXT,
                branch TEXT DEFAULT 'Основная',
                title TEXT,
                content TEXT,
                photo_attachment TEXT DEFAULT NULL,
                audio_attachment TEXT DEFAULT NULL,
                price_coins INTEGER DEFAULT 15,
                is_free INTEGER DEFAULT 0,
                is_ending INTEGER DEFAULT 0,
                ending_title TEXT DEFAULT NULL,
                next_chapter TEXT DEFAULT NULL,
                FOREIGN KEY (story_id) REFERENCES stories(id)
            )
        """)

        # 6. Развилки
        await db.execute("""
            CREATE TABLE IF NOT EXISTS choices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_id INTEGER,
                from_chapter TEXT,
                to_chapter TEXT,
                choice_text TEXT,
                is_vip_only INTEGER DEFAULT 0,
                price_coins INTEGER DEFAULT 0
            )
        """)

        # 7. Покупки и таймеры
        await db.execute("CREATE TABLE IF NOT EXISTS purchases (user_id INTEGER, story_id INTEGER, chapter_num TEXT, PRIMARY KEY (user_id, story_id, chapter_num))")
        await db.execute("CREATE TABLE IF NOT EXISTS chapter_timers (user_id INTEGER, story_id INTEGER, chapter_num TEXT, unlock_at INTEGER, PRIMARY KEY (user_id, story_id, chapter_num))")

        # ========== НОВЫЕ ТАБЛИЦЫ ДЛЯ ДОЖИМОВ ==========
        
        # 8. События удержания пользователей (retention)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS retention_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                story_id INTEGER,
                chapter_num TEXT,
                event_type TEXT,
                triggered_at INTEGER,
                notified_at INTEGER DEFAULT NULL,
                converted INTEGER DEFAULT 0,
                UNIQUE(user_id, story_id, chapter_num, event_type)
            )
        """)

        # 9. Настройки дожимов (админ может менять)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS retention_settings (
                trigger_name TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 1,
                frequency_hours INTEGER,
                last_updated INTEGER
            )
        """)

        # 10. История отправленных пушей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS push_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT,
                message_text TEXT,
                sent_at INTEGER,
                opened INTEGER DEFAULT 0,
                converted INTEGER DEFAULT 0
            )
        """)

        # 11. Промокоды и скидки
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                discount_percent INTEGER,
                user_id INTEGER,
                created_at INTEGER,
                expires_at INTEGER,
                used_count INTEGER DEFAULT 0,
                max_uses INTEGER DEFAULT 1
            )
        """)

        # ========== НОВЫЕ ТАБЛИЦЫ ДЛЯ АНАЛИТИКИ ==========

        # 12. Аналитика событий
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT,
                story_id INTEGER,
                chapter_num TEXT,
                source TEXT,
                event_time INTEGER,
                session_id TEXT
            )
        """)

        # 13. Источники трафика сессий
        await db.execute("""
            CREATE TABLE IF NOT EXISTS session_sources (
                user_id INTEGER PRIMARY KEY,
                source TEXT,
                ref_param TEXT,
                first_visit INTEGER
            )
        """)

        # 14. Платежи (для отслеживания LTV)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                story_id INTEGER,
                amount REAL,
                status TEXT,
                payment_method TEXT,
                created_at INTEGER
            )
        """)

        # 15. Когортный анализ
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cohort_data (
                user_id INTEGER PRIMARY KEY,
                signup_date TEXT,
                first_channel TEXT,
                lifetime_revenue REAL DEFAULT 0,
                total_purchases INTEGER DEFAULT 0,
                last_active INTEGER,
                churn_date TEXT DEFAULT NULL
            )
        """)

        # ========== НОВЫЕ ТАБЛИЦЫ ДЛЯ АДМИН-ПАНЕЛИ ==========

        # 16. Лог действий администраторов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_actions_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action TEXT,
                user_id INTEGER DEFAULT NULL,
                story_id INTEGER DEFAULT NULL,
                affected_users INTEGER DEFAULT NULL,
                timestamp INTEGER
            )
        """)

        # 17. Кампании рассылок
        await db.execute("""
            CREATE TABLE IF NOT EXISTS campaigns_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT UNIQUE,
                story_id INTEGER,
                admin_id INTEGER,
                campaign_type TEXT,
                sent INTEGER,
                converted INTEGER,
                timestamp INTEGER
            )
        """)

        # 18. AB-тесты
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ab_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id TEXT,
                user_id INTEGER,
                variant TEXT,
                created_at INTEGER,
                metric_value REAL,
                UNIQUE(test_id, user_id)
            )
        """)

        await db.commit()

# --- Хелперы ---

async def get_or_create_user(user_id: int, referrer_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            user = await cur.fetchone()
            if not user:
                now = int(time.time())
                await db.execute(
                    "INSERT INTO users (user_id, referrer_id, created_at, last_active) VALUES (?, ?, ?, ?)",
                    (user_id, referrer_id, now, now)
                )
                await db.commit()
                return {"user_id": user_id, "coins": 0, "vip_until": 0, "referrer_id": referrer_id, "last_story_id": None, "last_chapter_num": "1"}
            return {
                "user_id": user[0], "coins": user[1], "vip_until": user[2],
                "referrer_id": user[3], "last_story_id": user[4], "last_chapter_num": str(user[5] or "1")
            }

async def update_bookmark(user_id: int, story_id: int, chapter_num: str):
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_story_id = ?, last_chapter_num = ?, last_active = ? WHERE user_id = ?",
            (story_id, str(chapter_num), now, user_id)
        )
        await db.commit()

async def get_chapter_choices(story_id: int, chapter_num: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, to_chapter, choice_text, is_vip_only, price_coins FROM choices WHERE story_id = ? AND from_chapter = ?",
            (story_id, str(chapter_num))
        ) as cur:
            return await cur.fetchall()

# Админ-функции
async def admin_give_coins(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def admin_give_vip(user_id: int, days: int = 30):
    now = int(time.time())
    vip_time = now + (days * 86400)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET vip_until = ? WHERE user_id = ?", (vip_time, user_id))
        await db.commit()

async def admin_give_story(user_id: int, story_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO purchases (user_id, story_id, chapter_num) VALUES (?, ?, '0')", (user_id, story_id))
        await db.commit()

async def admin_give_chapter(user_id: int, story_id: int, chapter_num: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO purchases (user_id, story_id, chapter_num) VALUES (?, ?, ?)", (user_id, story_id, str(chapter_num)))
        await db.commit()

async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as c:
            row = await c.fetchone()
            return row[0] if row else default

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        await db.commit()

async def get_all_genres():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, name FROM genres") as c:
            return await c.fetchall()

async def add_genre_db(name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (name.strip(),))
        await db.commit()

async def delete_genre_db(genre_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM genres WHERE id = ?", (genre_id,))
        await db.commit()

# --- Новые хелперы для логирования ---

async def log_admin_action(admin_id: int, action: str, user_id: int = None, story_id: int = None, affected_users: int = None):
    """Логировать действие администратора"""
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO admin_actions_log (admin_id, action, user_id, story_id, affected_users, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (admin_id, action, user_id, story_id, affected_users, now)
        )
        await db.commit()

async def log_analytics_event(user_id: int, event_type: str, story_id: int = None, chapter_num: str = None, source: str = None, session_id: str = None):
    """Логировать аналитическое событие"""
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO analytics_events (user_id, event_type, story_id, chapter_num, source, event_time, session_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, event_type, story_id, chapter_num, source, now, session_id)
        )
        await db.commit()

async def log_push_sent(user_id: int, event_type: str, message_text: str):
    """Логировать отправленный пуш"""
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO push_history (user_id, event_type, message_text, sent_at) VALUES (?, ?, ?, ?)",
            (user_id, event_type, message_text, now)
        )
        await db.commit()
