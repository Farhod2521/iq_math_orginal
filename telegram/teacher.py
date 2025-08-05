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
    await update.message.reply_text(
        f"👋 Assalomu alaykum {full_name}!\nQuyidagi menyudan foydalaning:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# Callback handler
async def handle_teacher_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id
    page = 1

    # Sahifalash tugmalari: next/prev
    if query.data.startswith("next_page_"):
        page = int(query.data.split("_")[-1]) + 1
    elif query.data.startswith("prev_page_"):
        page = int(query.data.split("_")[-1]) - 1

    # 1) Murojaatlar ro'yxatini ko'rsatish
    if query.data in ['teacher_applications'] or query.data.startswith(("next_page_", "prev_page_")):
        try:
            resp = requests.post(API_URL, json={"telegram_id": telegram_id}, params={"page": page}, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            has_prev = data.get("previous") is not None
            has_next = data.get("next") is not None

            # Matn
            lines = [f"{i+1}. {s['student_full_name']} 📩 {len(s.get('requests', []))} ta murojaat"
                     for i, s in enumerate(results)]
            text = (
                f"📬 Sizga kelgan murojaatlar ro'yxati (sahifa {page}):\n\n"
                + ("\n".join(lines) if lines else "Murojaatlar topilmadi.")
            )

            # Tugmalar: har bir o'quvchi uchun
            kb = [[
                InlineKeyboardButton(
                    f"{i+1}. {s['student_full_name']}",
                    callback_data=f"student_{s['student_id']}_{page}"
                )
            ] for i, s in enumerate(results)]

            # Sahifa nav
            nav = []
            if has_prev: nav.append(InlineKeyboardButton("⬅️", callback_data=f"prev_page_{page}"))
            nav.append(InlineKeyboardButton("❌", callback_data="cancel"))
            if has_next: nav.append(InlineKeyboardButton("➡️", callback_data=f"next_page_{page}"))
            kb.append(nav)

            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    # 2) O'quvchi tanlandi: uning murojaatlari — faqat raqamlangan mavzular
    elif query.data.startswith("student_"):
        _, stu_id, pg = query.data.split("_")
        stu_id, pg = int(stu_id), int(pg)

        try:
            resp = requests.post(API_URL, json={"telegram_id": telegram_id}, params={"page": pg}, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            student = next((s for s in data.get("results", []) if s['student_id']==stu_id), None)

            if not student or not student.get("requests"):
                await query.edit_message_text(text="❌ Murojaatlar topilmadi.")
                return

            # Matn va raqamli tugmalar
            text = f"{student['student_full_name']} ga tegishli murojaatlar:\n\n"
            kb = []
            for i, req in enumerate(student['requests'], start=1):
                topics = req.get("topics_name_uz", [])
                text += f"{i}. {', '.join(topics) if topics else 'Mavzular mavjud emas'}\n"
                kb.append([InlineKeyboardButton(str(i), callback_data=f"topic_{req['id']}_{stu_id}")])

            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    # 3) Mavzu (raqam) tanlandi: batafsil ma'lumot (Natija yo'q)
    elif query.data.startswith("topic_"):
        _, help_id, stu_id = query.data.split("_")
        help_id, stu_id = int(help_id), int(stu_id)
        try:
            resp = requests.post(API_URL, json={"telegram_id": telegram_id}, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            student = next((s for s in data.get("results", []) if s['student_id']==stu_id), None)
            req = next((r for r in (student or {}).get("requests", []) if r['id']==help_id), None)

            if not student or not req:
                await query.edit_message_text(text="❌ Ma'lumot topilmadi.")
                return

            # Batafsil ma'lumot
            lines = [
                f"👤 O‘quvchi: {student['student_full_name']}",
                f"🆔 Savol ID: {req['id']}",
                f"📚 Sinf: {req.get('class_uz', '—')}",
                f"🕒 Yaratilgan: {req.get('created_at', '—')}",
                f"🏷 Status: {req.get('status', '—')}",
                f"⭐ Ball: {req.get('ball', 0)}",
            ]

            kb = [
                [InlineKeyboardButton("✅ Javob berish", callback_data=f"answer_{help_id}_{stu_id}")],
                [InlineKeyboardButton(
                    "🔗 Savolga o‘tish",
                    url=f"https://iqmath.uz/dashboard/teacher/student-examples/{help_id}?student_name={student['student_full_name'].replace(' ','%20')}"
                )]
            ]

            await query.edit_message_text(
                text="\n".join(lines),
                reply_markup=InlineKeyboardMarkup(kb)
            )
        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    # 4) Statistikalar (demo)
    elif query.data == 'teacher_stats':
        await query.edit_message_text(text="📊 Murojaatlar statistikasi (demo)...")

    # 5) Cancel
    elif query.data == "cancel":
        await query.edit_message_text(text="❌ Menyu bekor qilindi.")
