import requests
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler

API_URL = "https://api.iqmath.uz/api/v1/func_teacher/teacher-independent/telegram-list/"

async def teacher_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data.get('user_info')
    if not user_data or 'data' not in user_data or 'full_name' not in user_data['data']:
        await update.message.reply_text("❌ Foydalanuvchi ma'lumotlari topilmadi. Iltimos, qaytadan kiriting.")
        return

    full_name = user_data['data']['full_name']
    keyboard = [
        [InlineKeyboardButton("📬 Menga kelgan murojaatlar", callback_data='teacher_applications')],
        [InlineKeyboardButton("📊 Murojaatlar statistikasi", callback_data='teacher_stats')]
    ]
    await update.message.reply_text(
        f"👋 Assalomu alaykum {full_name}!\nQuyidagi menyudan foydalaning:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def answer_help_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        # Parse callback data
        _, help_id, stu_id = query.data.split("_")
        help_id, stu_id = int(help_id), int(stu_id)
        
        # Store the original message ID for possible later editing
        original_message_id = query.message.message_id
        
        # Check student's Telegram ID via API
        try:
            response = requests.get(
                f"https://api.iqmath.uz/api/v1/func_teacher/teacher/help-request/{help_id}/telegram-id/",
                headers={"Authorization": f"Token {context.user_data.get('token')}"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            telegram_id = data.get("telegram_id")
            if not telegram_id:
                # Student not registered on Telegram
                await context.bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=original_message_id,
                    text="❌ Ushbu o'quvchi hali Telegramdan ro'yxatdan o'tmagan.\n\n"
                         "Iltimos, platforma orqali javob bering yoki o'quvchiga Telegramda ro'yxatdan o'tishni aytib qo'ying.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"topic_{help_id}_{stu_id}")]
                    ])
                )
                return
            
            # Get student name from message text
            message_lines = query.message.text.split('\n')
            student_name = message_lines[0].replace("👤 O'quvchi: ", "") if message_lines else "Noma'lum"
            
            # Prepare for receiving answer
            context.user_data.update({
                'waiting_for_answer': True,
                'current_help_id': help_id,
                'current_stu_id': stu_id,
                'student_telegram_id': telegram_id,
                'original_message_id': original_message_id
            })
            
            # Delete the original message to clean up the chat
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=original_message_id
            )
            
            # Send new message prompting for answer
            prompt_message = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"✍️ Savol ID: {help_id} uchun javobingizni yozing:\n\n"
                     f"O'quvchi: {student_name}\n\n"
                     f"Yuborishingiz mumkin:\n"
                     f"- Matn\n"
                     f"- Rasm (screenshot)\n"
                     f"- Ovozli xabar\n\n"
                     f"Javobingiz avtomatik ravishda o'quvchiga yuboriladi.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Bekor qilish", callback_data=f"cancel_answer_{help_id}_{stu_id}")]
                ])
            )
            
            # Store the prompt message ID for possible cancellation
            context.user_data['prompt_message_id'] = prompt_message.message_id
            
        except requests.exceptions.RequestException as e:
            await context.bot.edit_message_text(
                chat_id=query.message.chat_id,
                message_id=original_message_id,
                text=f"❌ Telegram ID ni tekshirishda xatolik yuz berdi. Iltimos, keyinroq urunib ko'ring.\n\nXatolik: {str(e)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"topic_{help_id}_{stu_id}")]
                ])
            )
            
    except Exception as e:
        error_message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"❌ Kutilmagan xatolik yuz berdi: {str(e)}\n\nIltimos, qaytadan urunib ko'ring."
        )
        await asyncio.sleep(5)
        await context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=error_message.message_id
        )

