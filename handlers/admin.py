from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text, BaseStateGroup
import aiosqlite
import random
import asyncio
import time
from config import ADMIN_IDS, VK_TOKEN, GROUP_ID
from vkbottle import API
from database import (
    DB_PATH, get_all_genres, add_genre_db, delete_genre_db, get_setting, set_setting,
    get_or_create_user, admin_give_coins, admin_give_vip, admin_give_story, admin_give_chapter
)
from keyboards import main_menu_kb

admin_labeler = BotLabeler()
api = API(token=VK_TOKEN)

class AdminState(BaseStateGroup):
    ADD_GENRE = "add_genre"
    DEL_GENRE = "del_genre"
    SET_TIMER = "set_timer"
    SET_REF = "set_ref"
    STORY_TITLE = "story_title"
    STORY_GENRE = "story_genre"
    STORY_DESC = "story_desc"
    STORY_PRICE = "story_price"
    CH_STORY_ID = "ch_story_id"
    CH_NUM = "ch_num"
    CH_TITLE = "ch_title"
    CH_TEXT = "ch_text"
    CH_FREE = "ch_free"
    CH_IS_END = "ch_is_end"
    CH_END_TITLE = "ch_end_title"
    BROADCAST = "broadcast"
    GEN_LINK = "gen_link"
    DEL_STORY = "del_story"
    DEL_CHAPTER = "del_chapter"
    # Развилки
    CHOICE_STORY = "choice_story"
    CHOICE_FROM = "choice_from"
    CHOICE_TO = "choice_to"
    CHOICE_TEXT = "choice_text"
    CHOICE_VIP = "choice_vip"
    # Управление читателями
    USER_LOOKUP = "user_lookup"
    USER_GIVE_COINS = "user_give_coins"
    USER_GIVE_STORY = "user_give_story"
    USER_GIVE_CH = "user_give_ch"

