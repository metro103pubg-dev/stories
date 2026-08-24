import os
from vkbottle import Keyboard, KeyboardButtonColor, Text, OpenLink
from config import GROUP_ID

LAVA_LINK_50 = os.getenv("LAVA_LINK_50", "https://lava.top")
LAVA_LINK_99 = os.getenv("LAVA_LINK_99", "https://lava.top")
LAVA_LINK_199 = os.getenv("LAVA_LINK_199", "https://lava.top")
LAVA_LINK_BOOK = os.getenv("LAVA_LINK_BOOK", "https://lava.top")

def main_menu_kb():
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("📖 Продолжить чтение", payload={"cmd": "continue"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("📚 Каталог историй", payload={"cmd": "catalog"}))
    kb.add(Text("🔍 Поиск", payload={"cmd": "search"}))
    kb.row()
    kb.add(Text("🪙 Купить монеты / VIP", payload={"cmd": "shop_coins"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("👤 Профиль", payload={"cmd": "profile"}))
    return kb

def reading_kb(story_id: int, next_chapter: int):
    kb = Keyboard(inline=True)
    kb.add(
        Text("Читать дальше ➡️", payload={"cmd": "read", "story_id": story_id, "chapter": next_chapter}),
        color=KeyboardButtonColor.PRIMARY
    )
    return kb

def hybrid_paywall_kb(user_coins: int, story_id: int, chapter_num: int, chapter_coins: int, full_price: int):
    kb = Keyboard(inline=True)
    
    # 1. Если хватает монет — моментальное открытие
    if user_coins >= chapter_coins:
        kb.add(
            Text(f"🪙 Открыть главу ({chapter_coins} монет)", payload={"cmd": "unlock_coin", "story_id": story_id, "chapter": chapter_num}),
            color=KeyboardButtonColor.POSITIVE
        )
        kb.row()
    else:
        kb.add(Text("🪙 Пополнить монеты (от 50 ₽)", payload={"cmd": "shop_coins"}), color=KeyboardButtonColor.PRIMARY)
        kb.row()

    # 2. VIP VK Donut
    donut_url = f"https://vk.com/donut/club{GROUP_ID}"
    kb.add(OpenLink(donut_url, label="👑 VIP на всё (VK Donut)"))
    kb.row()

    # 3. Вся книга целиком по СБП
    kb.add(OpenLink(LAVA_LINK_BOOK, label=f"📖 Купить всю книгу ({full_price} ₽)"))
    kb.row()

    # 4. Бесплатный таймер
    kb.add(
        Text("⏳ Подождать 3 часа (бесплатно)", payload={"cmd": "start_timer", "story_id": story_id, "chapter": chapter_num}),
        color=KeyboardButtonColor.SECONDARY
    )
    return kb

def coin_shop_kb():
    """Витрина: VK Donut + Пакеты монет по СБП"""
    kb = Keyboard(inline=True)
    donut_url = f"https://vk.com/donut/club{GROUP_ID}"
    kb.add(OpenLink(donut_url, label="👑 VIP-Подписка на всё (199 ₽/мес)"))
    kb.row()
    kb.add(OpenLink(LAVA_LINK_50, label="🪙 50 монет — 50 ₽ (СБП)"))
    kb.row()
    kb.add(OpenLink(LAVA_LINK_99, label="🔥 120 монет — 99 ₽ (Хит)"))
    kb.row()
    kb.add(OpenLink(LAVA_LINK_199, label="💎 300 монет — 199 ₽ (Выгода)"))
    return kb
