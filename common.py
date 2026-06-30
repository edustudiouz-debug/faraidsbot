import re
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from config import ADMINS
from database import connect_db

# Xatolikni to'g'rilash uchun global lug'at
error_log = {}

router = Router()

# Tilni tekshirish funksiyalari
def is_cyrillic(text):
    return bool(re.search('[а-яА-ЯёЁ]', text))

def is_latin(text):
    return bool(re.search('[a-zA-Z]', text))

# FSM (State) Holatlari
class CommonStates(StatesGroup):
    waiting_for_gender = State()
    waiting_for_anon_message = State()

# =====================================================================
# KLAVIATURALAR (TUGMALAR)
# =====================================================================
gender_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="👨 Erkak"), KeyboardButton(text="👩 Ayol")]],
    resize_keyboard=True, one_time_keyboard=True
)

user_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Qabulga yozilish"), KeyboardButton(text="🧾 Tahlil natijasi")],
        [KeyboardButton(text="🏛 Qabul kunlari"), KeyboardButton(text="📍 Bizning manzil")],
        [KeyboardButton(text="❓ Anonim savol yo'llash")]
    ],
    resize_keyboard=True
)

admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📢 Xabar yuborish"), KeyboardButton(text="🧾 Test tahlili yuklash")],
        [KeyboardButton(text="📋 Bemorlar navbati"), KeyboardButton(text="📄 PDF Tahlil yaratish")],
        [KeyboardButton(text="📊 Tahlil so'raganlar (Excel)"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="🚫 Bloklash (Ban)")]
    ],
    resize_keyboard=True
)

# =====================================================================
# START BUYRUG'I
# =====================================================================
@router.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id in ADMINS:
        await message.answer("👋 Assalomu alaykum Admin Panelga xush kelibsiz!", reply_markup=admin_keyboard)
        return

    conn = connect_db()
    user = conn.execute("SELECT is_banned, gender FROM users WHERE user_id = ?", (message.from_user.id,)).fetchone()
    conn.close()

    if user and user[0] == 1:
        return

    if user is None or user[1] is None:
        await state.set_state(CommonStates.waiting_for_gender)
        await message.answer("👋 Assalomu alaykum! Botdan foydalanishdan avval jinsingizni tanlang:", reply_markup=gender_keyboard)
    else:
        await message.answer("👋 Fargʻona viloyat OITS markazi botiga xush kelibsiz!", reply_markup=user_keyboard)

# =====================================================================
# JINSNI QABUL QILISH
# =====================================================================
@router.message(CommonStates.waiting_for_gender)
async def process_gender(message: types.Message, state: FSMContext):
    if message.text not in ["👨 Erkak", "👩 Ayol"]:
        await message.answer("Iltimos, pastdagi tugmalardan birini bosing:", reply_markup=gender_keyboard)
        return
        
    gender_val = "Erkak" if "Erkak" in message.text else "Ayol"
    await state.clear()
    
    conn = connect_db()
    conn.execute("INSERT OR REPLACE INTO users (user_id, gender, is_banned) VALUES (?, ?, 0)", (message.from_user.id, gender_val))
    conn.commit()
    conn.close()
    
    await message.answer("✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!", reply_markup=user_keyboard)

# =====================================================================
# ANONIM SAVOL YO'LLASH TIZIMI
# =====================================================================
@router.message(F.text == "❓ Anonim savol yo'llash")
async def ask_anon_message(message: types.Message, state: FSMContext):
    await state.set_state(CommonStates.waiting_for_anon_message)
    await message.answer("✍️ Savolingizni yozing, biz uni shifokorlarga anonim tarzda yetkazamiz:", reply_markup=ReplyKeyboardRemove())

