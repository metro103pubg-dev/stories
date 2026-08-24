from vkbottle import Keyboard, KeyboardButtonColor, Text, OpenLink
from config import GROUP_ID

def main_menu_kb():
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("📖 Продолжить чтение", payload={"cmd": "continue"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("📚 Каталог историй", payload={"cmd": "catalog"}))
    kb.add(Text("🔍 Поиск", payload={"cmd": "search"}))
    kb.row()
    kb.add(Text("🪙 Купить монеты", payload={"cmd": "shop_coins"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("👤 Профиль", payload={"cmd": "profile"}))
    return kb

def reading_kb(story_id: int, next_chapter: int):
    kb = Keyboard(inline=True)
    kb.add(
        Text("Читать дальше ➡️", payload={"cmd": "read", "story_id": story_id, "chapter": next_chapter}),
        color=KeyboardButtonColor.PRIMARY
    )
    return kb

def hybrid_paywall_kb(user_coins: int, story_id: int, chapter_num: int, chapter_coins: int, full_price: int, story_pay_url: str):
    kb = Keyboard(inline=True)
    
    # 1. Если хватает монет — кнопка мгновенной покупки в чате!
    if user_coins >= chapter_coins:
        kb.add(
            Text(f"🪙 Открыть главу ({chapter_coins} монет)", payload={"cmd": "unlock_coin", "story_id": story_id, "chapter": chapter_num}),
            color=KeyboardButtonColor.POSITIVE
        )
        kb.row()
    else:
        kb.add(Text("🪙 Пополнить монеты (от 50 ₽)", payload={"cmd": "shop_coins"}), color=KeyboardButtonColor.PRIMARY)
        kb.row()

    # 2. VIP через VK Donut
    donut_url = f"https://vk.com/donut/club{GROUP_ID}"
    kb.add(OpenLink(donut_url, label="👑 VIP на всё (VK Donut)"))
    kb.row()

    # 3. Вся книга по СБП
    kb.add(OpenLink(story_pay_url, label=f"📖 Купить всю книгу ({full_price} ₽)"))
    kb.row()

    # 4. Бесплатный таймер
    kb.add(
        Text("⏳ Подождать 3 часа (бесплатно)", payload={"cmd": "start_timer", "story_id": story_id, "chapter": chapter_num}),
        color=KeyboardButtonColor.SECONDARY
    )
    return kb

def coin_shop_kb(url_50: str, url_120: str, url_300: str):
    """Магазин пакетов монет"""
    kb = Keyboard(inline=True)
    kb.add(OpenLink(url_50, label="🪙 50 монет — 50 ₽"))
    kb.row()
    kb.add(OpenLink(url_120, label="🔥 120 монет — 99 ₽ (Хит)"))
    kb.row()
    kb.add(OpenLink(url_300, label="💎 300 монет — 199 ₽ (Выгода)"))
    return kb
