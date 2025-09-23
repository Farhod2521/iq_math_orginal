import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from config import API_URL, BOT_TOKEN
from teacher import teacher_menu, handle_teacher_callback

# Log konfiguratsiyasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)



API_URL = "https://api.iqmath.uz/api/v1/func_student/id-independent"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    logger.info(f"Foydalanuvchi {telegram_id} /start buyrug'ini yubordi")

    args = context.args
    if args:
        payload = args[0]  # masalan "200_83"
        if "_" in payload:
            try:
                help_request_id, student_id = payload.split("_")
            except ValueError:
                await update.message.reply_text("Xato payload formati.")
                return

            # API chaqiramiz
            try:
                resp = requests.get(
                    f"{API_URL}/{help_request_id}/",
                    timeout=5
                )
                
                if resp.status_code == 200:
                    
                    data = resp.json()
                    subject = data.get("subject_name_uz")
                    chapters = ", ".join(data.get("chapter_name_uz", []))
                    topics = ", ".join(data.get("topic_name_uz", []))

                    # result massivdan 1-chi elementni olamiz
                    result = data.get("result", [])
                    if result:
                        result = result[0]
                        score = result.get("score", 0)
                        total_answers = result.get("total_answers", 0)
                        correct_answers = result.get("correct_answers", 0)
                        # Foizni o'zimiz hisoblaymiz
                        percentage = (correct_answers / total_answers * 100) if total_answers else 0
                    else:
                        score = total_answers = correct_answers = percentage = 0

                    # Xabarni formatlaymiz
                    text = (
                        f"📋 Ma'lumotlar:\n"
                        f"├─ 📖 Fan: {subject}\n"
                        f"├─ 📚 Bo'lim: {chapters}\n"
                        f"└─ 📝 Mavzu: {topics}\n\n"
                        f"📊 Test natijasi:\n"
                        f"├─ ❌ Jami savollar: {total_answers}\n"
                        f"├─ ✅ To'g'ri javoblar: {correct_answers}\n"
                        f"├─ 📈 Foiz: {percentage:.1f}%\n"
                        f"└─ ⭐ Ball: {score}"
                    )

                    await update.message.reply_text(text)
                else:
                    await update.message.reply_text("Ma'lumot topilmadi.")
            except requests.exceptions.RequestException as e:
                logger.error(f"API xatolik: {e}")
                await update.message.reply_text("Tizimda xatolik yuz berdi.")
            return

    # payload bo‘lmasa – eski logika
    await update.message.reply_text("Assalomu alaykum! Xush kelibsiz.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f'Xatolik: {context.error}', exc_info=context.error)


def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_teacher_callback))
    application.add_error_handler(error_handler)

    logger.info("Bot ishga tushdi...")
    application.run_polling()


if __name__ == '__main__':
    main()
