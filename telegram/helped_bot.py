import os
import django
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from asgiref.sync import sync_to_async

# Django sozlamasi
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django_app.app_student.models import HelpRequestMessageLog

BOT_TOKEN = "7826335243:AAGXTZvtzJ8e8g35Hrx_Swy7mwmRPd3T7Po"
BACKEND_ASSIGN_API = "https://api.iqmath.uz/api/v1/func_student/student/telegram/assign-teacher/"
TELEGRAM_ID_API = "https://api.iqmath.uz/api/v1/func_student/student/student_id/telegram_id/"

logging.basicConfig(level=logging.INFO)

@sync_to_async
def get_logs(help_request_id):
    return list(HelpRequestMessageLog.objects.filter(help_request_id=help_request_id))

@sync_to_async
def save_message_log(help_request_id, chat_id, message_id):
    log, created = HelpRequestMessageLog.objects.get_or_create(
        help_request_id=help_request_id,
        chat_id=chat_id,
        defaults={'message_id': message_id}
    )
    if not created:
        log.message_id = message_id
        log.save()
    return log

async def get_student_telegram_id(student_id):
    try:
        response = requests.post(TELEGRAM_ID_API, json={"student_id": student_id})
        result = response.json()
        return result.get("telegram_id")
    except Exception as e:
        logging.error(f"❌ Telegram ID olishda xatolik: {e}")
        return None

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("assign_"):
        help_request_id = int(data.split("_")[1])
        telegram_id = query.from_user.id
        
        try:
            response = requests.post(BACKEND_ASSIGN_API, data={
                "help_request_id": help_request_id,
                "telegram_id": telegram_id
            })
            result = response.json()
        except Exception as e:
            await query.message.reply_text("❌ Server bilan bog'lanib bo'lmadi.")
            logging.error(f"❌ API xatolik: {e}")
            return
        
        if result.get("success"):
            teacher_name = result.get("teacher_name")
            student_id = result.get("student_id")
            
            # O'qituvchi ID sini contextda saqlaymiz
            context.user_data['active_assignment'] = {
                'help_request_id': help_request_id,
                'student_id': student_id,
                'teacher_name': teacher_name
            }
            
            logs = await get_logs(help_request_id)
            url = f"https://iqmath.uz/dashboard/teacher/student-examples/{help_request_id}?student_name=Oquvchi"
            
            # Yangi tugmalar
            new_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("👨‍🏫 Siz javob berayapsiz", callback_data=f"assigned_{help_request_id}")],
                [InlineKeyboardButton("🔗 Savolga o'tish", url=url)]
            ])
            
            for log in logs:
                try:
                    # Faqat boshqa o'qituvchilarga xabar yuboramiz
                    if log.chat_id != query.message.chat_id:
                        # Boshqa o'qituvchilar uchun yangi tugmalar
                        other_teachers_markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton("👨‍🏫 Javob berilmoqda", callback_data=f"already_assigned_{help_request_id}")],
                            [InlineKeyboardButton("🔗 Savolga o'tish", url=url)]
                        ])
                        
                        # Matnni yangilash
                        original_text = query.message.text
                        new_text = original_text.replace("📥 Yangi savol!", f"👨‍🏫 {teacher_name} javob beryapti")
                        
                        await context.bot.edit_message_text(
                            chat_id=log.chat_id,
                            message_id=log.message_id,
                            text=new_text,
                            reply_markup=other_teachers_markup,
                            parse_mode="HTML"
                        )
                    else:
                        # Javob bergan o'qituvchi uchun matnni yangilash
                        original_text = query.message.text
                        new_text = original_text.replace("📥 Yangi savol!", "✅ Siz javob berayapsiz")
                        
                        await context.bot.edit_message_text(
                            chat_id=log.chat_id,
                            message_id=log.message_id,
                            text=new_text,
                            reply_markup=new_markup,
                            parse_mode="HTML"
                        )
                        
                        # Qo'shimcha yo'riqnoma xabari
                        await query.message.reply_text(
                            f"✅ Endi siz bu savolga javob berayapsiz.\n\n"
                            f"Talabaga javob yuborish uchun shu xabarga 'reply' qilib yozing yoki to'g'ridan-to'g'ri yozib, "
                            f"keyin 'Javobni yuborish' tugmasini bosing.",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_answer_{help_request_id}")]
                            ])
                        )
                        
                except Exception as e:
                    logging.error(f"❌ Xabar yangilashda xatolik: {e}")
        else:
            await query.message.reply_text(result.get("message", "❌ Xatolik yuz berdi"))
    
    elif data.startswith("send_answer_"):
        help_request_id = int(data.split("_")[2])
        assignment = context.user_data.get('active_assignment', {})
        
        if assignment.get('help_request_id') != help_request_id:
            await query.message.reply_text("❌ Siz bu savolga javob berish huquqiga ega emassiz.")
            return
        
        student_id = assignment.get('student_id')
        student_telegram_id = await get_student_telegram_id(student_id)
        
        if not student_telegram_id:
            await query.message.reply_text("❌ Talabaning Telegram ID sini topib bo'lmadi.")
            return
        
        # Foydalanuvchi javobini olish
        if 'answer_text' not in context.user_data:
            await query.message.reply_text("❌ Avval javob matnini yuboring.")
            return
        
        answer_text = context.user_data['answer_text']
        
        # Talabaga javobni yuborish
        try:
            await context.bot.send_message(
                chat_id=student_telegram_id,
                text=f"👨‍🏫 O'qituvchingizdan javob:\n\n{answer_text}"
            )
            await query.message.reply_text("✅ Javobingiz talabaga yuborildi.")
            
            # Contextni tozalash
            del context.user_data['answer_text']
            del context.user_data['active_assignment']
            
        except Exception as e:
            logging.error(f"❌ Javob yuborishda xatolik: {e}")
            await query.message.reply_text("❌ Javob yuborishda xatolik yuz berdi.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Agar reply qilingan bo'lsa va active assignment bo'lsa
    if update.message.reply_to_message and 'active_assignment' in context.user_data:
        reply_text = update.message.reply_to_message.text or update.message.reply_to_message.caption
        
        # Agar reply qilingan xabar javob yuborish yo'riqnomasi bo'lsa
        if reply_text and "savolga javob berayapsiz" in reply_text:
            context.user_data['answer_text'] = update.message.text
            await update.message.reply_text(
                "✅ Javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", 
                     callback_data=f"send_answer_{context.user_data['active_assignment']['help_request_id']}")]
                ])
            )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot ishga tushdi... kutyapti.")
    app.run_polling()

if __name__ == "__main__":
    main()