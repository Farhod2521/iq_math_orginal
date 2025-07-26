import os
import django
import logging
import requests
from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

# 1. Django sozlamalarini ulash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

# 2. Django modelni import qilish
from django_app.app_student.models import HelpRequestMessageLog

# 3. Bot va API sozlamalari
BOT_TOKEN = "7826335243:AAGXTZvtzJ8e8g35Hrx_Swy7mwmRPd3T7Po"
BACKEND_ASSIGN_API = "https://api.iqmath.uz/api/v1/func_student/student/telegram/assign-teacher/"

# 4. Log sozlash
logging.basicConfig(level=logging.INFO)

# 5. Django ORM ni async kontekstda ishlatish uchun
@sync_to_async
def get_logs(help_request_id):
    return list(HelpRequestMessageLog.objects.filter(help_request_id=help_request_id))

# 6. Callback tugma bosilganda ishlaydigan funksiya
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
            text = f"❗ Bu savolga hozirda <b>{teacher_name}</b> javob beryapti."

            # Hamma log'larni olish va xabarlarni yangilash
            logs = await get_logs(help_request_id)
            for log in logs:
                try:
                    await context.bot.edit_message_text(
                        chat_id=log.chat_id,
                        message_id=log.message_id,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=None  # ✅ tugmalarni o‘chiradi
                    )
                except Exception as e:
                    logging.error(f"❌ EditMessageText xatolik: {e}")
        else:
            await query.message.reply_text(result.get("message", "❌ Xatolik yuz berdi."))

# 7. Botni ishga tushurish
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("✅ Bot ishga tushdi... kutyapti.")
    app.run_polling()

if __name__ == "__main__":
    main()