async def handle_media_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_for_answer', False):
        return
    
    help_id = context.user_data['current_help_id']
    stu_id = context.user_data['current_stu_id']
    student_telegram_id = context.user_data.get('student_telegram_id')
    
    try:
        # Handle photo
        if update.message.photo:
            photo = update.message.photo[-1]
            caption = update.message.caption or f"Savol ID: {help_id} uchun javob"
            
            # Send confirmation to teacher
            await update.message.reply_text(
                f"✅ Rasm javobi qabul qilindi va o'quvchiga yuborildi!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"topic_{help_id}_{stu_id}")]
                ])
            )
            
            # Forward to student if available
            if student_telegram_id:
                try:
                    await context.bot.send_photo(
                        chat_id=student_telegram_id,
                        photo=photo.file_id,
                        caption=f"📬 Sizning savolingizga javob (ID: {help_id})\n\n{caption}"
                    )
                except Exception as e:
                    await update.message.reply_text(
                        f"⚠️ Javob o'quvchiga yuborilmadi. O'quvchi botni bloklagan bo'lishi mumkin."
                    )
        
        # Handle voice
        elif update.message.voice:
            voice = update.message.voice
            caption = update.message.caption or f"Savol ID: {help_id} uchun javob"
            
            # Send confirmation to teacher
            await update.message.reply_text(
                f"✅ Ovozli javob qabul qilindi va o'quvchiga yuborildi!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"topic_{help_id}_{stu_id}")]
                ]))
            
            # Forward to student if available
            if student_telegram_id:
                try:
                    await context.bot.send_voice(
                        chat_id=student_telegram_id,
                        voice=voice.file_id,
                        caption=f"📬 Sizning savolingizga javob (ID: {help_id})\n\n{caption}"
                    )
                except Exception as e:
                    await update.message.reply_text(
                        f"⚠️ Javob o'quvchiga yuborilmadi. O'quvchi botni bloklagan bo'lishi mumkin."
                    )
        
        # Clean up
        context.user_data.pop('waiting_for_answer', None)
        context.user_data.pop('current_help_id', None)
        context.user_data.pop('current_stu_id', None)
        context.user_data.pop('student_telegram_id', None)
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Javobingizni qabul qilishda xatolik yuz berdi: {e}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"topic_{help_id}_{stu_id}")]
            ])
        )

async def receive_answer_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_for_answer'):
        await update.message.reply_text("⚠️ Iltimos, avval 'Javob berish' tugmasini bosing")
        return

    help_id = context.user_data['current_help_id']
    stu_id = context.user_data['current_stu_id']
    answer_text = update.message.text
    telegram_id = context.user_data.get('student_telegram_id')
    
    try:
        # 1. First send confirmation to teacher
        await update.message.reply_text(
            f"✅ Javobingiz qabul qilindi!\n"
            f"Savol ID: {help_id}\n"
            f"Javob: {answer_text[:200]}" + ("..." if len(answer_text) > 200 else ""),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"topic_{help_id}_{stu_id}")]
            ])
        )
        
        # 2. Send answer to student if Telegram ID exists
        if telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"📬 Sizning savolingizga javob:\n\n"
                         f"Savol ID: {help_id}\n"
                         f"Javob: {answer_text}"
                )
                await update.message.reply_text("✉️ Javob o'quvchiga muvaffaqiyatli yuborildi!")
            except Exception as e:
                await update.message.reply_text(
                    f"⚠️ Javob o'quvchiga yuborilmadi. O'quvchi botni bloklagan bo'lishi mumkin."
                )
        else:
            await update.message.reply_text(
                "ℹ️ O'quvchining Telegram ID si topilmadi. Platforma orqali javob berishingiz mumkin."
            )
        
        # 3. Clean up state
        context.user_data.pop('waiting_for_answer', None)
        context.user_data.pop('current_help_id', None)
        context.user_data.pop('current_stu_id', None)
        context.user_data.pop('student_telegram_id', None)
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Xatolik yuz berdi: {str(e)}\nIltimos, qaytadan urunib ko'ring."
        )

