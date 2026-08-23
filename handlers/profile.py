from vkbottle.bot import BotLabeler, Message
import aiosqlite
import time
from database import DB_PATH, get_or_create_user, get_setting
from config import GROUP_ID

profile_labeler = BotLabeler()

@profile_labeler.message(payload={"cmd": "profile"})
async def profile_handler(message: Message):
    user_id = message.from_id
    user = await get_or_create_user(user_id)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,)) as c:
            invited = (await c.fetchone())[0]

    now = int(time.time())
    vip_status = f"Активен 👑" if user["vip_until"] > now else "Не активен ❌"
    ref_bonus = await get_setting("ref_coins", "20")
    ref_link = f"https://vk.com/club{GROUP_ID}?ref=ref_{user_id}"

    text = (
        f"👤 Личный кабинет читателя:\n\n"
        f"🆔 Твой ID: {user_id}\n"
        f"🪙 Баланс монет: {user['coins']}\n"
        f"👑 VIP-подписка: {vip_status}\n"
        f"👥 Приглашено друзей: {invited} чел.\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎁 Приглашай друзей и получай +{ref_bonus} 🪙 за каждого!\n"
        f"👉 Твоя реферальная ссылка:\n{ref_link}"
    )
    await message.answer(text)
