from vkbottle.bot import BotLabeler, Message
from database import DB_PATH, get_or_create_user, update_bookmark, get_setting, get_chapter_choices
from keyboards import reading_kb, choices_kb, ending_kb, hybrid_paywall_kb, coin_shop_kb, main_menu_kb
from config import GROUP_ID, VK_TOKEN
from vkbottle import API
import aiosqlite
import time
import json

reader_labeler = BotLabeler()
api = API(token=VK_TOKEN)

async def check_access(user_id: int, story_id: int, chapter_num: int, is_free: int, full_price: int) -> bool:
    if full_price == 0 or is_free == 1:
        return True

    # Проверка VK Donut
    try:
        if await api.donut.is_don(owner_id=-GROUP_ID, user_id=user_id):
            return True
    except Exception:
        pass

    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверка VIP из БД (ручная выдача)
        async with db.execute("SELECT vip_until FROM users WHERE user_id = ?", (user_id,)) as u_cur:
            u_row = await u_cur.fetchone()
            if u_row and u_row[0] > now:
                return True

        # Проверка покупок
        async with db.execute(
            "SELECT 1 FROM purchases WHERE user_id = ? AND story_id = ? AND (chapter_num = 0 OR chapter_num = ?)",
            (user_id, story_id, chapter_num)
        ) as p_cur:
            if await p_cur.fetchone():
                return True

        # Проверка таймера
        async with db.execute(
            "SELECT unlock_at FROM chapter_timers WHERE user_id = ? AND story_id = ? AND chapter_num = ?",
            (user_id, story_id, chapter_num)
        ) as t_cur:
            timer = await t_cur.fetchone()
            if timer and timer[0] <= now:
                return True
    return False

# Витрина магазина
@reader_labeler.message(text=["🪙 Купить монеты", "🪙 Купить монеты / VIP"])
@reader_labeler.message(payload={"cmd": "shop_coins"})
async def shop_coins_handler(message: Message):
    user_id = message.from_id
    user = await get_or_create_user(user_id)

    is_don = False
    try:
        is_don = bool(await api.donut.is_don(owner_id=-GROUP_ID, user_id=user_id))
    except Exception: pass
    if user["vip_until"] > int(time.time()):
        is_don = True

    vip_status = "👑 Активен (VK Donut / VIP)" if is_don else "Не активен ❌"

    text = (
        f"🛒 Магазин историй и монет:\n\n"
        f"🪙 Твой баланс: {user['coins']} монет\n"
        f"👑 VIP-статус: {vip_status}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👑 VIP-ПОДПИСКА (VK Donut):\n"
        f"• Безлимитный доступ ко ВСЕМ историям и развилкам\n"
        f"• Без таймеров и списания монет\n"
        f"• Стоимость: 199 ₽ / месяц\n\n"
        f"🪙 ПАКЕТЫ МОНЕТ (Оплата по СБП):\n"
        f"• Для поглавной покупки и премиум-выборов\n\n"
        f"👇 Выбирай подходящий вариант:"
    )
    await message.answer(text, keyboard=coin_shop_kb())

# Переход по интерактивному выбору
@reader_labeler.message(payload_map={"cmd": "choose", "story_id": int, "to_ch": int, "choice_id": int})
async def choose_branch_handler(message: Message):
    payload = json.loads(message.payload)
    story_id = payload["story_id"]
    to_chapter = payload["to_ch"]
    choice_id = payload["choice_id"]
    user_id = message.from_id

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_vip_only, price_coins FROM choices WHERE id = ?", (choice_id,)) as cur:
            choice_data = await cur.fetchone()

    if choice_data:
        is_vip, price = choice_data
        user = await get_or_create_user(user_id)
        now = int(time.time())

        # Проверка VIP-выбора
        if is_vip:
            is_don = False
            try:
                is_don = bool(await api.donut.is_don(owner_id=-GROUP_ID, user_id=user_id))
            except Exception: pass
            if user["vip_until"] > now: is_don = True

            if not is_don:
                await message.answer(
                    "👑 Этот выбор доступен только для VIP-читателей (VK Donut)!\n\n"
                    "Оформите подписку, чтобы открыть секретную сюжетную линию 👇",
                    keyboard=coin_shop_kb()
                )
                return

        # Проверка платного выбора
        if price > 0:
            if user["coins"] < price:
                await message.answer(f"🪙 Для этого выбора требуется {price} монет. Пополните баланс:", keyboard=coin_shop_kb())
                return
            else:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (price, user_id))
                    await db.commit()
                await message.answer(f"🪙 Списано {price} монет за премиум-выбор!")

    message.payload = json.dumps({"cmd": "read", "story_id": story_id, "chapter": to_chapter})
    await read_chapter_handler(message)

