from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta

from database import connect_db
from handlers.common import user_keyboard

router = Router()

# FSM Holatlari
class AppointmentStates(StatesGroup):
    waiting_for_doctor_select = State()
    waiting_for_appointment_name = State()
    waiting_for_appointment_time = State()
    waiting_for_phone = State()

# Shifokorlar ro'yxati klaviatura
def get_doctors_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🩺 Infeksionist", callback_data="doc_Infeksionist")],
        [InlineKeyboardButton(text="🩺 Dermatolog", callback_data="doc_Dermatolog")],
        [InlineKeyboardButton(text="🩺 Terapevt", callback_data="doc_Terapevt")],
        [InlineKeyboardButton(text="🩺 Ginekolog", callback_data="doc_Ginekolog")]
    ])

# Telefon raqam so'rash klaviatura
phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
    resize_keyboard=True, one_time_keyboard=True
)

# Jarayon boshlanishi
@router.message(F.text == "📅 Qabulga yozilish")
async def user_appointment_start(message: types.Message, state: FSMContext):
    await state.set_state(AppointmentStates.waiting_for_doctor_select)
    await message.answer("📋 Qaysi shifokor qabuliga yozilmoqchisiz?", reply_markup=get_doctors_keyboard())

# Shifokor tanlanganda
@router.callback_query(F.data.startswith("doc_"), AppointmentStates.waiting_for_doctor_select)
async def process_doctor_selection(callback: types.CallbackQuery, state: FSMContext):
    doctor_name = callback.data.split("doc_")[1]
    await state.update_data(chosen_doctor=doctor_name)
    await state.set_state(AppointmentStates.waiting_for_appointment_name)
    await callback.message.edit_text("✍️ Iltimos, to'liq ism-sharifingizni kiriting:")

# Ism kiritilganda kelgusi bo'sh vaqtlarni chiqarish
@router.message(AppointmentStates.waiting_for_appointment_name)
async def process_ap_name(message: types.Message, state: FSMContext):
    await state.update_data(patient_name=message.text.strip())
    await state.set_state(AppointmentStates.waiting_for_appointment_time)
    
    # Kelgusi 3 kunlik bo'sh vaqtlarni shakllantirish (Shanba va Yakshanbasiz)
    now = datetime.now()
    buttons = []
    for i in range(1, 4):
        day = now + timedelta(days=i)
        if day.weekday() < 5:  # 0-4 dushanba-juma degani
            day_str = day.strftime('%Y-%m-%d')
            buttons.append([InlineKeyboardButton(text=f"📅 {day_str} soat 10:00", callback_data=f"time_{day_str} 10:00")])
            buttons.append([InlineKeyboardButton(text=f"📅 {day_str} soat 14:00", callback_data=f"time_{day_str} 14:00")])
            
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("🕒 O'zingizga qulay qabul vaqtini tanlang:", reply_markup=kb)

# Tanlangan vaqtni bazada band yoki bo'shligini tekshirish
@router.callback_query(F.data.startswith("time_"), AppointmentStates.waiting_for_appointment_time)
async def process_time_callback(callback: types.CallbackQuery, state: FSMContext):
    selected_time = callback.data.split("time_")[1]
    data = await state.get_data()
    doc = data.get("chosen_doctor")

    # SQL Injectiondan himoyalangan holda tekshirish
    conn = connect_db()
    chk = conn.execute("SELECT COUNT(*) FROM appointments WHERE doctor_type=? AND details LIKE ?", (doc, f"%{selected_time}%")).fetchone()[0]
    conn.close()

    if chk > 0:
        await callback.answer("❌ Afsuski, ushbu vaqt band! Iltimos, boshqa vaqtni tanlang.", show_alert=True)
        return

    await state.update_data(booking_time=selected_time)
    await state.set_state(AppointmentStates.waiting_for_phone)
    await callback.message.answer("📱 Aloqa uchun telefon raqamingizni pastdagi tugma orqali yuboring:", reply_markup=phone_keyboard)

# Telefon raqamni olish va bazaga saqlash
@router.message(AppointmentStates.waiting_for_phone)
async def process_appointment_phone(message: types.Message, state: FSMContext):
    # Agar tugma orqali kontakt yuborilsa yoki qo'lda yozilsa ham qabul qiladi
    phone_number = message.contact.phone_number if message.contact else message.text
    data = await state.get_data()
    
    # MUHIM: details ustuniga faqat vaqtni yozamiz, shunda admin panelda chalkashlik bo'lmaydi
    booking_time = data.get('booking_time')
    patient_name = data.get('patient_name')
    doctor = data.get('chosen_doctor')

    await state.clear()

    conn = connect_db()
    conn.execute(
        "INSERT INTO appointments (user_id, full_name, doctor_type, details, phone_number) VALUES (?, ?, ?, ?, ?)",
        (message.from_user.id, patient_name, doctor, booking_time, phone_number)
    )
    conn.commit()
    conn.close()

    await message.answer(
        f"✅ Rahmat! Siz muvaffaqiyatli qabulga yozildingiz.\n\n"
        f"👨‍⚕️ Shifokor: {doctor}\n"
        f"🕒 Vaqt: {booking_time}\n\n"
        f"Bot sizga qabuldan 1 kun oldin va 20 daqiqa qolganda avtomatik ravishda eslatma yuboradi.", 
        reply_markup=user_keyboard
    )

    # Avtomatik eslatma taymerini (Scheduler) yuklash qismi
    try:
        from main import scheduler
        book_dt = datetime.strptime(booking_time, '%Y-%m-%d %H:%M')
        
        # 20 daqiqa oldin eslatma
        rem_20m = book_dt - timedelta(minutes=20)
        if rem_20m > datetime.now():
            scheduler.add_job(send_reminder_msg, 'date', run_date=rem_20m, args=[message.from_user.id, doctor, "20 daqiqa"])
            
        # 1 kun oldin eslatma
        rem_1d = book_dt - timedelta(days=1)
        if rem_1d > datetime.now():
            scheduler.add_job(send_reminder_msg, 'date', run_date=rem_1d, args=[message.from_user.id, doctor, "1 kun"])
    except Exception:
        pass

# Eslatma xabarini yuborish yordamchi funksiyasi
async def send_reminder_msg(user_id: int, doctor: str, period: str):
    from main import bot
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"⏰ <b>QABULGA ESLATMA!</b>\n\nSizning {doctor} shifokor qabulingizga <b>{period}</b> qoldi. "
                 f"Iltimos, belgilangan vaqtda yetib kelishingizni so'raymiz.",
            parse_mode="HTML"
        )
    except Exception:
        pass