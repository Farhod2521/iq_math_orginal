import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from config import API_URL, BOT_TOKEN
from teacher import teacher_menu, handle_teacher_callback
from urllib.parse import unquote
# Log konfiguratsiyasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    logger.info(f"Foydalanuvchi {telegram_id} /start buyrug'ini yubordi")

    # 1️⃣ Payloadni olish
    args = context.args
    if args:  # payload bor
        payload = args[0]
        
        try:
            # URL decode qilish
            payload_decoded = unquote(payload)
            
            # JSON ni parse qilish
            payload_data = json.loads(payload_decoded)
            
            # Ma'lumotlarni olish
            instance_id = payload_data.get('instance_id')
            student_id = payload_data.get('student_id')
            subject_name_uz = payload_data.get('subject_name_uz', '')
            chapter_name_uz = payload_data.get('chapter_name_uz', '')
            topic_name_uz = payload_data.get('topic_name_uz', '')
            total_answers = payload_data.get('total_answers', 0)
            correct_answers = payload_data.get('correct_answers', 0)
            score = payload_data.get('score', 0)
            
            # Chiroyli xabar tayyorlash
            message = f"""
📚 **Yangi savol so'rovi qabul qilindi**

👨‍🎓 **Student ID:** {student_id}
🆔 **Savol ID:** {instance_id}

📖 **Fan:** {subject_name_uz}
📚 **Bo'lim:** {chapter_name_uz}
📝 **Mavzu:** {topic_name_uz}

📊 **Test natijasi:**
• Jami savollar: {total_answers}
• To'g'ri javoblar: {correct_answers}
• Ball: {score}

✅ Savol muvaffaqiyatli yuborildi. Tez orada o'qituvchi javob beradi.
"""
            
            await update.message.reply_text(message)
            return  # payload bo'lsa shu yerda tugatamiz
            
        except json.JSONDecodeError:
            # Agar JSON parse qilishda xatolik bo'lsa, eski formatni tekshiramiz
            if "_" in payload:
                try:
                    help_request_id, student_id = payload.split("_")
                    await update.message.reply_text(
                        f"Salom! Siz {help_request_id}-savolni o'qituvchiga yubordingiz. "
                        f"Tez orada javob olasiz."
                    )
                    return
                except ValueError:
                    await update.message.reply_text("Xato payload formati.")
                    return
            else:
                await update.message.reply_text("Xato payload formati.")
                return

    # 2️⃣ Agar payload yo'q bo'lsa — oldingi logika
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
            await update.message.reply_text(
                "Siz ro'yxatdan o'tmagansiz. Iltimos, avval ro'yxatdan o'ting."
            )
    except requests.exceptions.RequestException as e:
        logger.error(f"API so'rovida xatolik: {e}")
        await update.message.reply_text(
            "Tizimda vaqtinchalik xatolik yuz berdi. Iltimos, keyinroq urunib ko'ring."
        )

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