@router.message(CommonStates.waiting_for_anon_message)
async def process_anonymous_message(message: types.Message, state: FSMContext):
    # TILNI TEKSHIRISH (Agar matn lotin yoki kirill alifbosida bo'lmasa, xabar berish)
    if not is_latin(message.text) and not is_cyrillic(message.text):
        await message.answer("❌ Murojaat tushunarsiz. Iltimos, to'g'ri tilda yozing.")
        return

    await state.clear()
    user = message.from_user
    username = f"@{user.username}" if user.username else "Username yo'q"
    
    caption = (
        f"📩 <b>Yangi anonim xabar:</b>\n\n"
        f"👤 <b>Ismi:</b> {user.full_name}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"🏷 <b>Username:</b> {username}\n\n"
        f"✍️ <b>Matn:</b> {message.text}"
    )

    try:
        photos = await message.bot.get_user_profile_photos(user_id=user.id, limit=1)
        if photos.total_count > 0:
            photo_id = photos.photos[0][-1].file_id
            for admin_id in ADMINS:
                await message.bot.send_photo(chat_id=admin_id, photo=photo_id, caption=caption)
        else:
            for admin_id in ADMINS:
                await message.bot.send_message(chat_id=admin_id, text=caption)
    except Exception as e:
        for admin_id in ADMINS:
            await message.bot.send_message(chat_id=admin_id, text=caption + f"\n\n⚠️ Rasm yuklashda xatolik: {e}")

    await message.answer("✅ Savolingiz anonim tarzda shifokorlarga yetkazildi.", reply_markup=user_keyboard)

# =====================================================================
# ADMIN JAVOB BERISH (REPLY ORQALI)
# =====================================================================
@router.message(F.reply_to_message, F.from_user.id.in_(ADMINS))
async def admin_reply_to_anon(message: types.Message):
    original_msg = message.reply_to_message
    original_text = original_msg.text or original_msg.caption or ""
    
    clean_text = original_text.replace("<code>", "").replace("</code>", "")
    user_id_match = re.search(r"ID:\s*(\d+)", clean_text)
    
    if not user_id_match:
        await message.answer("❌ ID topilmadi. Iltimos, faqat bot yuborgan xabarga 'Reply' qiling.")
        return

    target_user_id = user_id_match.group(1)
    
    try:
        await message.bot.send_message(
            chat_id=target_user_id,
            text=f"📩 <b>Shifokordan javob:</b>\n\n{message.text}"
        )
        await message.answer("✅ Javob foydalanuvchiga yuborildi!")
        error_log[target_user_id] = 0
    except Exception as e:
        error_log[target_user_id] = error_log.get(target_user_id, 0) + 1
        
        if error_log[target_user_id] >= 2:
            try:
                await message.bot.send_message(
                    chat_id=target_user_id,
                    text="⚠️ <b>Admin sizga javob yozdi, lekin texnik sabablarga ko'ra sizga yetib kelmayapti.</b>\n\nIltimos, botni /start qilib qayta ishga tushiring."
                )
                await message.answer("✅ Foydalanuvchiga muammo haqida xabar berildi.")
                error_log[target_user_id] = 0
            except:
                await message.answer("❌ Foydalanuvchi botni bloklagan bo'lishi mumkin.")
        else:
            await message.answer(f"⚠️ Xatolik yuz berdi. Yana bir marta urinib ko'ring ({error_log[target_user_id]}/2).")

# =====================================================================
# LOKATSIYA VA ISH VAQTI
# =====================================================================
@router.message(F.text == "📍 Bizning manzil")
async def user_location_info(message: types.Message):
    text = (
        "📍 <b>Bizning manzilimiz:</b> Farg'ona shahri, Madaniyat ko'chasi, 3-uy.\n"
        "🚌 <b>Muntazam transport:</b> 5-marshrutli avtobuslar (OITS markazi bekati).\n"
        "📞 <b>Ishonch telefoni:</b> +998 (73) 243-22-92"
    )
    await message.answer(text)
    await message.bot.send_location(chat_id=message.chat.id, latitude=40.383580, longitude=71.808801)

@router.message(F.text == "🏛 Qabul kunlari")
async def hospital_info(message: types.Message):
    info_text = (
        "🏛 <b>Farg'ona viloyat OITSga qarshi kurash markazi</b>\n\n"
        "📅 <b>Ish kunlari:</b> Dushanba - Juma\n"
        "⏰ <b>Ish vaqti:</b> 08:00 dan 16:00 gacha\n"
        "⏳ <b>Dam olish kunlari:</b> Shanba va Yakshanba\n\n"
        "<i>Tahlil topshirish istagida bo'lganlar ertalab soat 08:00 dan 11:00 gacha kelishlari tavsiya etiladi.</i>"
    )
    await message.answer(info_text)