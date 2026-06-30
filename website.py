import sqlite3
from aiogram import Router, F, Bot
from aiogram.types import Message

# Aiogram 3 da har bir alohida bo'lim uchun Router ishlatiladi
router = Router()

# Veb-saytdan kelgan va ichida maxsus kalit so'zi bor xabarga REPLY qilingandagina ishlaydi
@router.message(F.reply_to_message, F.reply_to_message.text.contains("VEB-SAYTDAN YANGI MUROJAAT!"))
async def handle_doctor_answer(message: Message, bot: Bot):
    original_text = message.reply_to_message.text
    doctor_answer = message.text  # Shifokor yozgan tashxis/javob
    
    token = None
    # Xabardan Murojaat Kodini (Tokenni) qidirib topish
    for line in original_text.split("\n"):
        if "Kodi:" in line:
            token = line.split("Kodi:")[1].replace("`", "").strip()
            break
            
    if token:
        try:
            # 📁 Django veb-saytning bazasiga ulanamiz
            conn = sqlite3.connect('D:/bot/sayt/db.sqlite3')
            cursor = conn.cursor()
            
            # Bazadagi arizani shifokor javobi bilan yangilaymiz
            cursor.execute('UPDATE savollar SET javob = ? WHERE token = ?', (doctor_answer, token))
            conn.commit()
            conn.close()
            
            # Shifokorga bot orqali tasdiqlash xabarini qaytaramiz
            await message.reply(
                f"✅ *Muvaffaqiyatli saqlandi!*\n🔑 Kod: `{token}` bo'yicha javobingiz veb-sayt bazasida yangilandi.", 
                parse_mode="Markdown"
            )
        except Exception as e:
            await message.reply(f"❌ Sayt bazasiga yozishda xatolik: {e}")
    else:
        await message.reply("❌ Xabardan murojaat kodi (Token) topilmadi.")