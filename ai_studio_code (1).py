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
                last_chapter_num INTEGER DEFAULT 1,
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

        # 5. Главы
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_id INTEGER,
                chapter_num INTEGER,
                title TEXT,
                content TEXT,
                photo_attachment TEXT DEFAULT NULL,
                audio_attachment TEXT DEFAULT NULL,
                price_coins INTEGER DEFAULT 15,
                is_free INTEGER DEFAULT 0,
                is_ending INTEGER DEFAULT 0,
                ending_title TEXT DEFAULT NULL,
                FOREIGN KEY (story_id) REFERENCES stories(id)
            )
        """)

        # 6. Развилки
        await db.execute("""
            CREATE TABLE IF NOT EXISTS choices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_id INTEGER,
                from_chapter INTEGER,
                to_chapter INTEGER,
                choice_text TEXT,
                is_vip_only INTEGER DEFAULT 0,
                price_coins INTEGER DEFAULT 0
            )
        """)

        # 7. Покупки и таймеры
        await db.execute("CREATE TABLE IF NOT EXISTS purchases (user_id INTEGER, story_id INTEGER, chapter_num INTEGER, PRIMARY KEY (user_id, story_id, chapter_num))")
        await db.execute("CREATE TABLE IF NOT EXISTS chapter_timers (user_id INTEGER, story_id INTEGER, chapter_num INTEGER, unlock_at INTEGER, PRIMARY KEY (user_id, story_id, chapter_num))")

        # Автоматическая миграция (добавление новых колонок в старую базу)
        try:
            await db.execute("ALTER TABLE chapters ADD COLUMN is_ending INTEGER DEFAULT 0")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE chapters ADD COLUMN ending_title TEXT DEFAULT NULL")
        except Exception:
            pass

        await db.commit()

# --- Вспомогательные функции ---

async def get_or_create_user(user_id: int, referrer_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            user = await cur.fetchone()
            if not user:
                now = int(time.time())
                await db.execute(
                    "INSERT INTO users (user_id, referrer_id, created_at) VALUES (?, ?, ?)",
                    (user_id, referrer_id, now)
                )
                await db.commit()
                return {"user_id": user_id, "coins": 0, "vip_until": 0, "referrer_id": referrer_id, "last_story_id": None, "last_chapter_num": 1}
            return {
                "user_id": user[0], "coins": user[1], "vip_until": user[2],
                "referrer_id": user[3], "last_story_id": user[4], "last_chapter_num": user[5]
            }

async def update_bookmark(user_id: int, story_id: int, chapter_num: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_story_id = ?, last_chapter_num = ? WHERE user_id = ?",
            (story_id, chapter_num, user_id)
        )
        await db.commit()

async def get_chapter_choices(story_id: int, chapter_num: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, to_chapter, choice_text, is_vip_only, price_coins FROM choices WHERE story_id = ? AND from_chapter = ?",
            (story_id, chapter_num)
        ) as cur:
            return await cur.fetchall()

# Админ-функции выдачи читателям
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
        await db.execute("INSERT OR IGNORE INTO purchases (user_id, story_id, chapter_num) VALUES (?, ?, 0)", (user_id, story_id))
        await db.commit()

async def admin_give_chapter(user_id: int, story_id: int, chapter_num: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO purchases (user_id, story_id, chapter_num) VALUES (?, ?, ?)", (user_id, story_id, chapter_num))
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