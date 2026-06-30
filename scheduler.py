from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

# Markaziy scheduler obyektini yaratamiz
scheduler = AsyncIOScheduler()

async def send_reminder_msg(user_id: int, doctor: str, period: str):
    """Bemorga belgilangan vaqtda shifokor qabuli haqida eslatma yuborish"""
    from main import bot
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"⏰ <b>QABULGA ESLATMA!</b>\n\n"
                 f"Sizning {doctor} shifokor qabulingizga <b>{period}</b> vaqt qoldi. "
                 f"Belgilangan vaqtda yetib kelishingizni so'raymiz."
        )
    except Exception:
        pass

async def db_backup():
    """Har kuni tunda ma'lumotlar bazasining nusxasini adminlarga yuborish"""
    import os
    from aiogram.types import FSInputFile
    from main import bot
    from config import ADMINS
    
    db_file_path = os.path.join("data", "bot.db")
    
    if os.path.exists(db_file_path):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        backup_file = FSInputFile(db_file_path)
        
        for admin_id in ADMINS:
            try:
                await bot.send_document(
                    chat_id=admin_id, 
                    document=backup_file, 
                    caption=f"🛡️ <b>AVTOMATIK BAZA BЕKAPI</b>\n📅 Sana: {current_time}\n\n"
                            f"Tizim xavfsizligi uchun baza nusxasi muvaffaqiyatli saqlandi."
                )
            except Exception:
                continue