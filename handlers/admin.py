from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text, BaseStateGroup
import aiosqlite
from config import ADMIN_IDS, VK_TOKEN
from vkbottle import API
from database import DB_PATH, get_all_genres, add_genre_db, delete_genre_db, get_setting, set_setting

admin_labeler = BotLabeler()
api = API(token=VK_TOKEN)

class AdminState(BaseStateGroup):
    ADD_GENRE = 0
    DEL_GENRE = 1
    SET_TIMER = 2
    SET_REF = 3
    STORY_TITLE = 4
    STORY_GENRE = 5
    STORY_DESC = 6
    STORY_PRICE = 7
    CH_STORY_ID = 8
    CH_NUM = 9
    CH_TITLE = 10
    CH_TEXT = 11
    CH_FREE = 12
    CH_PRICE = 13
    BROADCAST = 14

def admin_root_kb():
    kb = Keyboard(inline=False)
    kb.add(Text("➕ Создать историю", payload={"adm": "add_story"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("📝 Добавить главу", payload={"adm": "add_chapter"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🏷️ Жанры", payload={"adm": "menu_genres"}))
    kb.add(Text("⚙️ Экономика", payload={"adm": "menu_settings"}))
    kb.row()
    kb.add(Text("📢 Рассылка", payload={"adm": "broadcast"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("📊 Статистика", payload={"adm": "stats"}))
    kb.row()
    kb.add(Text("🔙 Главное меню", payload={"cmd": "main_menu"}))
    return kb

@admin_labeler.message(text=["/admin", "админка", "Админка"])
async def admin_panel(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await message.answer("🛠 Панель управления ботом:", keyboard=admin_root_kb())

# Статистика
@admin_labeler.message(payload={"adm": "stats"})
async def stats(message: Message):
    if message.from_id not in ADMIN_IDS: return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as u: total_u = (await u.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM stories") as s: total_s = (await s.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM purchases") as p: total_p = (await p.fetchone())[0]
    await message.answer(f"📊 Читателей: {total_u}\n📚 Историй: {total_s}\n💰 Покупок: {total_p}")

# Добавление истории
@admin_labeler.message(payload={"adm": "add_story"})
async def add_story_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.STORY_TITLE)
    await message.answer("Введите название новой истории:")

@admin_labeler.message(state=AdminState.STORY_TITLE)
async def add_story_2(message: Message):
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.STORY_GENRE, title=message.text)
    genres = await get_all_genres()
    kb = Keyboard(inline=True)
    for _, g_name in genres:
        kb.add(Text(g_name)); kb.row()
    await message.answer("Выберите жанр:", keyboard=kb)

@admin_labeler.message(state=AdminState.STORY_GENRE)
async def add_story_3(message: Message):
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.STORY_DESC, title=state.payload["title"], genre=message.text)
    await message.answer("Введите описание истории (аннотацию):")

@admin_labeler.message(state=AdminState.STORY_DESC)
async def add_story_4(message: Message):
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(
        message.peer_id, AdminState.STORY_PRICE,
        title=state.payload["title"], genre=state.payload["genre"], desc=message.text
    )
    await message.answer("Введите цену покупки всей истории целиком в рублях (например: 149):")

@admin_labeler.message(state=AdminState.STORY_PRICE)
async def add_story_5(message: Message):
    if not message.text.isdigit():
        await message.answer("Введите число!")
        return
    price = int(message.text)
    state = await admin_labeler.state_dispenser.get(message.peer_id)

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO stories (title, genre, description, full_price) VALUES (?, ?, ?, ?)",
            (state.payload["title"], state.payload["genre"], state.payload["desc"], price)
        )
        s_id = cur.lastrowid
        await db.commit()

    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer(f"✅ История «{state.payload['title']}» успешно создана!\nID истории: {s_id}", keyboard=admin_root_kb())

# Добавление главы
@admin_labeler.message(payload={"adm": "add_chapter"})
async def add_ch_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.CH_STORY_ID)
    await message.answer("Введите ID истории (цифру), к которой добавляем главу:")

@admin_labeler.message(state=AdminState.CH_STORY_ID)
async def add_ch_2(message: Message):
    if not message.text.isdigit():
        await message.answer("Введите число!")
        return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.CH_NUM, story_id=int(message.text))
    await message.answer("Введите номер главы (например: 1 или 2):")

@admin_labeler.message(state=AdminState.CH_NUM)
async def add_ch_3(message: Message):
    if not message.text.isdigit():
        await message.answer("Введите число!")
        return
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.CH_TITLE, story_id=state.payload["story_id"], ch_num=int(message.text))
    await message.answer("Введите название главы:")

@admin_labeler.message(state=AdminState.CH_TITLE)
async def add_ch_4(message: Message):
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(
        message.peer_id, AdminState.CH_TEXT,
        story_id=state.payload["story_id"], ch_num=state.payload["ch_num"], ch_title=message.text
    )
    await message.answer("Отправьте текст главы (можно прикрепить фото):")

@admin_labeler.message(state=AdminState.CH_TEXT)
async def add_ch_5(message: Message):
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    photo_att = None
    if message.attachments:
        for a in message.attachments:
            if a.photo:
                photo_att = f"photo{a.photo.owner_id}_{a.photo.id}"
                break

    await admin_labeler.state_dispenser.set(
        message.peer_id, AdminState.CH_FREE,
        story_id=state.payload["story_id"], ch_num=state.payload["ch_num"],
        ch_title=state.payload["ch_title"], text=message.text, photo=photo_att
    )
    kb = Keyboard(inline=True)
    kb.add(Text("Да (Бесплатная)", payload={"free": 1}))
    kb.add(Text("Нет (Платная)", payload={"free": 0}))
    await message.answer("Сделать главу бесплатной?", keyboard=kb)

@admin_labeler.message(state=AdminState.CH_FREE)
async def add_ch_6(message: Message):
    import json
    is_free = 1 if (message.payload and json.loads(message.payload).get("free") == 1) else 0
    state = await admin_labeler.state_dispenser.get(message.peer_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO chapters (story_id, chapter_num, title, content, photo_attachment, is_free) VALUES (?, ?, ?, ?, ?, ?)",
            (state.payload["story_id"], state.payload["ch_num"], state.payload["ch_title"], state.payload["text"], state.payload["photo"], is_free)
        )
        await db.commit()

    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer(f"✅ Глава {state.payload['ch_num']} успешно сохранена!", keyboard=admin_root_kb())

# Рассылка
@admin_labeler.message(payload={"adm": "broadcast"})
async def broadcast_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.BROADCAST)
    await message.answer("Введите текст сообщения для рассылки всем читателям:")

@admin_labeler.message(state=AdminState.BROADCAST)
async def broadcast_2(message: Message):
    text_to_send = message.text
    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer("⏳ Рассылка отправляется...")

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            users = await cur.fetchall()

    for u in users:
        try:
            await api.messages.send(user_id=u[0], message=text_to_send, random_id=0)
        except Exception:
            pass
    await message.answer("✅ Рассылка завершена!", keyboard=admin_root_kb())