async def handle_teacher_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id
    page = 1

    # Sahifalash tugmalari
    if query.data.startswith("next_page_"):
        page = int(query.data.split("_")[-1]) + 1
    elif query.data.startswith("prev_page_"):
        page = int(query.data.split("_")[-1]) - 1

    # Murojaatlar ro'yxati
    if query.data in ['teacher_applications'] or query.data.startswith(("next_page_", "prev_page_")):
        try:
            resp = requests.post(
                API_URL,
                json={"telegram_id": telegram_id},
                headers={"Authorization": f"Token {context.user_data.get('token')}"},
                params={"page": page},
                timeout=5
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            has_prev = data.get("previous") is not None
            has_next = data.get("next") is not None

            lines = [f"{i+1}. {s['student_full_name']} 📩 {len(s.get('requests', []))} ta murojaat"
                     for i, s in enumerate(results)]
            text = (
                f"📬 Sizga kelgan murojaatlar ro'yxati (sahifa {page}):\n\n"
                + ("\n".join(lines) if lines else "Murojaatlar topilmadi.")
            )

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

            nav = []
            if has_prev: nav.append(InlineKeyboardButton("⬅️", callback_data=f"prev_page_{page}"))
            nav.append(InlineKeyboardButton("❌", callback_data="cancel"))
            if has_next: nav.append(InlineKeyboardButton("➡️", callback_data=f"next_page_{page}"))
            kb.append(nav)

            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    # O'quvchi tanlandi
    elif query.data.startswith("student_"):
        _, stu_id, pg = query.data.split("_")
        stu_id, pg = int(stu_id), int(pg)

        try:
            resp = requests.post(
                API_URL,
                json={"telegram_id": telegram_id},
                headers={"Authorization": f"Token {context.user_data.get('token')}"},
                params={"page": pg},
                timeout=5
            )
            resp.raise_for_status()
            data = resp.json()
            student = next((s for s in data.get("results", []) if s['student_id']==stu_id), None)

            if not student or not student.get("requests"):
                await query.edit_message_text(text="❌ Murojaatlar topilmadi.")
                return

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

            kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data=f"back_to_students_{pg}")])
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    # Mavzu tanlandi
    elif query.data.startswith("topic_"):
        _, help_id, stu_id = query.data.split("_")
        help_id, stu_id = int(help_id), int(stu_id)
        try:
            resp = requests.post(
                API_URL,
                json={"telegram_id": telegram_id},
                headers={"Authorization": f"Token {context.user_data.get('token')}"},
                timeout=5
            )
            resp.raise_for_status()
            data = resp.json()
            student = next((s for s in data.get("results", []) if s['student_id']==stu_id), None)
            req = next((r for r in (student or {}).get("requests", []) if r['id']==help_id), None)

            if not student or not req:
                await query.edit_message_text(text="❌ Ma'lumot topilmadi.")
                return

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

    # Javob berish
    elif query.data.startswith("answer_"):
        await answer_help_request(update, context)

    # Bekor qilish
    elif query.data.startswith("cancel_answer_"):
        _, _, help_id, stu_id = query.data.split("_")
        help_id, stu_id = int(help_id), int(stu_id)
        
        context.user_data.pop('waiting_for_answer', None)
        context.user_data.pop('current_help_id', None)
        context.user_data.pop('current_stu_id', None)
        context.user_data.pop('student_telegram_id', None)
        
        await query.edit_message_text(
            text="❌ Javob berish bekor qilindi.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"topic_{help_id}_{stu_id}")]
            ])
        )

    # Orqaga qaytish
    elif query.data.startswith("back_to_topics_"):
        stu_id = int(query.data.split("_")[-1])
        try:
            resp = requests.post(
                API_URL,
                json={"telegram_id": telegram_id},
                headers={"Authorization": f"Token {context.user_data.get('token')}"},
                timeout=5
            )
            resp.raise_for_status()
            data = resp.json()
            student = next((s for s in data.get("results", []) if s['student_id']==stu_id), None)

            if not student or not student.get("requests"):
                await query.edit_message_text(text="❌ Murojaatlar topilmadi.")
                return

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

            kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data=f"back_to_students_1")])
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    elif query.data.startswith("back_to_students_"):
        page = int(query.data.split("_")[-1])
        try:
            resp = requests.post(
                API_URL,
                json={"telegram_id": telegram_id},
                headers={"Authorization": f"Token {context.user_data.get('token')}"},
                params={"page": page},
                timeout=5
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            has_prev = data.get("previous") is not None
            has_next = data.get("next") is not None

            lines = [f"{i+1}. {s['student_full_name']} 📩 {len(s.get('requests', []))} ta murojaat"
                     for i, s in enumerate(results)]
            text = (
                f"📬 Sizga kelgan murojaatlar ro'yxati (sahifa {page}):\n\n"
                + ("\n".join(lines) if lines else "Murojaatlar topilmadi.")
            )

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

            nav = []
            if has_prev: nav.append(InlineKeyboardButton("⬅️", callback_data=f"prev_page_{page}"))
            nav.append(InlineKeyboardButton("❌", callback_data="cancel"))
            if has_next: nav.append(InlineKeyboardButton("➡️", callback_data=f"next_page_{page}"))
            kb.append(nav)

            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            await query.edit_message_text(text=f"❌ Xatolik yuz berdi: {e}")

    # Statistikalar
    elif query.data == 'teacher_stats':
        await query.edit_message_text(text="📊 Murojaatlar statistikasi (demo)...")

    # Cancel
    elif query.data == "cancel":
        await query.edit_message_text(text="❌ Menyu bekor qilindi.")

def setup_handlers(application):
    application.add_handler(CallbackQueryHandler(
        handle_teacher_callback, 
        pattern="^(teacher_applications|teacher_stats|student_|topic_|answer_|cancel_answer_|back_to_|prev_page_|next_page_|cancel)"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_answer_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_media_answer))
    application.add_handler(MessageHandler(filters.VOICE, handle_media_answer))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^/'),
        receive_answer_text
    ))
    
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VOICE,
        handle_media_answer
    ))