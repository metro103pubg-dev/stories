from vkbottle.bot import BotLabeler, Message
from database import DB_PATH, get_or_create_user, update_bookmark, get_setting
from keyboards import reading_kb, hybrid_paywall_kb, coin_shop_kb, main_menu_kb
from config import GROUP_ID, VK_TOKEN
from lava_pay import create_lava_payment
from vkbottle import API
import aiosqlite
import time
import json

reader_labeler = BotLabeler()
api = API(token=VK_TOKEN)

async def check_access(user_id: int, story_id: int, chapter_num: int, is_free: int) -> bool:
    if is_free == 1:
        return True
    try:
        if await api.donut.is_don(owner_id=-GROUP_ID, user_id=user_id):
            return True
    except Exception:
        pass

    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM purchases WHERE user_id = ? AND story_id = ? AND (chapter_num = 0 OR chapter_num = ?)",
            (user_id, story_id, chapter_num)
        ) as p_cur:
            if await p_cur.fetchone():
                return True

        async with db.execute(
            "SELECT unlock_at FROM chapter_timers WHERE user_id = ? AND story_id = ? AND chapter_num = ?",
            (user_id, story_id, chapter_num)
        ) as t_cur:
            timer = await t_cur.fetchone()
            if timer and timer[0] <= now:
                return True
    return False

# Магазин монет (витрина пакетов)
@reader_labeler.message(payload={"cmd": "shop_coins"})
async def shop_coins_handler(message: Message):
    user_id = message.from_id
    url_50 = await create_lava_payment(user_id, 50, "coins", 1, coins=50)
    url_120 = await create_lava_payment(user_id, 99, "coins", 2, coins=120)
    url_300 = await create_lava_payment(user_id, 199, "coins", 3, coins=300)

    await message.answer(
        "🪙 Пополнение баланса монет через СБП:\n\n"
        "Выберите удобный пакет:",
        keyboard=coin_shop_kb(url_50, url_120, url_300)
    )

# Открытие главы за монеты в 1 клик
@reader_labeler.message(payload_map={"cmd": "unlock_coin", "story_id": int, "chapter": int})
async def unlock_with_coins(message: Message):
    payload = json.loads(message.payload)
    story_id = payload["story_id"]
    chapter_num = payload["chapter"]
    user_id = message.from_id

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,)) as u_cur:
            user_coins = (await u_cur.fetchone())[0]

        async with db.execute("SELECT price_coins FROM chapters WHERE story_id = ? AND chapter_num = ?", (story_id, chapter_num)) as c_cur:
            row = await c_cur.fetchone()
            cost = row[0] if row else 15

        if user_coins >= cost:
            # Списываем монеты и выдаем главу
            await db.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (cost, user_id))
            await db.execute("INSERT OR IGNORE INTO purchases (user_id, story_id, chapter_num) VALUES (?, ?, ?)", (user_id, story_id, chapter_num))
            await db.commit()

            await message.answer(f"🎉 Списано {cost} монет. Приятного чтения!")
            await read_chapter_handler(message)
        else:
            await message.answer("❌ Недостаточно монет на балансе!", keyboard=main_menu_kb())

# Чтение главы
@reader_labeler.message(payload_map={"cmd": "read", "story_id": int, "chapter": int})
async def read_chapter_handler(message: Message):
    payload = json.loads(message.payload)
    story_id = payload["story_id"]
    chapter_num = payload["chapter"]
    user_id = message.from_id

    user = await get_or_create_user(user_id)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT title, content, photo_attachment, audio_attachment, price_coins, is_free FROM chapters WHERE story_id = ? AND chapter_num = ?",
            (story_id, chapter_num)
        ) as cur:
            chapter = await cur.fetchone()

        async with db.execute("SELECT title, full_price FROM stories WHERE id = ?", (story_id,)) as s_cur:
            story = await s_cur.fetchone()

    if not chapter or not story:
        await message.answer("🎉 Вы дочитали до конца вышедших глав!", keyboard=main_menu_kb())
        return

    ch_title, content, photo, audio, price_coins, is_free = chapter
    story_title, full_price = story

    if await check_access(user_id, story_id, chapter_num, is_free):
        await update_bookmark(user_id, story_id, chapter_num)
        next_kb = reading_kb(story_id, chapter_num + 1)
        text = f"📖 {story_title} — Глава {chapter_num}: {ch_title}\n\n{content}"

        attachments = []
        if photo: attachments.append(photo)
        if audio: attachments.append(audio)

        if attachments:
            await message.answer(text, attachment=",".join(attachments), keyboard=next_kb)
        else:
            await message.answer(text, keyboard=next_kb)
    else:
        # Пейволл с балансом монет
        story_pay_url = await create_lava_payment(user_id, full_price, "story", story_id)
        cost_coins = price_coins or 15

        await message.answer(
            f"🔒 Доступ к главе {chapter_num} закрыт.\n\n"
            f"💰 Стоимость: {cost_coins} монет\n"
            f"🪙 У вас на балансе: {user['coins']} монет\n\n"
            f"Выберите удобный вариант:",
            keyboard=hybrid_paywall_kb(user['coins'], story_id, chapter_num, cost_coins, full_price, story_pay_url)
        )

# Закладка (Продолжить чтение)
@reader_labeler.message(payload={"cmd": "continue"})
async def continue_reading(message: Message):
    user = await get_or_create_user(message.from_id)
    story_id = user["last_story_id"]
    chapter_num = user["last_chapter_num"] or 1

    if not story_id:
        await message.answer("Вы еще не начали читать ни одну историю! Выберите в каталоге 👇", keyboard=main_menu_kb())
        return

    fake_payload = json.dumps({"cmd": "read", "story_id": story_id, "chapter": chapter_num})
    message.payload = fake_payload
    await read_chapter_handler(message)

# Таймер ожидания
@reader_labeler.message(payload_map={"cmd": "start_timer", "story_id": int, "chapter": int})
async def set_timer_handler(message: Message):
    payload = json.loads(message.payload)
    story_id = payload["story_id"]
    chapter_num = payload["chapter"]
    user_id = message.from_id

    hours = int(await get_setting("timer_hours", "3"))
    unlock_at = int(time.time()) + (hours * 3600)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO chapter_timers (user_id, story_id, chapter_num, unlock_at) VALUES (?, ?, ?, ?)",
            (user_id, story_id, chapter_num, unlock_at)
        )
        await db.commit()

    await message.answer(f"⏳ Таймер запущен! Глава {chapter_num} откроется бесплатно через {hours} ч.", keyboard=main_menu_kb())
