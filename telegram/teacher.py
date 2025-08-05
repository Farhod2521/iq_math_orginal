import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

API_URL = "https://api.iqmath.uz/api/v1/func_teacher/teacher-independent/telegram-list/"

# Asosiy menyu
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

# Callback handler
async def handle_teacher_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id
    page = 1

    if query.data.startswith("next_page_"):
        page = int(query.data.split("_")[-1]) + 1
    elif query.data.startswith("prev_page_"):
        page = int(query.data.split("_")[-1]) - 1

    if query.data in ['teacher_applications'] or query.data.startswith(("next_page_", "prev_page_")):
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

            text_lines = []
            index = 1
            for student in results:
                name = student.get("student_full_name", "Noma'lum")
                count = len(student.get("requests", []))
                text_lines.append(f"{index}. {name} 📩 {count} ta murojaat")
                index += 1

            text = "📬 Sizga kelgan murojaatlar ro'yxati (sahifa {}):\n\n{}".format(
                page,
                "\n".join(text_lines) if text_lines else "Murojaatlar topilmadi."
            )

            # Pagination tugmalari
            pagination_buttons = []
            for i in range(1, 11):
                pagination_buttons.append(InlineKeyboardButton(str(i), callback_data=f"student_dummy_{i}"))

            keyboard = []
            for i in range(0, 10, 5):
                keyboard.append(pagination_buttons[i:i+5])

            nav_buttons = []
            if has_previous:
                nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"prev_page_{page}"))
            nav_buttons.append(InlineKeyboardButton("❌", callback_data="cancel"))
            if has_next:
                nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"next_page_{page}"))
            keyboard.append(nav_buttons)

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup
            )
        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    elif query.data == 'teacher_stats':
        await query.edit_message_text(text="📊 Murojaatlar statistikasi (demo)...")

    elif query.data.startswith("student_"):
        student_id = query.data.split("_")[1]
        await query.edit_message_text(
            text=f"🧑‍🎓 Student ID: {student_id} murojaatlari ko‘rsatilmoqda (ishlab chiqilmoqda)..."
        )

    elif query.data == "cancel":
        await query.edit_message_text(text="❌ Menyu bekor qilindi.")
