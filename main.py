import asyncio
import os
import sqlite3
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from fpdf import FPDF
import requests

# 1. Sozlamalar
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN .env faylda topilmadi!")
ADMIN_ID = 5916727569

BASE_URL = "https://student.jbnuu.uz/rest/v1"
LOGIN_URL = f"{BASE_URL}/auth/login"
PROFILE_URL = f"{BASE_URL}/account/me"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# 2. Ma'lumotlar bazasi
conn = sqlite3.connect("bot_users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY
                  )""")
conn.commit()

# 3. Holatlar
class LoginState(StatesGroup):
    login = State()
    password = State()
    authorized = State()

# 4. Klaviaturalar
def main_menu():
    kb = [
        [KeyboardButton(text="👤 Mening profilim"), KeyboardButton(text="📄 SHAXSIY MA'LUMOTLAR (PDF)")],
        [KeyboardButton(text="🏛 JBNUU haqida"), KeyboardButton(text="👨‍💻 Dasturchi")],
        [KeyboardButton(text="🌐 TIZIMGA KIRISH"), KeyboardButton(text="❌ Chiqish")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_menu():
    kb = [
        [KeyboardButton(text="📊 STATISTIKA"), KeyboardButton(text="🏠 Bosh menyu")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# 5. PDF yaratish
def clean_text(text):
    if not text:
        return "-"
    text = str(text)
    replacements = {"‘": "'", "’": "'", "ʻ": "'", "ʼ": "'", "o‘": "o'", "g‘": "g'", "O‘": "O'", "G‘": "G'"}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def create_pdf(data, login):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    img_url = data.get("image")
    y_start = 15
    temp_img = "temp_img.jpg"
    if img_url:
        try:
            img_res = requests.get(img_url, timeout=10)
            img_res.raise_for_status()
            with open(temp_img, "wb") as f:
                f.write(img_res.content)
            pdf.image(temp_img, x=150, y=8, w=45)
            y_start = 60
            os.remove(temp_img)
        except Exception:
            pass

    pdf.set_y(y_start)
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 10, "TALABA SHAXSIY VARAQASI", ln=1, align="C")
    pdf.ln(10)

    def add_field(label, value):
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(50, 10, f"{label}:", border=1)
        pdf.set_font("helvetica", "", 12)
        pdf.cell(140, 10, clean_text(value), border=1, ln=1)

    add_field("F.I.SH", data.get("full_name", "-"))
    add_field("HEMIS ID", data.get("student_id_number", "-"))
    add_field("GPA", data.get("avg_gpa", "-"))
    add_field("Fakultet", data.get("faculty", {}).get("name", "-"))
    add_field("Guruh", data.get("group", {}).get("name", "-"))
    add_field("Telefon", data.get("phone", "-"))

    path = f"anketa_{login}.pdf"
    pdf.output(path)
    return path

# 6. Handlerlar
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    await message.answer(
        "Assalomu alaykum! 🎉\n\n"
        "JBNUU talabalari uchun maxsus botga xush kelibsiz!\n"
        "Profil va shaxsiy ma'lumotlarni ko'rish uchun avval HEMIS tizimiga kiring yoki to'g'ridan-to'g'ri saytga o'ting.",
        reply_markup=main_menu()
    )

# YANGI: TIZIMGA KIRISH tugmasi — saytni ochadi
@dp.message(F.text == "🌐 TIZIMGA KIRISH")
async def open_hemis_site(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 HEMIS Tizimiga Kirish", url="https://student.jbnuu.uz/")]
    ])
    await message.answer(
        "📢 HEMIS axborot tizimiga kirish uchun quyidagi tugmani bosing:",
        reply_markup=keyboard
    )

# YANGI: Dasturchi tugmasi — yangi matn
@dp.message(F.text == "👨‍💻 Dasturchi")
async def dev_info(message: types.Message):
    text = (
        "👨‍💻 Dasturchi: Sadullayev Jaxongir\n"
        "🎓 Loyiha: HEMIS Intellektual Tizimi\n\n"
        "🤖 **Bot haqida:**\n"
        "Ushbu bot universitet talabalari uchun HEMIS axborot tizimi bilan "
        "integratsiya qilingan holda ishlab chiqilgan. Bot orqali siz:\n\n"
        "✅ O'z shaxsiy ma'lumotlaringizni ko'rishingiz;\n"
        "✅ Akademik ko'rsatkichlaringizni (GPA) kuzatishingiz;\n"
        "✅ Shaxsiy varaqangizni (Anketa) PDF shaklida yuklab olishingiz mumkin.\n\n"
        "⚠️ *Barcha ma'lumotlar bevosita universitet bazasidan real vaqt rejimida olinadi.*"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 Admin paneliga xush kelibsiz!", reply_markup=admin_menu())
    else:
        await message.answer("⛔️ Ruxsat etilmagan!")

@dp.message(F.text == "📊 STATISTIKA")
async def get_stats(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        await message.answer(f"📊 Bot foydalanuvchilari soni: **{count}** ta", parse_mode="Markdown")
    else:
        await message.answer("⛔️ Faqat admin!")

@dp.message(F.text == "🏠 Bosh menyu")
async def back_main(message: types.Message):
    await message.answer("🏠 Asosiy menyuga qaytdik.", reply_markup=main_menu())

# /login buyrug'i hali ham ishlaydi (agar kerak bo'lsa)
@dp.message(Command("login"))
async def login_via_command(message: types.Message, state: FSMContext):
    await message.answer("👤 HEMIS loginni kiriting:")
    await state.set_state(LoginState.login)

@dp.message(LoginState.login)
async def process_login(message: types.Message, state: FSMContext):
    await state.update_data(login=message.text.strip())
    await message.answer("🔐 HEMIS parolni kiriting:")
    await state.set_state(LoginState.password)

@dp.message(LoginState.password)
async def process_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    login = data["login"]
    password = message.text

    try:
        response = requests.post(LOGIN_URL, json={"login": login, "password": password}, timeout=15)
        response.raise_for_status()
        result = response.json()

        if result.get("success") and result.get("data", {}).get("token"):
            token = result["data"]["token"]
            await state.update_data(token=token, login=login)
            await state.set_state(LoginState.authorized)
            await message.answer("✅ Muvaffaqiyatli kirish! Endi profilingizni ko'rishingiz mumkin.", reply_markup=main_menu())
        else:
            await message.answer("❌ Login yoki parol noto'g'ri!\nQaytadan /login buyrug'ini yuboring.")
            await state.clear()
    except requests.exceptions.RequestException:
        await message.answer("⚠️ Server bilan ulanishda xatolik. Keyinroq urinib ko'ring.")
        await state.clear()
    except Exception:
        await message.answer("❌ Noma'lum xatolik. /login bilan qayta boshlang.")
        await state.clear()

@dp.message(F.text == "👤 Mening profilim")
async def my_profile(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("token"):
        await message.answer("⚠️ Profilingizni ko'rish uchun avval HEMISga kiring.\nYoki to'g'ridan-to'g'ri saytga o'ting: 🌐 TIZIMGA KIRISH")
        return

    try:
        headers = {"Authorization": f"Bearer {data['token']}"}
        response = requests.get(PROFILE_URL, headers=headers, timeout=15)
        response.raise_for_status()
        profile = response.json().get("data", {})

        text = (
            f"👤 **{clean_text(profile.get('full_name', '-'))}**\n"
            f"🆔 HEMIS ID: `{profile.get('student_id_number', '-')}`\n"
            f"📈 O'rtacha baho (GPA): {profile.get('avg_gpa', '-')}"
        )

        if profile.get("image"):
            await message.answer_photo(profile["image"], caption=text, parse_mode="Markdown")
        else:
            await message.answer(text, parse_mode="Markdown")
    except Exception:
        await message.answer("❌ Ma'lumotlarni yuklashda xatolik. Token eskirgan bo'lishi mumkin – qayta /login qiling.")

@dp.message(F.text == "📄 SHAXSIY MA'LUMOTLAR (PDF)")
async def get_pdf(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("token"):
        await message.answer("⚠️ PDF olish uchun avval HEMISga kiring.\n🌐 TIZIMGA KIRISH tugmasidan foydalaning.")
        return

    wait_msg = await message.answer("⏳ PDF fayl tayyorlanmoqda... Iltimos kuting.")

    try:
        headers = {"Authorization": f"Bearer {data['token']}"}
        response = requests.get(PROFILE_URL, headers=headers, timeout=15)
        response.raise_for_status()
        profile_data = response.json().get("data", {})

        pdf_path = create_pdf(profile_data, data["login"])

        await message.answer_document(FSInputFile(pdf_path), caption="📄 Sizning shaxsiy ma'lumotlaringiz (PDF)")
        os.remove(pdf_path)
    except Exception:
        await message.answer("❌ PDF yaratishda xatolik yuz berdi. Qayta urinib ko'ring.")
    finally:
        await wait_msg.delete()

@dp.message(F.text == "🏛 JBNUU haqida")
async def about_jbnuu(message: types.Message):
    await message.answer(
        "🏛 **O'zMU Jizzax filiali (JBNUU)**\n"
        "📍 Manzil: Jizzax shahri, Sh.Rashidov shoh ko'chasi, 259-uy\n"
        "🌐 Rasmiy sayt: https://jbnuu.uz/",
        parse_mode="Markdown"
    )

@dp.message(F.text == "❌ Chiqish")
async def logout(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Tizimdan muvaffaqiyatli chiqdingiz.", reply_markup=main_menu())

# 7. Ishga tushirish
async def main():
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())