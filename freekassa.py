import hashlib
import time
from config import FK_MERCHANT_ID, FK_SECRET_1

def generate_fk_link(user_id: int, amount: int, item_type: str, item_id: int) -> str:
    order_id = f"{user_id}_{int(time.time())}"
    currency = "RUB"
    sign_str = f"{FK_MERCHANT_ID}:{amount}:{FK_SECRET_1}:{currency}:{order_id}"
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()

    return (
        f"https://pay.freekassa.ru/?"
        f"m={FK_MERCHANT_ID}&oa={amount}&currency={currency}&o={order_id}&s={sign}&"
        f"us_userid={user_id}&us_type={item_type}&us_itemid={item_id}"
    )
