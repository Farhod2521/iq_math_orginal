import os
import django
import logging
import requests
from asgiref.sync import sync_to_async
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

# Django sozlamasi
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django_app.app_student.models import HelpRequestMessageLog

BOT_TOKEN = "7826335243:AAGXTZvtzJ8e8g35Hrx_Swy7mwmRPd3T7Po"
BACKEND_ASSIGN_API = "https://api.iqmath.uz/api/v1/func_student/student/telegram/assign-teacher/"

logging.basicConfig(level=logging.INFO)

@sync_to_async
def get_logs(help_request_id):
    return list(HelpRequestMessageLog.objects.filter(help_request_id=help_request_id))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("assign_"):
        help_request_id = int(data.split("_")[1])
        telegram_id = query.from_user.id

        # Backendga so‘rov yuborish
        try:
            response = requests.post(BACKEND_ASSIGN_API, data={
                "help_request_id": help_request_id,
                "telegram_id": telegram_id
            })
            result = response.json()
        except Exception as e:
            await query.message.reply_text("❌ Server bilan bog‘lanib bo‘lmadi.")
            logging.error(f"❌ API xatolik: {e}")
            return

        if result.get("success"):
            teacher_name = result.get("teacher_name")

            # 🔘 Faqat "🔗 Savolga o‘tish" tugmasini qoldiramiz
            student_name_encoded = ""  # optional: if kerak bo‘lsa, backenddan qaytar
            url = f"https://mentor.iqmath.uz/dashboard/teacher/student-examples/{help_request_id}?student_name=Oquvchi"

            new_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Savolga o‘tish", url=url)]
            ])

            # Har bir yuborilgan xabar uchun tugmalarni yangilaymiz
            logs = await get_logs(help_request_id)
            for log in logs:
                try:
                    await context.bot.edit_message_reply_markup(
                        chat_id=log.chat_id,
                        message_id=log.message_id,
                        reply_markup=new_markup  # faqat "🔗" tugma qoladi
                    )
                except Exception as e:
                    logging.error(f"❌ Tugma o‘zgartirish xatoligi: {e}")
        else:
            await query.message.reply_text(result.get("message", "❌ Xatolik yuz berdi."))

# Botni ishga tushirish
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("✅ Bot ishga tushdi... kutyapti.")
    app.run_polling()

if __name__ == "__main__":
    main()
