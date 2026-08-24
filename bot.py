import asyncio
import json
from vkbottle.bot import Bot, Message
from config import VK_TOKEN
from database import init_db, get_or_create_user
from keyboards import main_menu_kb

from handlers.catalog import catalog_labeler
from handlers.reader import reader_labeler, read_chapter_handler
from handlers.profile import profile_labeler
from handlers.admin import admin_labeler

bot = Bot(token=VK_TOKEN)

# Подключаем модули
bot.labeler.load(catalog_labeler)
bot.labeler.load(reader_labeler)
bot.labeler.load(profile_labeler)
bot.labeler.load(admin_labeler)

# Главный обработчик команды "Начать" + Deep-link из рекламы
@bot.on.message(text=["Начать", "начать", "Start", "start", "Меню", "меню"])
async def start_handler(message: Message):
    user_id = message.from_id
    ref_payload = None

    # Проверяем переход по реф-ссылке рекламы (?ref=story_1_2)
    if message.payload:
        try:
            payload_data = json.loads(message.payload)
            ref_payload = payload_data.get("ref")
        except Exception:
            pass

    if ref_payload and ref_payload.startswith("story_"):
        parts = ref_payload.split("_")
        if len(parts) >= 3:
            s_id = int(parts[1])
            ch_num = int(parts[2])
            await get_or_create_user(user_id)
            message.payload = json.dumps({"cmd": "read", "story_id": s_id, "chapter": ch_num})
            await read_chapter_handler(message)
            return

    await get_or_create_user(user_id)
    await message.answer(
        "👋 Добро пожаловать в мир захватывающих интерактивных историй!\n\n"
        "Выбирай жанр в каталоге или жми «Продолжить чтение» 👇",
        keyboard=main_menu_kb()
    )

# Функция правильного асинхронного запуска
async def main():
    await init_db()
    print("✅ База данных готова. Бот запущен!")
    await bot.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
