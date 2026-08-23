from vkbottle import Keyboard, KeyboardButtonColor, Text, OpenLink
from freekassa import generate_fk_link
from config import GROUP_ID

def main_menu_kb():
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("📖 Продолжить чтение", payload={"cmd": "continue"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("📚 Каталог историй", payload={"cmd": "catalog"}))
    kb.add(Text("🔍 Поиск", payload={"cmd": "search"}))
    kb.row()
    kb.add(Text("👤 Профиль", payload={"cmd": "profile"}))
    return kb

def reading_kb(story_id: int, next_chapter: int):
    kb = Keyboard(inline=True)
    kb.add(
        Text("Читать дальше ➡️", payload={"cmd": "read", "story_id": story_id, "chapter": next_chapter}),
        color=KeyboardButtonColor.PRIMARY
    )
    return kb

def hybrid_paywall_kb(user_id: int, story_id: int, chapter_num: int, chapter_price: int, full_price: int):
    kb = Keyboard(inline=True)
    donut_url = f"https://vk.com/donut/club{GROUP_ID}"
    kb.add(OpenLink(donut_url, label="👑 VIP на всё (VK Donut)"))
    kb.row()

    story_pay_url = generate_fk_link(user_id, full_price, "story", story_id)
    kb.add(OpenLink(story_pay_url, label=f"📖 Купить книгу ({full_price} ₽)"))
    kb.row()

    chapter_pay_url = generate_fk_link(user_id, chapter_price, "chapter", chapter_num)
    kb.add(OpenLink(chapter_pay_url, label=f"⚡ Купить главу ({chapter_price} ₽)"))
    kb.row()

    kb.add(
        Text("⏳ Подождать 3 часа", payload={"cmd": "start_timer", "story_id": story_id, "chapter": chapter_num}),
        color=KeyboardButtonColor.SECONDARY
    )
    return kb
