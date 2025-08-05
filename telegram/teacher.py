import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

API_URL = "https://api.iqmath.uz/api/v1/func_teacher/teacher-independent/telegram-list/"

# Boshlang‘ich o‘qituvchi menyusi
async def teacher_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data.get('user_info')
    full_name = user_data['data']['full_name']
    
    keyboard = [
        [InlineKeyboardButton("📬 Menga kelgan murojaatlar", callback_data='teacher_applications')],
        [InlineKeyboardButton("📊 Murojaatlar statistikasi", callback_data='teacher_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Assalomu alaykum {full_name}!\nQuyidagi menyudan foydalaning:",
        reply_markup=reply_markup
    )

# Inline tugmalar klaviaturasini yasash
def build_teacher_applications_keyboard(results, page, has_next, has_previous):
    keyboard = []

    for item in results:
        student_name = item.get("student_full_name", "No Name")
        student_id = item.get("student_id")
        count = len(item.get("requests", []))
        btn_text = f"{student_name} 📩 {count} ta murojaat"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"student_{student_id}")
        ])

    # Pagination tugmalari
    pagination_buttons = []
    if has_previous:
        pagination_buttons.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"prev_page_{page}"))
    if has_next:
        pagination_buttons.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"next_page_{page}"))

    if pagination_buttons:
        keyboard.append(pagination_buttons)

    return InlineKeyboardMarkup(keyboard)

# Callback tugmalarni boshqarish
async def handle_teacher_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id
    page = 1

    # Sahifa aniqlash
    if query.data.startswith("next_page_"):
        page = int(query.data.split("_")[-1]) + 1
    elif query.data.startswith("prev_page_"):
        page = int(query.data.split("_")[-1]) - 1

    # Murojaatlar sahifasi
    if query.data in ['teacher_applications', 'next_page_1', 'prev_page_2'] or query.data.startswith(("next_page_", "prev_page_")):
        try:
            response = requests.post(
                API_URL,
                json={"telegram_id": telegram_id},
                params={"page": page},
                timeout=5
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            has_next = data.get("next") is not None
            has_previous = data.get("previous") is not None

            reply_markup = build_teacher_applications_keyboard(results, page, has_next, has_previous)

            await query.edit_message_text(
                text=f"📬 Sizga kelgan murojaatlar ro'yxati (sahifa {page}):",
                reply_markup=reply_markup
            )
        except Exception as e:
            await query.edit_message_text(
                text=f"❌ Xatolik yuz berdi: {e}"
            )

    # Statistika tugmasi
    elif query.data == 'teacher_stats':
        await query.edit_message_text(text="📊 Murojaatlar statistikasi (demo)...")

    # Har bir studentning murojaatini ko‘rsatish (keyinchalik to‘ldirish uchun joy)
    elif query.data.startswith("student_"):
        student_id = query.data.split("_")[1]
        await query.edit_message_text(
            text=f"🧑‍🎓 Student ID: {student_id} murojaatlari ko‘rsatilmoqda (ishlab chiqilmoqda)..."
        )
