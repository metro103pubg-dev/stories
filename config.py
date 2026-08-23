import os

VK_TOKEN = os.getenv("VK_TOKEN", "")
GROUP_ID = int(os.getenv("GROUP_ID", "0"))

admin_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in admin_raw.split(",") if x.strip().isdigit()]

FK_MERCHANT_ID = os.getenv("FK_MERCHANT_ID", "12345")
FK_SECRET_1 = os.getenv("FK_SECRET_1", "secret1")
FK_SECRET_2 = os.getenv("FK_SECRET_2", "secret2")
PORT = int(os.getenv("PORT", "8080"))
