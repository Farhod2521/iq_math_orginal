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
    print(f"Foydalanuvchi {telegram_id} /start buyrug'ini yubordi")

    args = context.args
    if args:
        payload = args[0]  # masalan "209_83"
        if "_" in payload:
            try:
                help_request_id, student_id = payload.split("_")
            except ValueError:
                await update.message.reply_text("Xato payload formati.")
                return

            # API chaqiramiz
            try:
                resp = requests.get(f"{API_URL}/{help_request_id}/", timeout=5)
                if resp.status_code == 200:
                    data = resp.json()

                    # 🔹 Ma’lumotlarni API dan olamiz
                    subject = data.get("subject_name_uz", "-")
                    chapters = ", ".join(data.get("chapter_name_uz", []))
                    topics = ", ".join(data.get("topic_name_uz", []))

                    # 🔹 STATUS ni olib emoji bilan qo‘shamiz
                    status = data.get("status", "")
                    if status == "sent":
                        header = "📩 Yangi murojaat"
                        footer = "💬 Murojaatingiz tez orada ko'rib chiqiladi!"
                    elif status == "reviewing":
                        header = "⏳ Muhokama bo'lmoqda"
                        footer = "💬 O'qituvchi sizning murojaatingizni ko'rib chiqmoqda."
                    elif status == "answered":
                        header = "✅ Javob berilgan"
                        footer = "💬 Sizning murojaatingizga javob berildi!"
                    else:
                        header = "ℹ️ Ma'lumot"
                        footer = ""

                    # 🔹 result massivdan birinchi elementni olamiz
                    result = data.get("result", [])
                    if result:
                        result = result[0]
                        score = result.get("score", 0)
                        total_answers = result.get("total_answers", 0)
                        correct_answers = result.get("correct_answers", 0)
                        percentage = (correct_answers / total_answers * 100) if total_answers else 0
                    else:
                        score = total_answers = correct_answers = percentage = 0

                    # 🔹 Xabarni formatlaymiz
                    text = (
                        f"{header}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📖 Fan: {subject}\n"
                        f"📚 <b>Bo'lim:</b> {chapters}\n"
                        f"📝 Mavzu: {topics}\n"
                        f"📌 Holati: ⏳ Muhokamada\n\n"
                        f"📊 Test natijasi\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"❌ Jami savollar: {total_answers}\n"
                        f"✅ To'g'ri javoblar: {correct_answers}\n"
                        f"📈 Foiz: {percentage:.1f}%\n"
                        f"⭐️ Ball: {score}\n\n"
                        f"{footer}"
                    )

                    await update.message.reply_text(text)

                else:
                    await update.message.reply_text("Ma'lumot topilmadi.")

            except requests.exceptions.RequestException as e:
                print(f"API xatolik: {e}")
                await update.message.reply_text("Tizimda xatolik yuz berdi.")
            return

    # payload bo‘lmasa – oddiy javob
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
