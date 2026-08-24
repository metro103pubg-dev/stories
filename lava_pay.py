import aiohttp
import os

LAVA_API_KEY = os.getenv("LAVA_API_KEY", "")

async def create_lava_payment(user_id: int, amount: int, item_type: str, item_id: int, coins: int = 0) -> str:
    """
    item_type: 'coins' (пакет монет), 'story' (вся книга)
    """
    url = "https://gate.lava.top/api/v2/invoice"
    
    headers = {
        "Authorization": f"Bearer {LAVA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # В customFields передаем: user_id:item_type:item_id:coins_amount
    custom_field = f"{user_id}:{item_type}:{item_id}:{coins}"

    payload = {
        "sum": float(amount),
        "currency": "RUB",
        "orderId": f"{user_id}_{item_type}_{item_id}_{coins}",
        "comment": f"Покупка {item_type} user {user_id}",
        "customFields": custom_field
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                res_data = await response.json()
                return res_data.get("data", {}).get("url", "https://vk.com")
    except Exception as e:
        print(f"Ошибка Lava: {e}")
        return "https://vk.com"
