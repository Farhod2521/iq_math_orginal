import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler

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

# Javob yozish uchun handler
async def answer_help_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Callback ma'lumotlarini ajratib olish
    _, help_id, stu_id = query.data.split("_")
    help_id, stu_id = int(help_id), int(stu_id)
    
    # Telegram ID ni tekshirish uchun API so'rov
    try:
        response = requests.get(
            f"https://api.iqmath.uz/api/v1/func_teacher/teacher/help-request/{help_id}/telegram-id/"
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("telegram_id", 0) == 0:
            await query.edit_message_text(
                text="❌ Ushbu o'quvchi hali Telegramdan ro'yxatdan o'tmagan.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"topic_{help_id}_{stu_id}")]
                ])
            )
        else:
            # Foydalanuvchiga javob yozish uchun so'rov yuborish
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✍️ Endi javobingizni yozing (Savol ID: {help_id}):"
            )
            # Javob matnini kutib olish uchun context.user_data ga saqlaymiz
            context.user_data['waiting_for_answer'] = True
            context.user_data['current_help_id'] = help_id
            context.user_data['current_stu_id'] = stu_id
            
    except Exception as e:
        await query.edit_message_text(
            text=f"❌ Xatolik yuz berdi: {e}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"topic_{help_id}_{stu_id}")]
            ])
        )

