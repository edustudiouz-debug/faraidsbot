import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# .env faylini xavfsiz yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
admin_env = os.getenv("ADMINS", "")

# Admin ID larini to'plam (set) ko'rinishida xavfsiz formatlash
ADMINS = {int(admin_id.strip()) for admin_id in admin_env.split(",") if admin_id.strip().isdigit()}

# 🔐 ШИФРЛАШ ТИЗИМИ (Cryptography)
KEY_FILE = "secret.key"
if not os.path.exists(KEY_FILE):
    # Agar kalit fayli bo'lmasa, yangi maxfiy kalit yaratiladi
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(key)
else:
    # Bor bo'lsa, xavfsiz o'qib olinadi
    with open(KEY_FILE, "rb") as key_file:
        key = key_file.read()

cipher_suite = Fernet(key)

def encrypt_data(text: str) -> str:
    """Матнни хакерлар ўқий олмайдиган кодга айлантириш"""
    if not text: 
        return ""
    return cipher_suite.encrypt(text.encode()).decode()

def decrypt_data(cipher_text: str) -> str:
    """Кодланган матнни асл ҳолига (паспорт/жшшир) қайтариш"""
    if not cipher_text: 
        return ""
    try:
        return cipher_suite.decrypt(cipher_text.encode()).decode()
    except Exception:
        return "Шифрлаш хатоси (Калит нотўғри)"