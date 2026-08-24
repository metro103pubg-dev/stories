from vkbottle.bot import BotLabeler, Message
from vkbottle import API
import aiosqlite
from database import DB_PATH, get_or_create_user, get_setting
from config import GROUP_ID, VK_TOKEN

profile_labeler = BotLabeler()
api = API(token=VK_TOKEN)

@profile_labeler.message(payload={"cmd": "profile"})
async def profile_handler(message: Message):
    user_id = message.from_id
    user = await get_or_create_user(user_id)

    # 1. Проверяем статус дона через VK Donut API
    is_don = False
    try:
        is_don = bool(await api.donut.is_don(owner_id=-GROUP_ID, user_id=user_id))
    except Exception:
        pass

    vip_status = "👑 Активен (VK Donut)" if is_don else "Не активен ❌"

    # 2. Считаем приглашенных друзей
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,)) as c:
            invited = (await c.fetchone())[0]

    ref_bonus = await get_setting("ref_coins", "20")
    ref_link = f"https://vk.com/club{GROUP_ID}?ref=ref_{user_id}"
    donut_link = f"https://vk.com/donut/club{GROUP_ID}"

    text = (
        f"👤 Личный кабинет читателя:\n\n"
        f"🆔 Твой ID: {user_id}\n"
        f"🪙 Баланс монет: {user['coins']}\n"
        f"👑 VIP-подписка: {vip_status}\n"
        f"👥 Приглашено друзей: {invited} чел.\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👉 Оформить VIP на месяц: {donut_link}\n\n"
        f"🎁 Приглашай друзей и получай +{ref_bonus} 🪙 за каждого!\n"
        f"🔗 Твоя реферальная ссылка:\n{ref_link}"
    )
    await message.answer(text)