# Javob matnini qabul qilish handleri
# Javob matnini qabul qilish handleri (yangilangan versiyasi)
async def receive_answer_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_answer', False):
        help_id = context.user_data['current_help_id']
        stu_id = context.user_data['current_stu_id']
        answer_text = update.message.text
        
        try:
            # Bu yerda APIga javobni yuborish kodi bo'lishi kerak
            # Lekin hozircha demo uchun faqat xabarni ko'rsatamiz
            
            # Avval foydalanuvchiga javob qabul qilindi degan xabar
            sent_message = await update.message.reply_text(
                f"✅ Javobingiz qabul qilindi va o'quvchiga yuborildi!\n"
                f"Savol ID: {help_id}\n"
                f"Javobingiz: {answer_text[:200]}...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"topic_{help_id}_{stu_id}")]
                ]))
            
            # Keyin asl javobni o'quvchiga yuborish (agar telegram_id mavjud bo'lsa)
            telegram_id_response = requests.get(
                f"https://api.iqmath.uz/api/v1/func_teacher/teacher/help-request/{help_id}/telegram-id/"
            )
            
            if telegram_id_response.status_code == 200:
                data = telegram_id_response.json()
                student_telegram_id = data.get("telegram_id")
                
                if student_telegram_id and student_telegram_id != 0:
                    try:
                        await context.bot.send_message(
                            chat_id=student_telegram_id,
                            text=f"📬 Sizning savolingizga javob:\n\n"
                                 f"Savol ID: {help_id}\n"
                                 f"Javob: {answer_text}"
                        )
                    except Exception as e:
                        print(f"O'quvchiga javob yuborishda xatolik: {e}")
                        await sent_message.edit_text(
                            text=f"✅ Javobingiz qabul qilindi, lekin o'quvchiga yuborishda xatolik yuz berdi.\n"
                                 f"Savol ID: {help_id}\n"
                                 f"Xatolik: {str(e)}",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"topic_{help_id}_{stu_id}")]
                            ])
                        )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Javobingizni saqlashda xatolik yuz berdi: {e}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"topic_{help_id}_{stu_id}")]
                ])
            )
        
        # Holatni tozalash
        context.user_data.pop('waiting_for_answer', None)
        context.user_data.pop('current_help_id', None)
        context.user_data.pop('current_stu_id', None)

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

            # Tugmalar: har bir o'quvchi uchun (5 tadan qatorlarga joylashtirish)
            kb = []
            row = []
            for i, s in enumerate(results):
                row.append(InlineKeyboardButton(
                    f"{i+1}",
                    callback_data=f"student_{s['student_id']}_{page}"
                ))
                if len(row) == 5 or i == len(results) - 1:
                    kb.append(row)
                    row = []

            # Sahifa nav
            nav = []
            if has_prev: nav.append(InlineKeyboardButton("⬅️", callback_data=f"prev_page_{page}"))
            nav.append(InlineKeyboardButton("❌", callback_data="cancel"))
            if has_next: nav.append(InlineKeyboardButton("➡️", callback_data=f"next_page_{page}"))
            kb.append(nav)

            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    # 2) O'quvchi tanlandi: uning murojaatlari — faqat raqamlangan mavzular (5 tadan qatorlarga joylashtirish)
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

            # Matn va raqamli tugmalar (5 tadan qatorlarga joylashtirish)
            text = f"{student['student_full_name']} ga tegishli murojaatlar:\n\n"
            kb = []
            row = []
            for i, req in enumerate(student['requests'], start=1):
                topics = req.get("topics_name_uz", [])
                text += f"{i}. {', '.join(topics) if topics else 'Mavzular mavjud emas'}\n"
                row.append(InlineKeyboardButton(str(i), callback_data=f"topic_{req['id']}_{stu_id}"))
                if len(row) == 5 or i == len(student['requests']):
                    kb.append(row)
                    row = []

            # Orqaga qaytish tugmasi
            kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data=f"back_to_students_{pg}")])

            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    # 3) Mavzu (raqam) tanlandi: batafsil ma'lumot
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
                f"👤 O'quvchi: {student['student_full_name']}",
                f"🆔 Savol ID: {req['id']}",
                f"📚 Sinf: {req.get('class_uz', '—')}",
                f"🕒 Yaratilgan: {req.get('created_at', '—')}",
                f"🏷 Status: {req.get('status', '—')}",
                f"⭐ Ball: {req.get('ball', 0)}",
            ]

            kb = [
                [InlineKeyboardButton("✅ Javob berish", callback_data=f"answer_{help_id}_{stu_id}")],
                [InlineKeyboardButton(
                    "🔗 Savolga o'tish",
                    url=f"https://iqmath.uz/dashboard/teacher/student-examples/{help_id}?student_name={student['student_full_name'].replace(' ','%20')}"
                )],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"back_to_topics_{stu_id}")]
            ]

            await query.edit_message_text(
                text="\n".join(lines),
                reply_markup=InlineKeyboardMarkup(kb)
            )
        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    # 4) Javob berish handleri
    elif query.data.startswith("answer_"):
        await answer_help_request(update, context)

    # 5) Orqaga qaytish handlerlari
    elif query.data.startswith("back_to_topics_"):
        stu_id = int(query.data.split("_")[-1])
        try:
            resp = requests.post(API_URL, json={"telegram_id": telegram_id}, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            student = next((s for s in data.get("results", []) if s['student_id']==stu_id), None)

            if not student or not student.get("requests"):
                await query.edit_message_text(text="❌ Murojaatlar topilmadi.")
                return

            # Matn va raqamli tugmalar (5 tadan qatorlarga joylashtirish)
            text = f"{student['student_full_name']} ga tegishli murojaatlar:\n\n"
            kb = []
            row = []
            for i, req in enumerate(student['requests'], start=1):
                topics = req.get("topics_name_uz", [])
                text += f"{i}. {', '.join(topics) if topics else 'Mavzular mavjud emas'}\n"
                row.append(InlineKeyboardButton(str(i), callback_data=f"topic_{req['id']}_{stu_id}"))
                if len(row) == 5 or i == len(student['requests']):
                    kb.append(row)
                    row = []

            # Orqaga qaytish tugmasi (o'quvchilar ro'yxatiga)
            kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data=f"back_to_students_1")])

            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    elif query.data.startswith("back_to_students_"):
        page = int(query.data.split("_")[-1])
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

            # Tugmalar: har bir o'quvchi uchun (5 tadan qatorlarga joylashtirish)
            kb = []
            row = []
            for i, s in enumerate(results):
                row.append(InlineKeyboardButton(
                    f"{i+1}",
                    callback_data=f"student_{s['student_id']}_{page}"
                ))
                if len(row) == 5 or i == len(results) - 1:
                    kb.append(row)
                    row = []

            # Sahifa nav
            nav = []
            if has_prev: nav.append(InlineKeyboardButton("⬅️", callback_data=f"prev_page_{page}"))
            nav.append(InlineKeyboardButton("❌", callback_data="cancel"))
            if has_next: nav.append(InlineKeyboardButton("➡️", callback_data=f"next_page_{page}"))
            kb.append(nav)

            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    # 6) Statistikalar (demo)
    elif query.data == 'teacher_stats':
        await query.edit_message_text(text="📊 Murojaatlar statistikasi (demo)...")

    # 7) Cancel
    elif query.data == "cancel":
        await query.edit_message_text(text="❌ Menyu bekor qilindi.")

# Application builderda handlerlarni qo'shish
def setup_handlers(application):
    application.add_handler(CallbackQueryHandler(
        handle_teacher_callback, 
        pattern="^(teacher_applications|teacher_stats|student_|topic_|answer_|back_to_|prev_page_|next_page_|cancel)"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_answer_text))