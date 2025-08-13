import os
import django
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from asgiref.sync import sync_to_async

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
            logs = await get_logs(help_request_id)

            url = f"https://iqmath.uz/dashboard/teacher/student-examples/{help_request_id}?student_name=Oquvchi"
            new_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Savolga o‘tish", url=url)]
            ])

            for log in logs:
                try:
                    # Faqat tugma bosgan o‘qituvchidan boshqalarga reply xabar
                    if log.chat_id != query.message.chat_id:
                        # Reply bilan xabar
                        await context.bot.send_message(
                            chat_id=log.chat_id,
                            text=f"❗ Bu savolga hozirda <b>{teacher_name}</b> javob beryapti.",
                            parse_mode="HTML",
                            reply_to_message_id=log.message_id
                        )

                    # Matnni yangilash (📥 -> 👨‍🏫)
                    original_text = context.bot_data.get(f"text_{log.message_id}", query.message.text)
                    new_text = original_text.replace("📥 Yangi savol!", f"👨‍🏫 O‘qituvchi: {teacher_name}")

                    await context.bot.edit_message_text(
                        chat_id=log.chat_id,
                        message_id=log.message_id,
                        text=new_text,
                        reply_markup=new_markup,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logging.error(f"❌ Edit/send xatolik: {e}")
        else:
            await query.message.reply_text(result.get("message", "❌ Xatolik yuz berdi"))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("✅ Bot ishga tushdi... kutyapti.")
    app.run_polling()

if __name__ == "__main__":
    main()
