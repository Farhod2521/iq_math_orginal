import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

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

        response = requests.post(BACKEND_ASSIGN_API, data={
            "help_request_id": help_request_id,
            "telegram_id": telegram_id
        })

        result = response.json()

        if result.get("success"):
            teacher_name = result.get("teacher_name")

            # Savolga javob berilganligini bildiruvchi matn
            text = f"❗ Bu savolga hozirda <b>{teacher_name}</b> javob beryapti."

            try:
                await context.bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    text=text,
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Xatolik: {e}")
        else:
            await query.message.reply_text(result.get("message", "Xatolik yuz berdi"))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("✅ Bot ishga tushdi... kutyapti.")
    app.run_polling()

if __name__ == "__main__":
    main()
