import logging
import requests
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from django_app.app_student.models import HelpRequestMessageLog

BOT_TOKEN = "7826335243:AAGXTZvtzJ8e8g35Hrx_Swy7mwmRPd3T7Po"
BACKEND_ASSIGN_API = "https://api.iqmath.uz/api/v1/func_student/student/telegram/assign-teacher/"

logging.basicConfig(level=logging.INFO)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("assign_"):
        help_request_id = int(data.split("_")[1])
        telegram_id = query.from_user.id

        # Backendga so‘rov yuboramiz
        response = requests.post(BACKEND_ASSIGN_API, data={
            "help_request_id": help_request_id,
            "telegram_id": telegram_id
        })

        result = response.json()

        if result.get("success"):
            teacher_name = result.get("teacher_name")

            # Hamma o'qituvchilarga yuborilgan xabarlarni yangilaymiz
            logs = HelpRequestMessageLog.objects.filter(help_request_id=help_request_id)
            for log in logs:
                try:
                    text = f"❗ Bu savolga hozirda <b>{teacher_name}</b> javob beryapti."
                    await context.bot.edit_message_text(
                        chat_id=log.chat_id,
                        message_id=log.message_id,
                        text=text,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logging.error(f"❌ Edit xatolik: {e}")

        else:
            await query.message.reply_text(result.get("message", "Xatolik yuz berdi"))
