from vkbottle.bot import BotLabeler, Message
from database import DB_PATH, get_or_create_user, update_bookmark, get_setting
from keyboards import reading_kb, hybrid_paywall_kb, main_menu_kb
from config import GROUP_ID, VK_TOKEN
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

# Чтение главы
@reader_labeler.message(payload_map={"cmd": "read", "story_id": int, "chapter": int})
async def read_chapter_handler(message: Message):
    payload = json.loads(message.payload)
    story_id = payload["story_id"]
    chapter_num = payload["chapter"]
    user_id = message.from_id

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT title, content, photo_attachment, audio_attachment, price_coins, is_free FROM chapters WHERE story_id = ? AND chapter_num = ?",
            (story_id, chapter_num)
        ) as cur:
            chapter = await cur.fetchone()

        async with db.execute("SELECT title, full_price FROM stories WHERE id = ?", (story_id,)) as s_cur:
            story = await s_cur.fetchone()

    if not chapter or not story:
        await message.answer("🎉 Новые главы этой истории скоро выйдут!", keyboard=main_menu_kb())
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
        await message.answer(
            f"🔒 Доступ к главе {chapter_num} закрыт.\n\n"
            f"Выберите способ разблокировки:",
            keyboard=hybrid_paywall_kb(user_id, story_id, chapter_num, price_coins, full_price)
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