# Перезапуск истории
@reader_labeler.message(payload_map={"cmd": "restart_story", "story_id": int})
async def restart_story_handler(message: Message):
    payload = json.loads(message.payload)
    story_id = payload["story_id"]
    await update_bookmark(message.from_id, story_id, 1)
    message.payload = json.dumps({"cmd": "read", "story_id": story_id, "chapter": 1})
    await read_chapter_handler(message)

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
            "SELECT title, content, photo_attachment, audio_attachment, price_coins, is_free, is_ending, ending_title FROM chapters WHERE story_id = ? AND chapter_num = ?",
            (story_id, chapter_num)
        ) as cur:
            chapter = await cur.fetchone()

        async with db.execute("SELECT title, full_price FROM stories WHERE id = ?", (story_id,)) as s_cur:
            story = await s_cur.fetchone()

    if not chapter or not story:
        await message.answer("🎉 Вы дочитали до конца вышедших глав!", keyboard=main_menu_kb())
        return

    ch_title, content, photo, audio, price_coins, is_free, is_ending, ending_title = chapter
    story_title, full_price = story

    if await check_access(user_id, story_id, chapter_num, is_free, full_price):
        await update_bookmark(user_id, story_id, chapter_num)
        text = f"📖 {story_title} — Глава {chapter_num}: {ch_title}\n\n{content}"

        attachments = []
        if photo: attachments.append(photo)
        if audio: attachments.append(audio)

        # 1. Если это ФИНАЛ (Концовка)
        if is_ending == 1:
            end_name = ending_title or "Завершение истории"
            text += f"\n\n━━━━━━━━━━━━━━━━━━\n🏆 ФИНАЛ: {end_name}"
            kb = ending_kb(story_id)
            if attachments:
                await message.answer(text, attachment=",".join(attachments), keyboard=kb)
            else:
                await message.answer(text, keyboard=kb)
            return

        # 2. Проверяем развилки
        choices = await get_chapter_choices(story_id, chapter_num)
        if choices:
            text += "\n\n👉 Сделайте ваш выбор:"
            kb = choices_kb(story_id, choices)
        else:
            kb = reading_kb(story_id, chapter_num + 1)

        if attachments:
            await message.answer(text, attachment=",".join(attachments), keyboard=kb)
        else:
            await message.answer(text, keyboard=kb)
    else:
        # Пейволл
        cost_coins = price_coins or 15
        await message.answer(
            f"🔒 Доступ к главе {chapter_num} закрыт.\n\n"
            f"💰 Стоимость: {cost_coins} монет\n"
            f"🪙 У вас на балансе: {user['coins']} монет\n\n"
            f"Выберите удобный вариант продолжения:",
            keyboard=hybrid_paywall_kb(user['coins'], story_id, chapter_num, cost_coins, full_price)
        )

# Покупка главы за монеты
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
            await db.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (cost, user_id))
            await db.execute("INSERT OR IGNORE INTO purchases (user_id, story_id, chapter_num) VALUES (?, ?, ?)", (user_id, story_id, chapter_num))
            await db.commit()

            await message.answer(f"🎉 Списано {cost} монет. Приятного чтения!")
            await read_chapter_handler(message)
        else:
            await message.answer("❌ Недостаточно монет на балансе!", keyboard=main_menu_kb())

# Закладка
@reader_labeler.message(text="📖 Продолжить чтение")
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

# Таймер
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
