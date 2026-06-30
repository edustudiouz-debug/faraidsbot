from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
# Mana bu qatorda InlineKeyboardMarkup va InlineKeyboardButton ni qo'shdik:
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMINS
from database import connect_db, add_analysis_request
from handlers.common import user_keyboard
router = Router()

# FSM Holatlari (States)
class AnalysisStates(StatesGroup):
    waiting_for_passport = State()
    waiting_for_jshshir = State()
    waiting_for_birthdate = State()
    waiting_for_selfie = State()

# Tahlil natijasini so'rash boshlanishi
@router.message(F.text == "🧾 Tahlil natijasi")
async def user_analysis_request_start(message: types.Message, state: FSMContext):
    await state.clear()
    
    conn = connect_db()
    # Avval tayyor javobi bor-yo'qligini tekshiramiz
    res = conn.execute("SELECT result_text, file_id FROM analysis WHERE user_id = ?", (message.from_user.id,)).fetchone()
    conn.close()

    if res:
        text, file_id = res
        await message.answer(f"🧾 <b>Sizning tahlil natijangiz tayyor:</b>\n\n{text}", reply_markup=user_keyboard)
        if file_id:
            try: 
                await message.bot.send_document(message.from_user.id, document=file_id)
            except Exception: 
                pass
        return

    # Agar javob bo'lmasa, pasport ma'lumotlarini so'rash rejimini yoqamiz
    await state.set_state(AnalysisStates.waiting_for_passport)
    await message.answer(
        "🧾 Tahlil natijasini olish uchun shaxsingizni tasdiqlashingiz kerak.\n"
        "Iltimos, <b>Pasport seriyasi va raqamini</b> kiriting (Masalan: AA1234567):", 
        reply_markup=ReplyKeyboardRemove()
    )

# Pasport seriyasini qabul qilish
@router.message(AnalysisStates.waiting_for_passport)
async def process_user_passport(message: types.Message, state: FSMContext):
    passport_input = message.text.upper().strip().replace(" ", "")
    
    # Oddiy validatsiya (masalan, uzunligi kamida 7 ta bo'lishi kerak)
    if len(passport_input) < 7:
        await message.answer("⚠️ Pasport formati noto'g'ri. Iltimos, qaytadan to'g'ri kiriting (Masalan: AA1234567):")
        return
        
    await state.update_data(passport=passport_input)
    await state.set_state(AnalysisStates.waiting_for_jshshir)
    await message.answer("🔢 14 xonali <b>JSHSHIR (ПИНФЛ)</b> kodingizni kiriting:")

# JSHSHIRni qabul qilish
@router.message(AnalysisStates.waiting_for_jshshir)
async def process_user_jshshir(message: types.Message, state: FSMContext):
    jshshir = message.text.strip()
    
    # 14 ta raqamdan iboratligini tekshirish (Xavfsizlik va xatolik nazorati)
    if not jshshir.isdigit() or len(jshshir) != 14:
        await message.answer("⚠️ Xato! JSHSHIR faqat 14 ta raqamdan iborat bo'lishi shart.\nQaytadan tekshirib kiriting:")
        return
        
    await state.update_data(jshshir=jshshir)
    await state.set_state(AnalysisStates.waiting_for_birthdate)
    await message.answer("📅 Tug'ilgan kuningizni kiriting (Masalan: 15.08.1995):")

# Tug'ilgan sanani qabul qilish
@router.message(AnalysisStates.waiting_for_birthdate)
async def process_user_birthdate(message: types.Message, state: FSMContext):
    birth_date = message.text.strip()
    await state.update_data(birth_date=birth_date)
    
    # Keyingi bosqich - Face ID nazorati
    await state.set_state(AnalysisStates.waiting_for_selfie)
    await message.answer(
        "📸 <b>Xavfsizlik tizimi (Face Control):</b>\n\n"
        "Tahlil natijalari maxfiy bo'lganligi sababli, shaxsingizni tasdiqlash uchun hozir kamerani yoqib, "
        "<b>o'zingizni selfi (rasm) ko'rinishida</b> yuboring:"
    )

# Face ID (Selfi rasm) qabul qilish va yakunlash
@router.message(AnalysisStates.waiting_for_selfie, F.photo)
async def process_user_selfie(message: types.Message, state: FSMContext):
    # Foydalanuvchi yuborgan rasmning eng sifatli (katta) nusxasini olamiz
    selfie_id = message.photo[-1].file_id
    data = await state.get_data()
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    await state.clear()

    # database.py faylidagi xavfsiz shifrlangan funksiyaga yuboramiz
    add_analysis_request(
        user_id=user_id,
        full_name=full_name,
        passport=data['passport'],
        jshshir=data['jshshir'],
        birth_date=data['birth_date'],
        selfie_id=selfie_id
    )

    await message.answer(
        "⏳ Rahmat! Ma'lumotlaringiz va Face ID rasmingiz markaz shifokorlariga yuborildi.\n"
        "Natijangiz tekshirilib, tasdiqlangach bot orqali avtomatik PDF shaklida yuboriladi.", 
        reply_markup=user_keyboard
    )

    # Adminlarga tugmalar bilan xabarnoma yuborish qismi
    admin_text = (
        f"🔔 <b>YANGI TAHLIL SO'ROVI (FACE CONTROL)</b>\n\n"
        f"👤 Bemor: {full_name}\n"
        f"🆔 Telegram ID: <code>{user_id}</code>\n"
        f"🪪 Pasport: <code>{data['passport']}</code>\n"
        f"🔢 JSHSHIR: <code>{data['jshshir']}</code>\n"
        f"📅 Tug'ilgan sana: {data['birth_date']}"
    )
    
    # Qabul qilish va Rad etish tugmalarini yaratamiz
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"accept_{user_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{user_id}")
        ]
    ])
    
    for admin_id in ADMINS:
        try:
            # Adminga bemor rasmi, ma'lumotlari va tugmalar bilan yuboramiz
            await message.bot.send_photo(
                chat_id=admin_id, 
                photo=selfie_id, 
                caption=admin_text, 
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception: 
            continue

# Agar rasm o'rniga boshqa narsa yuborsa, ogohlantiramiz
@router.message(AnalysisStates.waiting_for_selfie)
async def process_user_selfie_invalid(message: types.Message):
    await message.answer("⚠️ Iltimos, Face ID tizimidan o'tish uchun faqat rasm (selfi) yuboring:")