def admin_root_kb():
    kb = Keyboard(inline=False)
    kb.add(Text("➕ Создать историю", payload={"adm": "add_story"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("📝 Добавить главу", payload={"adm": "add_chapter"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("🔀 Добавить развилку", payload={"adm": "add_choice"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("👤 Управление читателем", payload={"adm": "user_mgr"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("🔗 Ссылка для рекламы", payload={"adm": "gen_link"}))
    kb.add(Text("🏷️ Жанры", payload={"adm": "menu_genres"}))
    kb.row()
    kb.add(Text("🗑️ Удалить историю", payload={"adm": "del_story"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("🗑️ Удалить главу", payload={"adm": "del_chapter"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("⚙️ Экономика", payload={"adm": "menu_settings"}))
    kb.add(Text("📊 Статистика", payload={"adm": "stats"}))
    kb.row()
    kb.add(Text("📢 Рассылка", payload={"adm": "broadcast"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("🔙 Главное меню", payload={"cmd": "main_menu"}))
    return kb

def cancel_kb():
    """Кнопка отмены текущего действия"""
    kb = Keyboard(inline=False)
    kb.add(Text("❌ Отмена", payload={"adm": "cancel"}), color=KeyboardButtonColor.NEGATIVE)
    return kb

@admin_labeler.message(text=["/admin", "админка", "Админка"])
async def admin_panel(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await get_or_create_user(message.from_id)
    await message.answer("🛠 Панель управления ботом:", keyboard=admin_root_kb())

# Универсальная отмена любого действия
@admin_labeler.message(text=["❌ Отмена", "Отмена", "отмена", "/cancel"])
@admin_labeler.message(payload={"adm": "cancel"})
async def admin_cancel_handler(message: Message):
    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer("❌ Действие отменено. Возврат в панель администратора:", keyboard=admin_root_kb())

# Выход в главное меню
@admin_labeler.message(text="🔙 Главное меню")
@admin_labeler.message(payload={"cmd": "main_menu"})
async def back_to_main_user_menu(message: Message):
    await message.answer("Вы вернулись в главное меню читателя 👇", keyboard=main_menu_kb())

# ==================== 🔀 ДОБАВЛЕНИЕ РАЗВИЛКИ ====================
@admin_labeler.message(text="🔀 Добавить развилку")
@admin_labeler.message(payload={"adm": "add_choice"})
async def choice_step1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.CHOICE_STORY)
    await message.answer("🔀 Введите ID истории (число), в которую добавляем развилку:", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.CHOICE_STORY)
async def choice_step2(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    if not message.text.isdigit():
        await message.answer("Введите число!", keyboard=cancel_kb())
        return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.CHOICE_FROM, s_id=int(message.text))
    await message.answer("В какой главе показывать кнопку выбора? (номер главы, например: 2):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.CHOICE_FROM)
async def choice_step3(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    if not message.text.isdigit():
        await message.answer("Введите число!", keyboard=cancel_kb())
        return
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.CHOICE_TO, s_id=state.payload["s_id"], from_ch=int(message.text))
    await message.answer("На какую главу должен перевести этот выбор? (номер целевой главы, например: 3):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.CHOICE_TO)
async def choice_step4(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    if not message.text.isdigit():
        await message.answer("Введите число!", keyboard=cancel_kb())
        return
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(
        message.peer_id, AdminState.CHOICE_TEXT,
        s_id=state.payload["s_id"], from_ch=state.payload["from_ch"], to_ch=int(message.text)
    )
    await message.answer("Введите текст кнопки выбора (например: 🚪 Открыть дверь подвала):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.CHOICE_TEXT)
async def choice_step5(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(
        message.peer_id, AdminState.CHOICE_VIP,
        s_id=state.payload["s_id"], from_ch=state.payload["from_ch"], to_ch=state.payload["to_ch"], c_text=message.text
    )
    kb = Keyboard(inline=True)
    kb.add(Text("Обычный (Бесплатный)", payload={"vip": 0}))
    kb.add(Text("👑 Только для VIP (Donut)", payload={"vip": 1}))
    await message.answer("Этот выбор доступен всем или только для VIP-подписчиков?", keyboard=kb)

@admin_labeler.message(state=AdminState.CHOICE_VIP)
async def choice_step6(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    import json
    is_vip = 0
    if message.payload:
        try: is_vip = json.loads(message.payload).get("vip", 0)
        except Exception: pass
    elif "VIP" in message.text:
        is_vip = 1

    state = await admin_labeler.state_dispenser.get(message.peer_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO choices (story_id, from_chapter, to_chapter, choice_text, is_vip_only) VALUES (?, ?, ?, ?, ?)",
            (state.payload["s_id"], state.payload["from_ch"], state.payload["to_ch"], state.payload["c_text"], is_vip)
        )
        await db.commit()

    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer(f"✅ Развилка для главы {state.payload['from_ch']} успешно сохранена!", keyboard=admin_root_kb())

# ==================== 👤 УПРАВЛЕНИЕ ЧИТАТЕЛЕМ ====================
@admin_labeler.message(text="👤 Управление читателем")
@admin_labeler.message(payload={"adm": "user_mgr"})
async def user_mgr_step1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.USER_LOOKUP)
    await message.answer("👤 Введите цифровой VK ID читателя (например: 123456789):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.USER_LOOKUP)
async def user_mgr_card(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите корректный цифровой ID:", keyboard=cancel_kb())
        return

    target_id = int(message.text)
    user = await get_or_create_user(target_id)
    now = int(time.time())

    vip_str = "Не активен ❌"
    if user["vip_until"] > now:
        days_left = (user["vip_until"] - now) // 86400
        vip_str = f"Активен (осталось {days_left} дн.) 👑"

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM purchases WHERE user_id = ? AND chapter_num = 0", (target_id,)) as c1:
            stories_bought = (await c1.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM purchases WHERE user_id = ? AND chapter_num > 0", (target_id,)) as c2:
            chapters_bought = (await c2.fetchone())[0]

    text = (
        f"👤 Карточка читателя [ID: {target_id}]:\n\n"
        f"🪙 Баланс: {user['coins']} монет\n"
        f"👑 VIP-статус: {vip_str}\n"
        f"📚 Куплено историй целиком: {stories_bought}\n"
        f"📖 Куплено отдельных глав: {chapters_bought}\n\n"
        f"Выберите действие с читателем 👇"
    )

    kb = Keyboard(inline=True)
    kb.add(Text("🪙 Выдать монеты", payload={"act": "give_coins", "uid": target_id}))
    kb.add(Text("👑 Выдать VIP (30 дн)", payload={"act": "give_vip", "uid": target_id}))
    kb.row()
    kb.add(Text("📚 Выдать всю историю", payload={"act": "give_story", "uid": target_id}))
    kb.add(Text("📖 Выдать главу", payload={"act": "give_ch", "uid": target_id}))

    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer(text, keyboard=kb)

@admin_labeler.message(payload_map={"act": "give_coins", "uid": int})
async def act_give_coins(message: Message):
    import json
    uid = json.loads(message.payload)["uid"]
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.USER_GIVE_COINS, target_uid=uid)
    await message.answer(f"Сколько монет начислить пользователю {uid}? (введите число, например: 50):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.USER_GIVE_COINS)
async def act_give_coins_finish(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    if not message.text.isdigit():
        await message.answer("Введите число монет:", keyboard=cancel_kb())
        return
    coins = int(message.text)
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    uid = state.payload["target_uid"]

    await admin_give_coins(uid, coins)
    await admin_labeler.state_dispenser.delete(message.peer_id)

    try:
        await api.messages.send(user_id=uid, random_id=random.randint(100, 999999), message=f"🎁 Администратор начислил вам +{coins} 🪙 монет!")
    except Exception: pass

    await message.answer(f"✅ Успешно начислено {coins} монет читателю {uid}!", keyboard=admin_root_kb())

@admin_labeler.message(payload_map={"act": "give_vip", "uid": int})
async def act_give_vip_finish(message: Message):
    import json
    uid = json.loads(message.payload)["uid"]
    await admin_give_vip(uid, days=30)

    try:
        await api.messages.send(user_id=uid, random_id=random.randint(100, 999999), message="👑 Администратор активировал вам VIP-статус на 30 дней! Все книги открыты!")
    except Exception: pass

    await message.answer(f"✅ VIP-статус на 30 дней выдан читателю {uid}!", keyboard=admin_root_kb())

@admin_labeler.message(payload_map={"act": "give_story", "uid": int})
async def act_give_story(message: Message):
    import json
    uid = json.loads(message.payload)["uid"]
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.USER_GIVE_STORY, target_uid=uid)
    await message.answer(f"Введите ID истории, которую хотите открыть читателю {uid}:", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.USER_GIVE_STORY)
async def act_give_story_finish(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    if not message.text.isdigit():
        await message.answer("Введите ID истории (число):", keyboard=cancel_kb())
        return
    s_id = int(message.text)
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    uid = state.payload["target_uid"]

    await admin_give_story(uid, s_id)
    await admin_labeler.state_dispenser.delete(message.peer_id)

    try:
        await api.messages.send(user_id=uid, random_id=random.randint(100, 999999), message=f"🎁 Вам открыт полный доступ к истории #{s_id}!")
    except Exception: pass

    await message.answer(f"✅ Доступ ко всей истории #{s_id} выдан читателю {uid}!", keyboard=admin_root_kb())

@admin_labeler.message(payload_map={"act": "give_ch", "uid": int})
async def act_give_ch(message: Message):
    import json
    uid = json.loads(message.payload)["uid"]
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.USER_GIVE_CH, target_uid=uid)
    await message.answer(f"Введите через пробел: ID истории и номер главы для выдачи (например: 1 3):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.USER_GIVE_CH)
async def act_give_ch_finish(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("Введите два числа через пробел (например: 1 3):", keyboard=cancel_kb())
        return
    s_id = int(parts[0])
    ch_num = int(parts[1])
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    uid = state.payload["target_uid"]

    await admin_give_chapter(uid, s_id, ch_num)
    await admin_labeler.state_dispenser.delete(message.peer_id)

    try:
        await api.messages.send(user_id=uid, random_id=random.randint(100, 999999), message=f"🎁 Вам открыта Глава #{ch_num} истории #{s_id}!")
    except Exception: pass

    await message.answer(f"✅ Глава #{ch_num} истории #{s_id} успешно выдана читателю {uid}!", keyboard=admin_root_kb())

# ==================== 📝 СОЗДАНИЕ ГЛАВ И ИСТОРИЙ ====================

@admin_labeler.message(text="➕ Создать историю")
@admin_labeler.message(payload={"adm": "add_story"})
async def add_story_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.STORY_TITLE)
    await message.answer("Введите название новой истории:", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.STORY_TITLE)
async def add_story_2(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.STORY_GENRE, title=message.text)
    genres = await get_all_genres()
    kb = Keyboard(inline=True)
    for _, g_name in genres:
        kb.add(Text(g_name)); kb.row()
    await message.answer("Выберите жанр:", keyboard=kb)

@admin_labeler.message(state=AdminState.STORY_GENRE)
async def add_story_3(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.STORY_DESC, title=state.payload["title"], genre=message.text)
    await message.answer("Введите описание сюжета (аннотацию):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.STORY_DESC)
async def add_story_4(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(
        message.peer_id, AdminState.STORY_PRICE,
        title=state.payload["title"], genre=state.payload["genre"], desc=message.text
    )
    await message.answer("Укажите цену всей книги (или 0, если это бесплатный Лид-магнит):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.STORY_PRICE)
async def add_story_5(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    if not message.text.isdigit():
        await message.answer("Введите число!", keyboard=cancel_kb())
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
    await message.answer(f"✅ История [ID: {s_id}] «{state.payload['title']}» успешно создана!", keyboard=admin_root_kb())

# Добавление главы
@admin_labeler.message(text="📝 Добавить главу")
@admin_labeler.message(payload={"adm": "add_chapter"})
async def add_ch_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.CH_STORY_ID)
    await message.answer("Введите ID истории (цифру), к которой добавляем главу:", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.CH_STORY_ID)
async def add_ch_2(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    if not message.text.isdigit():
        await message.answer("Введите число!", keyboard=cancel_kb())
        return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.CH_NUM, story_id=int(message.text))
    await message.answer("Введите номер главы (например: 1, 2, 3):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.CH_NUM)
async def add_ch_3(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    if not message.text.isdigit():
        await message.answer("Введите число!", keyboard=cancel_kb())
        return
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.CH_TITLE, story_id=state.payload["story_id"], ch_num=int(message.text))
    await message.answer("Введите название главы:", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.CH_TITLE)
async def add_ch_4(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(
        message.peer_id, AdminState.CH_TEXT,
        story_id=state.payload["story_id"], ch_num=state.payload["ch_num"], ch_title=message.text
    )
    await message.answer("Отправьте текст главы (можно прикрепить фото):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.CH_TEXT)
async def add_ch_5(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
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
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    import json
    is_free = 1
    if message.payload:
        try: is_free = json.loads(message.payload).get("free", 1)
        except Exception: pass
    elif "Нет" in message.text:
        is_free = 0

    state = await admin_labeler.state_dispenser.get(message.peer_id)
    await admin_labeler.state_dispenser.set(
        message.peer_id, AdminState.CH_IS_END,
        story_id=state.payload["story_id"], ch_num=state.payload["ch_num"],
        ch_title=state.payload["ch_title"], text=state.payload["text"], photo=state.payload["photo"], is_free=is_free
    )
    kb = Keyboard(inline=True)
    kb.add(Text("Обычная глава", payload={"ending": 0}))
    kb.add(Text("🏆 Это Финал (Концовка)", payload={"ending": 1}))
    await message.answer("Эта глава является финалом (концовкой одной из веток)?", keyboard=kb)

@admin_labeler.message(state=AdminState.CH_IS_END)
async def add_ch_7(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    import json
    is_end = 0
    if message.payload:
        try: is_end = json.loads(message.payload).get("ending", 0)
        except Exception: pass
    elif "Финал" in message.text:
        is_end = 1

    state = await admin_labeler.state_dispenser.get(message.peer_id)

    if is_end == 1:
        await admin_labeler.state_dispenser.set(
            message.peer_id, AdminState.CH_END_TITLE,
            story_id=state.payload["story_id"], ch_num=state.payload["ch_num"],
            ch_title=state.payload["ch_title"], text=state.payload["text"],
            photo=state.payload["photo"], is_free=state.payload["is_free"], is_ending=1
        )
        await message.answer("Введите название этой концовки (например: Концовка 1 из 3: Трагический финал):", keyboard=cancel_kb())
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO chapters (story_id, chapter_num, title, content, photo_attachment, is_free, is_ending) VALUES (?, ?, ?, ?, ?, ?, 0)",
                (state.payload["story_id"], state.payload["ch_num"], state.payload["ch_title"], state.payload["text"], state.payload["photo"], state.payload["is_free"])
            )
            await db.commit()

        await admin_labeler.state_dispenser.delete(message.peer_id)
        await message.answer(f"✅ Глава {state.payload['ch_num']} успешно сохранена!", keyboard=admin_root_kb())

@admin_labeler.message(state=AdminState.CH_END_TITLE)
async def add_ch_8(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    state = await admin_labeler.state_dispenser.get(message.peer_id)
    end_title = message.text

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO chapters (story_id, chapter_num, title, content, photo_attachment, is_free, is_ending, ending_title) VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
            (state.payload["story_id"], state.payload["ch_num"], state.payload["ch_title"], state.payload["text"], state.payload["photo"], state.payload["is_free"], end_title)
        )
        await db.commit()

    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer(f"🏆 Финальная глава {state.payload['ch_num']} с концовкой «{end_title}» успешно сохранена!", keyboard=admin_root_kb())

# ==================== ОСТАЛЬНЫЕ КОМАНДЫ (Удаление, Статистика, Рассылка) ====================

@admin_labeler.message(text="🗑️ Удалить историю")
@admin_labeler.message(payload={"adm": "del_story"})
async def del_story_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, title FROM stories") as cur: stories = await cur.fetchall()
    if not stories:
        await message.answer("Список пуст.", keyboard=admin_root_kb())
        return
    text = "📚 Список историй:\n\n"
    for s_id, s_title in stories: text += f"• [ID: {s_id}] {s_title}\n"
    text += "\nВведите ID истории для удаления:"
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.DEL_STORY)
    await message.answer(text, keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.DEL_STORY)
async def del_story_2(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    if not message.text.isdigit(): return
    s_id = int(message.text)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM stories WHERE id = ?", (s_id,))
        await db.execute("DELETE FROM chapters WHERE story_id = ?", (s_id,))
        await db.execute("DELETE FROM choices WHERE story_id = ?", (s_id,))
        await db.commit()
    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer(f"🗑️ История #{s_id} удалена!", keyboard=admin_root_kb())

@admin_labeler.message(text="🗑️ Удалить главу")
@admin_labeler.message(payload={"adm": "del_chapter"})
async def del_ch_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.DEL_CHAPTER)
    await message.answer("Введите через пробел ID истории и номер главы для удаления (например: 1 2):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.DEL_CHAPTER)
async def del_ch_2(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit(): return
    s_id = int(parts[0])
    ch_num = int(parts[1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM chapters WHERE story_id = ? AND chapter_num = ?", (s_id, ch_num))
        await db.execute("DELETE FROM choices WHERE story_id = ? AND from_chapter = ?", (s_id, ch_num))
        await db.commit()
    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer(f"🗑️ Глава #{ch_num} истории #{s_id} удалена!", keyboard=admin_root_kb())

@admin_labeler.message(text="🔗 Ссылка для рекламы")
@admin_labeler.message(payload={"adm": "gen_link"})
async def gen_link_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.GEN_LINK)
    await message.answer("Введите через пробел ID истории и номер главы (например: 1 2):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.GEN_LINK)
async def gen_link_2(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit(): return
    s_id, ch_num = parts[0], parts[1]
    await admin_labeler.state_dispenser.delete(message.peer_id)
    link = f"https://vk.me/club{GROUP_ID}?ref=story_{s_id}_{ch_num}"
    await message.answer(f"🔗 Готовая ссылка:\n\n{link}", keyboard=admin_root_kb())

@admin_labeler.message(text="📊 Статистика")
@admin_labeler.message(payload={"adm": "stats"})
async def stats(message: Message):
    if message.from_id not in ADMIN_IDS: return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as u: total_u = (await u.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM stories") as s: total_s = (await s.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM purchases") as p: total_p = (await p.fetchone())[0]
    await message.answer(f"📊 Статистика:\n\n👤 Читателей: {total_u}\n📚 Историй: {total_s}\n💰 Покупок: {total_p}", keyboard=admin_root_kb())

@admin_labeler.message(text="📢 Рассылка")
@admin_labeler.message(payload={"adm": "broadcast"})
async def broadcast_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.BROADCAST)
    await message.answer("Введите текст рассылки (можно прикрепить фото):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.BROADCAST)
async def broadcast_2(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    text_to_send = message.text
    photo_att = None
    if message.attachments:
        for a in message.attachments:
            if a.photo:
                photo_att = f"photo{a.photo.owner_id}_{a.photo.id}"
                break
    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer("⏳ Рассылка отправляется...")
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur: users = await cur.fetchall()
    total, success, errors = len(users), 0, 0
    for u in users:
        try:
            r_id = random.randint(100000, 999999999)
            if photo_att:
                await api.messages.send(user_id=u[0], message=text_to_send, attachment=photo_att, random_id=r_id)
            else:
                await api.messages.send(user_id=u[0], message=text_to_send, random_id=r_id)
            success += 1
            await asyncio.sleep(0.05)
        except Exception: errors += 1
    await message.answer(f"✅ Рассылка завершена!\n👥 В базе: {total}\n Доставлено: {success}\n❌ Ошибок: {errors}", keyboard=admin_root_kb())

# Жанры и Экономика
@admin_labeler.message(text="🏷️ Жанры")
@admin_labeler.message(payload={"adm": "menu_genres"})
async def admin_genres_view(message: Message):
    if message.from_id not in ADMIN_IDS: return
    genres = await get_all_genres()
    text = "🏷️ Список активных жанров:\n\n"
    for g_id, g_name in genres: text += f"• [{g_id}] {g_name}\n"
    kb = Keyboard(inline=True)
    kb.add(Text("➕ Добавить жанр", payload={"adm": "add_genre"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("🗑️ Удалить жанр", payload={"adm": "del_genre"}), color=KeyboardButtonColor.NEGATIVE)
    await message.answer(text, keyboard=kb)

@admin_labeler.message(text="➕ Добавить жанр")
@admin_labeler.message(payload={"adm": "add_genre"})
async def add_genre_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.ADD_GENRE)
    await message.answer("Введите название нового жанра:", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.ADD_GENRE)
async def add_genre_2(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    await add_genre_db(message.text)
    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer(f"✅ Жанр «{message.text}» добавлен!", keyboard=admin_root_kb())

@admin_labeler.message(text="🗑️ Удалить жанр")
@admin_labeler.message(payload={"adm": "del_genre"})
async def del_genre_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.DEL_GENRE)
    await message.answer("Введите ID жанра для удаления:", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.DEL_GENRE)
async def del_genre_2(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    if not message.text.isdigit(): return
    await delete_genre_db(int(message.text))
    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer("🗑️ Жанр удален!", keyboard=admin_root_kb())

@admin_labeler.message(text="⚙️ Экономика")
@admin_labeler.message(payload={"adm": "menu_settings"})
async def admin_settings_view(message: Message):
    if message.from_id not in ADMIN_IDS: return
    t_hours = await get_setting("timer_hours", "3")
    r_coins = await get_setting("ref_coins", "20")
    kb = Keyboard(inline=True)
    kb.add(Text("⏳ Изменить таймер", payload={"adm": "set_timer"}))
    kb.row()
    kb.add(Text("🎁 Изменить награду за друга", payload={"adm": "set_ref"}))
    await message.answer(f"⚙️ Экономика:\n\n⏳ Таймер: {t_hours} ч.\n🎁 За друга: {r_coins} монет", keyboard=kb)

@admin_labeler.message(text="⏳ Изменить таймер")
@admin_labeler.message(payload={"adm": "set_timer"})
async def set_timer_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.SET_TIMER)
    await message.answer("Сколько часов ждать бесплатную главу? (число):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.SET_TIMER)
async def set_timer_2(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    if not message.text.isdigit(): return
    await set_setting("timer_hours", message.text)
    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer(f"✅ Таймер изменен на {message.text} ч.!", keyboard=admin_root_kb())

@admin_labeler.message(text="🎁 Изменить награду за друга")
@admin_labeler.message(payload={"adm": "set_ref"})
async def set_ref_1(message: Message):
    if message.from_id not in ADMIN_IDS: return
    await admin_labeler.state_dispenser.set(message.peer_id, AdminState.SET_REF)
    await message.answer("Сколько монет давать за друга? (число):", keyboard=cancel_kb())

@admin_labeler.message(state=AdminState.SET_REF)
async def set_ref_2(message: Message):
    if message.text == "❌ Отмена": return await admin_cancel_handler(message)
    if not message.text.isdigit(): return
    await set_setting("ref_coins", message.text)
    await admin_labeler.state_dispenser.delete(message.peer_id)
    await message.answer(f"✅ Награда изменена на {message.text} монет!", keyboard=admin_root_kb())
