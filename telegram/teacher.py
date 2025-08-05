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

    # 1. Murojaatlar ro'yxati sahifalash bilan
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

            # Murojaatlar ro'yxati, raqam bilan
            text_lines = []
            for idx, student in enumerate(results, start=1):
                name = student.get("student_full_name", "Noma'lum")
                count = len(student.get("requests", []))
                text_lines.append(f"{idx}. {name} 📩 {count} ta murojaat")

            text = "📬 Sizga kelgan murojaatlar ro'yxati (sahifa {}):\n\n{}".format(
                page,
                "\n".join(text_lines) if text_lines else "Murojaatlar topilmadi."
            )

            # O'quvchilar tugmalari — har biri o'quvchi ID bilan
            keyboard = []
            for idx, student in enumerate(results, start=1):
                student_id = student.get("student_id")
                student_name = student.get("student_full_name", "Noma'lum")
                keyboard.append([InlineKeyboardButton(f"{idx}. {student_name}", callback_data=f"student_{student_id}_{page}")])

            # Sahifa boshqaruvi tugmalari
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

    # 2. O'quvchi tugmasi bosilganda, uning murojaatlari va topic_name_uz larini ko'rsatish
    elif query.data.startswith("student_"):
        parts = query.data.split("_")
        student_id = int(parts[1])
        page = int(parts[2]) if len(parts) > 2 else 1

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
            student = next((s for s in results if s.get("student_id") == student_id), None)

            if not student:
                await query.edit_message_text(text="❌ O‘quvchi topilmadi yoki murojaatlar mavjud emas.")
                return

            requests_list = student.get("requests", [])
            if not requests_list:
                await query.edit_message_text(text="❌ Murojaatlar topilmadi.")
                return

            text_lines = [f"{student['student_full_name']} ga tegishli murojaatlar:\n"]
            for i, req in enumerate(requests_list, start=1):
                topics = req.get("topics_name_uz", [])
                topics_str = ", ".join(topics) if topics else "Mavzular mavjud emas"
                text_lines.append(f"{i}. {topics_str}")

            text = "\n".join(text_lines)

            keyboard = []
            for req in requests_list:
                help_request_id = req.get("id")
                student_name = student.get("student_full_name", "Oquvchi")
                # URL dagi bo'sh joyni %20 ga almashtiramiz
                url = f"https://iqmath.uz/dashboard/teacher/student-examples/{help_request_id}?student_name={student_name.replace(' ', '%20')}"
                keyboard.append([InlineKeyboardButton("🔗 Savolga o‘tish", url=url)])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup
            )

        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    # 3. Statistikalar tugmasi (hozircha demo)
    elif query.data == 'teacher_stats':
        await query.edit_message_text(text="📊 Murojaatlar statistikasi (demo)...")

    # 4. Cancel tugmasi
    elif query.data == "cancel":
        await query.edit_message_text(text="❌ Menyu bekor qilindi.")
