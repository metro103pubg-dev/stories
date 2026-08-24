from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text, BaseStateGroup
import aiosqlite
from database import DB_PATH, get_all_genres
from keyboards import main_menu_kb

catalog_labeler = BotLabeler()

class SearchState(BaseStateGroup):
    QUERY = 0

# Каталог (выбор жанра)
@catalog_labeler.message(text="📚 Каталог историй")
@catalog_labeler.message(payload={"cmd": "catalog"})
async def catalog_genres(message: Message):
    genres = await get_all_genres()
    kb = Keyboard(inline=True)
    for g_id, g_name in genres:
        kb.add(Text(g_name, payload={"cmd": "view_genre", "genre": g_name}))
        kb.row()
    await message.answer("📚 Выберите жанр историй:", keyboard=kb)

# Истории по жанру (Отображаем ID перед названием)
@catalog_labeler.message(payload_map={"cmd": "view_genre", "genre": str})
async def view_genre_stories(message: Message):
    import json
    genre = json.loads(message.payload)["genre"]

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, full_price FROM stories WHERE genre = ?", (genre,)) as cur:
            stories = await cur.fetchall()

    if not stories:
        await message.answer(f"В жанре «{genre}» пока нет историй. Скоро добавим!", keyboard=main_menu_kb())
        return

    kb = Keyboard(inline=True)
    for s_id, s_title, s_price in stories:
        # Отображаем ID и тип (Бесплатно / Цена)
        badge = f"[ID: {s_id}] 🎁 [БЕСПЛАТНО]" if s_price == 0 else f"[ID: {s_id}] 📖 [{s_price} ₽]"
        kb.add(Text(f"{badge} {s_title}", payload={"cmd": "story_card", "story_id": s_id}))
        kb.row()

    await message.answer(f"Список историй в жанре «{genre}»:", keyboard=kb)

# Карточка истории
@catalog_labeler.message(payload_map={"cmd": "story_card", "story_id": int})
async def story_card(message: Message):
    import json
    story_id = json.loads(message.payload)["story_id"]

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT title, description, full_price, genre FROM stories WHERE id = ?", (story_id,)) as cur:
            story = await cur.fetchone()

    if not story:
        await message.answer("История не найдена.")
        return

    title, desc, full_price, genre = story
    price_label = "🎁 БЕСПЛАТНО (Лид-магнит)" if full_price == 0 else f"{full_price} ₽"

    kb = Keyboard(inline=True)
    kb.add(Text("Начать читать ➡️", payload={"cmd": "read", "story_id": story_id, "chapter": 1}), color=KeyboardButtonColor.POSITIVE)

    await message.answer(
        f"📖 [ID: {story_id}] *{title}*\n"
        f"🏷️ Жанр: {genre}\n"
        f"💰 Стоимость: {price_label}\n\n"
        f"{desc}",
        keyboard=kb
    )

# Поиск по названию
@catalog_labeler.message(text="🔍 Поиск")
@catalog_labeler.message(payload={"cmd": "search"})
async def search_start(message: Message):
    await catalog_labeler.state_dispenser.set(message.peer_id, SearchState.QUERY)
    await message.answer("🔍 Введите название или слово из названия истории:")

@catalog_labeler.message(state=SearchState.QUERY)
async def search_process(message: Message):
    query = message.text
    await catalog_labeler.state_dispenser.delete(message.peer_id)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title, full_price FROM stories WHERE title LIKE ?", (f"%{query}%",)) as cur:
            results = await cur.fetchall()

    if not results:
        await message.answer("😔 Ничего не найдено. Попробуйте другое слово.", keyboard=main_menu_kb())
        return

    kb = Keyboard(inline=True)
    for s_id, s_title, s_price in results:
        badge = f"[ID: {s_id}] 🎁" if s_price == 0 else f"[ID: {s_id}] 📖"
        kb.add(Text(f"{badge} {s_title}", payload={"cmd": "story_card", "story_id": s_id}))
        kb.row()

    await message.answer(f"Найдено историй: {len(results)}", keyboard=kb)
