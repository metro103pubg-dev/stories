from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text, BaseStateGroup
import aiosqlite
from config import ADMIN_IDS, VK_TOKEN, GROUP_ID
from vkbottle import API
from database import DB_PATH, get_all_genres, add_genre_db, delete_genre_db, get_setting, set_setting
from keyboards import main_menu_kb

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
    BROADCAST = 13
    GEN_LINK = 14

def admin_root_kb():
    kb = Keyboard(inline=False)
    kb.add(Text("➕ Создать историю", payload={"adm": "add_story"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("📝 Добавить главу", payload={"adm": "add_chapter"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🔗 Ссылка для рекламы", payload={"adm": "gen_link"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("🏷️ Жанры", payload={"adm": "menu_genres"}))
    kb.row()
    kb.add(Text("⚙️ Экономика", payload={"adm": "menu_settings"}))
    kb.add(Text("📊 Статистика", payload={"adm": "stats"}))
    kb.row()
    kb.add(Text("📢 Рассылка", payload={"adm": "broadcast"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("🔙 Главное меню", payload={"cmd": "main_menu"}))
    return kb

@admin_labeler.message(text=["/admin", "админка", "Админка"])
async def admin_panel(message: Message):
    if message.from_id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    await message.answer("🛠 Панель управления ботом:", keyboard=admin_root_kb())

# Выход в главное меню
@admin_labeler.message(payload={"cmd": "main_menu"})
async def back_to_main_user_menu(message: Message):
    await message.answer("Вы вернулись в главное меню читателя 👇", keyboard=main_menu_kb())

# --- ⚙️ РАЗДЕЛ: ЭКОНОМИКА И НАСТРОЙКИ ---
@admin_labeler.message(payload={"adm": "menu_settings"})
async def admin_settings_view(message: Message):
    if message.from_id not in ADMIN_IDS: return
    t_hours = await get_setting("timer_hours", "3")
    r_coins = await get_setting("ref_coins", "20")
    
    kb = Keyboard(inline=True)
    kb.add(Text("⏳ Изменить таймер", payload={"adm": "set_timer"}))
    kb.row()
    kb.add(Text("🎁 Изменить награду за друга", payload={"adm": "set_ref"}))

    await message.answer(
        f"⚙️ Текущие настройки экономики:\n\n"
        f"⏳ Бесплатный таймер: {t_hours} ч.\n"
        f"🎁 Награда за реферала: {r_coins} монет",
        keyboard=kb
    )

@admin_labeler.message(payload={"adm": "set_timer"})
async def set_timer_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.SET_TIMER)
    await message.answer("Сколько часов читатель должен ждать бесплатную главу? (введите число, например: 2):")

@admin_labeler.message(state=AdminState.SET_TIMER)
async def set_timer_2(message: Message):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число!")
        return
    await set_setting("timer_hours", message.text)
    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer(f"✅ Время таймера изменено на {message.text} ч.!", keyboard=admin_root_kb())

@admin_labeler.message(payload={"adm": "set_ref"})
async def set_ref_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.SET_REF)
    await message.answer("Сколько монет начислять за каждого приглашенного друга? (введите число, например: 20):")

@admin_labeler.message(state=AdminState.SET_REF)
async def set_ref_2(message: Message):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число!")
        return
    await set_setting("ref_coins", message.text)
    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer(f"✅ Награда за реферала изменена на {message.text} монет!", keyboard=admin_root_kb())

# --- 🏷️ РАЗДЕЛ: ЖАНРЫ ---
@admin_labeler.message(payload={"adm": "menu_genres"})
async def admin_genres_view(message: Message):
    if message.from_id not in ADMIN_IDS: return
    genres = await get_all_genres()
    text = "🏷️ Список активных жанров:\n\n"
    for g_id, g_name in genres:
        text += f"• [{g_id}] {g_name}\n"
    
    kb = Keyboard(inline=True)
    kb.add(Text("➕ Добавить жанр", payload={"adm": "add_genre"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🗑️ Удалить жанр", payload={"adm": "del_genre"}), color=KeyboardButtonColor.NEGATIVE)
    
    await message.answer(text, keyboard=kb)

@admin_labeler.message(payload={"adm": "add_genre"})
async def add_genre_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.ADD_GENRE)
    await message.answer("Введите название нового жанра (например: 🛸 Фантастика):")

@admin_labeler.message(state=AdminState.ADD_GENRE)
async def add_genre_2(message: Message):
    await add_genre_db(message.text)
    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer(f"✅ Жанр «{message.text}» успешно добавлен!", keyboard=admin_root_kb())

@admin_labeler.message(payload={"adm": "del_genre"})
async def del_genre_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.DEL_GENRE)
    await message.answer("Введите ID жанра (цифру в скобках), который хотите удалить:")

@admin_labeler.message(state=AdminState.DEL_GENRE)
async def del_genre_2(message: Message):
    if not message.text.isdigit():
        await message.answer("Введите число (ID жанра)!")
        return
    await delete_genre_db(int(message.text))
    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer("🗑️ Жанр успешно удален!", keyboard=admin_root_kb())

# --- 🔗 ГЕНЕРАТОР ССЫЛОК ДЛЯ РЕКЛАМЫ ---
@admin_labeler.message(payload={"adm": "gen_link"})
async def gen_link_step1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.GEN_LINK)
    await message.answer(
        "🔗 Введите через пробел: ID истории и номер главы\n"
        "Например: 1 2 (означает История #1, Глава #2):"
    )

@admin_labeler.message(state=AdminState.GEN_LINK)
async def gen_link_step2(message: Message):
    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("Пожалуйста, введите два числа через пробел (например: 1 2):")
        return

    s_id = parts[0]
    ch_num = parts[1]
    await admin_labeler.state_dispenser.delete(message.peer_id)

    link = f"https://vk.me/club{GROUP_ID}?ref=story_{s_id}_{ch_num}"

    text = (
        f"🔗 Ваша готовая ссылка для рекламного поста:\n\n"
        f"{link}\n\n"
        f"📋 Вставьте её в пост в ВК, ОК или Дзен.\n"
        f"Читатель перейдет и сразу начнет читать Главу {ch_num} истории #{s_id}!"
    )
    await message.answer(text, keyboard=admin_root_kb())

# --- 📊 СТАТИСТИКА ---
@admin_labeler.message(payload={"adm": "stats"})
async def stats(message: Message):
    if message.from_id not in ADMIN_IDS: return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as u: total_u = (await u.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM stories") as s: total_s = (await s.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM purchases") as p: total_p = (await p.fetchone())[0]
    await message.answer(f"📊 Статистика:\n\n👤 Читателей в базе: {total_u}\n📚 Историй: {total_s}\n💰 Покупок: {total_p}", keyboard=admin_root_kb())

# --- ➕ СОЗДАНИЕ ИСТОРИИ ---
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
    await message.answer("Выберите жанр истории из списка:", keyboard=kb)

@admin_labeler.message(state=AdminState.STORY_GENRE)
async def add_story_3(message: Message):
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.STORY_DESC, title=state.payload["title"], genre=message.text)
    await message.answer("Введите краткое описание сюжета (аннотацию):")

@admin_labeler.message(state=AdminState.STORY_DESC)
async def add_story_4(message: Message):
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(
        message.peer_id, AdminState.STORY_PRICE,
        title=state.payload["title"], genre=state.payload["genre"], desc=message.text
    )
    await message.answer("Укажите цену покупки всей истории целиком в рублях (например: 149):")

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

# --- 📝 ДОБАВЛЕНИЕ ГЛАВЫ ---
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

# --- 📢 РАССЫЛКА ---
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
