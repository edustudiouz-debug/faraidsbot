import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

# O'zimiz yozgan sozlamalar, routerlar va taymer modullarini chaqiramiz
from config import BOT_TOKEN, ADMINS
from database import init_db
from handlers import admin, analysis, appointment, common  # Tartiblangan importlar
from utils.scheduler import scheduler, db_backup

# Bot faoliyatini jurnallash (Logging) sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Bot va Dispetcher obyektlarini yangi standartlar asosida yaratamiz
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# =====================================================================
# 🚀 BOTNI ISHGA TUSHIRISH ASOSIY FUNKSIYASI
# =====================================================================
async def main():
    # 1. Ma'lumotlar bazasini tekshirish va jadvallarni yaratish
    init_db()
    
    # 2. Routerlarni (Mantiqlarni) dispetcherga xavfsiz tartibda ulash
    # ⚠️ DIQQAT TARTIB: Admin va maxsus xizmatlar tepada, umumiy matn ushlovchi 'common' ESA HAR DOIM ENG OXIRIDA turishi shart!
    dp.include_router(admin.router)
    dp.include_router(analysis.router)
    dp.include_router(appointment.router)  # Yangi qo'shilgan router (Navbat va admin tugmalari uchun)
    dp.include_router(common.router)       # Har doim eng tagida qoladi
    
    # 3. Avtomatik taymerlarni (Scheduler) sozlash
    # Har kuni tunda soat 03:00 da bazani adminlarga backup qilish vazifasi
    scheduler.add_job(db_backup, 'cron', hour=3, minute=0)
    scheduler.start()
    
    logging.info("🔒 Bot xavfsizlik arxitekturasi asosida muvaffaqiyatli ishga tushdi!")
    
    # 4. Bot o'chiq bo'lgan vaqtda kelgan eski xabarlarni tozalab, yangidan polling boshlash
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot ma'mur tomonidan to'xtatildi!")