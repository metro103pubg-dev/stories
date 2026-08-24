import asyncio
import json
from aiohttp import web
from vkbottle.bot import Bot, Message
from vkbottle import API
from config import VK_TOKEN, PORT
from database import init_db, get_or_create_user, DB_PATH
from keyboards import main_menu_kb
import aiosqlite

from handlers.catalog import catalog_labeler
from handlers.reader import reader_labeler, read_chapter_handler
from handlers.profile import profile_labeler
from handlers.admin import admin_labeler

bot = Bot(token=VK_TOKEN)
api = API(token=VK_TOKEN)

# Подключаем модули
bot.labeler.load(catalog_labeler)
bot.labeler.load(reader_labeler)
bot.labeler.load(profile_labeler)
bot.labeler.load(admin_labeler)

# Главное меню и Deep-link
@bot.on.message(text=["Начать", "начать", "Start", "start", "Меню", "меню"])
async def start_handler(message: Message):
    user_id = message.from_id
    ref_payload = None

    if message.payload:
        try:
            payload_data = json.loads(message.payload)
            ref_payload = payload_data.get("ref")
        except Exception:
            pass

    # Реферальная ссылка друга
    if ref_payload and ref_payload.startswith("ref_"):
        try:
            ref_id = int(ref_payload.replace("ref_", ""))
            await get_or_create_user(user_id, referrer_id=ref_id)
        except Exception:
            await get_or_create_user(user_id)
    # Ссылка на историю из рекламы
    elif ref_payload and ref_payload.startswith("story_"):
        parts = ref_payload.split("_")
        if len(parts) >= 3:
            s_id = int(parts[1])
            ch_num = int(parts[2])
            await get_or_create_user(user_id)
            message.payload = json.dumps({"cmd": "read", "story_id": s_id, "chapter": ch_num})
            await read_chapter_handler(message)
            return
    else:
        await get_or_create_user(user_id)

    await message.answer(
        "👋 Добро пожаловать в мир захватывающих интерактивных историй!\n\n"
        "Выбирай жанр в каталоге или жми «Продолжить чтение» 👇",
        keyboard=main_menu_kb()
    )

# Вебхук для приема оплат от Lava.top
async def lava_webhook_handler(request: web.Request):
    try:
        data = await request.json()
        if data.get("status") == "success":
            custom_data = data.get("custom_fields", "")
            if custom_data:
                # user_id:item_type:item_id:coins
                parts = custom_data.split(":")
                user_id = int(parts[0])
                item_type = parts[1]
                item_id = int(parts[2])
                coins = int(parts[3]) if len(parts) > 3 else 0

                async with aiosqlite.connect(DB_PATH) as db:
                    if item_type == "coins":
                        # Начисляем купленные монеты
                        await db.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (coins, user_id))
                        msg = f"🎉 Оплата получена! На ваш баланс начислено +{coins} 🪙 монет!"
                    elif item_type == "story":
                        # Доступ ко всей книге
                        await db.execute("INSERT OR IGNORE INTO purchases (user_id, story_id, chapter_num) VALUES (?, ?, 0)", (user_id, item_id))
                        msg = "🎉 Оплата получена! Вся книга разблокирована навсегда!"
                    await db.commit()

                # Уведомляем в ВК
                await api.messages.send(user_id=user_id, random_id=0, message=msg)
    except Exception as e:
        print(f"Ошибка вебхука Lava: {e}")

    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_post("/payment/lava", lava_webhook_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ Веб-сервер приема платежей запущен на порту {PORT}")

# Главный запуск
async def main():
    await init_db()
    await start_web_server()
    print("✅ База данных готова. Бот запущен!")
    await bot.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
