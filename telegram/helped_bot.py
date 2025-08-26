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

BOT_TOKEN = "TOKEN"
BACKEND_ASSIGN_API = "https://api.iqmath.uz/api/v1/func_student/student/telegram/assign-teacher/"
GET_STUDENT_TG_API = "https://api.iqmath.uz/api/v1/func_student/student/student_id/telegram_id/"

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

            # Inline tugmalarni yangilash: "Javob berish" -> "O‘zim javob qilaman"
            new_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("O‘zim javob qilaman", callback_data=f"takeover_{help_request_id}")]
            ])

            for log in logs:
                try:
                    if log.chat_id == query.message.chat_id:
                        # Javob berayotgan o‘qituvchiga xabar
                        await context.bot.send_message(
                            chat_id=log.chat_id,
                            text=f"✅ Siz bu savolni javoblayapsiz.",
                            reply_to_message_id=log.message_id
                        )
                    else:
                        # Boshqa o‘qituvchilarga bildirishnoma va yangi tugma
                        await context.bot.send_message(
                            chat_id=log.chat_id,
                            text=f"❗ Bu savolga hozirda <b>{teacher_name}</b> javob beryapti.",
                            parse_mode="HTML",
                            reply_to_message_id=log.message_id
                        )
                        await context.bot.edit_message_reply_markup(
                            chat_id=log.chat_id,
                            message_id=log.message_id,
                            reply_markup=new_markup
                        )
                except Exception as e:
                    logging.error(f"Edit/send xatolik: {e}")
        else:
            await query.message.reply_text(result.get("message", "❌ Xatolik yuz berdi"))

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O‘qituvchi studentga javob berishi"""
    if update.message.reply_to_message:
        text = update.message.text
        # Reply qilingan xabarda help_request_id saqlangani kerak
        # Masalan: reply_to_message.text ichida yoki bot_data orqali
        help_request_id = context.bot_data.get(f"help_id_{update.message.reply_to_message.message_id}")
        if help_request_id:
            # Backend orqali student telegram_id olish
            try:
                resp = requests.post(GET_STUDENT_TG_API, json={"student_id": help_request_id})
                student_data = resp.json()
                tg_id = student_data.get("telegram_id")
                if tg_id:
                    await context.bot.send_message(chat_id=tg_id, text=f"👨‍🏫 Javob: {text}")
                else:
                    await update.message.reply_text("❌ Student topilmadi.")
            except Exception as e:
                await update.message.reply_text("❌ Studentga yuborib bo‘lmadi.")
                logging.error(e)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply))
    print("✅ Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
