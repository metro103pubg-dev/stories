import asyncio
import json
from aiohttp import web
from vkbottle.bot import Bot, Message
from vkbottle import API
from config import VK_TOKEN, PORT, ADMIN_IDS
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

# Главный обработчик на любые сообщения (с выводом в лог)
@bot.on.message()
async def default_handler(message: Message):
    user_id = message.from_id
    print(f"📩 [ВК СООБЩЕНИЕ] Получено: '{message.text}' от ID: {user_id}")

    # Если админ пишет команду админки
    if message.text in ["/admin", "админка", "Админка"]:
        if user_id in ADMIN_IDS:
            from handlers.admin import admin_root_kb
            await message.answer("🛠 Панель управления ботом:", keyboard=admin_root_kb())
            return
        else:
            await message.answer(f"❌ Доступ закрыт. Твой ID: {user_id}")
            return

    # Проверяем Deep-link рефералок / историй
    ref_payload = None
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

# Вебхук для приема оплат от Lava.top
async def lava_webhook_handler(request: web.Request):
    try:
        data = await request.json()
        if data.get("status") == "success":
            custom_data = data.get("custom_fields", "")
            if custom_data:
                parts = custom_data.split(":")
                user_id = int(parts[0])
                item_type = parts[1]
                item_id = int(parts[2])
                coins = int(parts[3]) if len(parts) > 3 else 0

                async with aiosqlite.connect(DB_PATH) as db:
                    if item_type == "coins":
                        await db.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (coins, user_id))
                        msg = f"🎉 Оплата получена! На ваш баланс начислено +{coins} 🪙 монет!"
                    elif item_type == "story":
                        await db.execute("INSERT OR IGNORE INTO purchases (user_id, story_id, chapter_num) VALUES (?, ?, 0)", (user_id, item_id))
                        msg = "🎉 Оплата получена! Вся книга разблокирована навсегда!"
                    await db.commit()

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
    print(f"✅ Веб-сервер запущен на порту {PORT}")

async def main():
    await init_db()
    await start_web_server()
    print("🚀 [БОТ ГОТОВ] Ожидаем сообщения из ВК...")
    await bot.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
