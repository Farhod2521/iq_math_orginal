import os
import django
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from asgiref.sync import sync_to_async

# 🔧 Django sozlamasi
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

# 🧩 Django model
from django_app.app_student.models import HelpRequestMessageLog

# 🔑 Tashqi fayllar
from config import API_URL, BOT_TOKEN
from teacher import teacher_menu, handle_teacher_callback

# 🔗 API manzillar
BACKEND_ASSIGN_API = "https://api.iqmath.uz/api/v1/func_student/student/telegram/assign-teacher/"

# 📋 Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🧠 User start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    logger.info(f"Foydalanuvchi {telegram_id} /start buyrug'ini yubordi")

    try:
        response = requests.post(API_URL, json={"telegram_id": telegram_id}, timeout=5)

        if response.status_code == 200:
            data = response.json()
            context.user_data['user_info'] = data

            if data['role'] == 'teacher':
                await teacher_menu(update, context)
            elif data['role'] == 'student':
                await update.message.reply_text("Assalomu alaykum student! Xush kelibsiz!")
        else:
            await update.message.reply_text("Siz ro'yxatdan o'tmagansiz. Iltimos, avval ro'yxatdan o'ting.")
    except requests.exceptions.RequestException as e:
        logger.error(f"API so'rovida xatolik: {e}")
        await update.message.reply_text("Tizimda vaqtinchalik xatolik yuz berdi. Iltimos, keyinroq urunib ko‘ring.")

# 🔍 Loglarni olish (DB)
@sync_to_async
def get_logs(help_request_id):
    return list(HelpRequestMessageLog.objects.filter(help_request_id=help_request_id))

# 🧑‍🏫 O‘qituvchini tayinlash handler
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
            logger.error(f"❌ API xatolik: {e}")
            return

        if result.get("success"):
            teacher_name = result.get("teacher_name")
            logs = await get_logs(help_request_id)

            url = f"https://mentor.iqmath.uz/dashboard/teacher/student-examples/{help_request_id}?student_name=Oquvchi"
            new_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Savolga o‘tish", url=url)]
            ])

            for log in logs:
                try:
                    if log.chat_id != query.message.chat_id:
                        await context.bot.send_message(
                            chat_id=log.chat_id,
                            text=f"❗ Bu savolga hozirda <b>{teacher_name}</b> javob beryapti.",
                            parse_mode="HTML",
                            reply_to_message_id=log.message_id
                        )

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
                    logger.error(f"❌ Edit/send xatolik: {e}")
        else:
            await query.message.reply_text(result.get("message", "❌ Xatolik yuz berdi"))

# 🚨 Xatoliklarni logga yozish
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f'Xatolik: {context.error}', exc_info=context.error)

# 🏁 Botni ishga tushurish
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Komandalar
    application.add_handler(CommandHandler('start', start))

    # Callbacklar (ikkita handler ham ketma-ket ishlaydi)
    application.add_handler(CallbackQueryHandler(handle_teacher_callback))  # teacher.py dan
    application.add_handler(CallbackQueryHandler(handle_callback))  # assign_ uchun

    # Xatoliklar
    application.add_error_handler(error_handler)

    logger.info("✅ Bot ishga tushdi... kutyapti.")
    application.run_polling()

if __name__ == '__main__':
    main()
