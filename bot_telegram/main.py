import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
import json
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

    args = context.args
    if args:
        payload = args[0]
        
        try:
            # Avval oddiy formatni tekshiramiz (200_83)
            if "_" in payload and not payload.startswith("{"):
                instance_id, student_id = payload.split("_")
                await show_simple_message(update, instance_id, student_id)
                return
            
            # JSON formatini tekshiramiz
            try:
                payload_decoded = unquote(payload)
                payload_data = json.loads(payload_decoded)
                
                # Qisqartirilgan kalitlardan ma'lumotlarni olish
                instance_id = payload_data.get('i') or payload_data.get('instance_id')
                student_id = payload_data.get('s') or payload_data.get('student_id')
                subject_name_uz = payload_data.get('sub') or payload_data.get('subject_name_uz', 'Noma\'lum')
                chapter_name_uz = payload_data.get('ch') or payload_data.get('chapter_name_uz', 'Noma\'lum')
                topic_name_uz = payload_data.get('top') or payload_data.get('topic_name_uz', 'Noma\'lum')
                total_answers = payload_data.get('ta') or payload_data.get('total_answers', 0)
                correct_answers = payload_data.get('ca') or payload_data.get('correct_answers', 0)
                score = payload_data.get('sc') or payload_data.get('score', 0)
                
                await show_detailed_message(update, instance_id, student_id, subject_name_uz, 
                                          chapter_name_uz, topic_name_uz, total_answers, 
                                          correct_answers, score)
                
            except json.JSONDecodeError:
                # Agar JSON bo'lmasa, oddiy formatni tekshiramiz
                if "_" in payload:
                    instance_id, student_id = payload.split("_")
                    await show_simple_message(update, instance_id, student_id)
                else:
                    await update.message.reply_text("❌ Xato: Noto'g'ri payload formati")
                    
        except Exception as e:
            logger.error(f"Payload parse qilishda xatolik: {e}")
            # Oddiy formatni tekshiramiz
            if "_" in payload:
                try:
                    instance_id, student_id = payload.split("_")
                    await show_simple_message(update, instance_id, student_id)
                except:
                    await update.message.reply_text("❌ Xato: Noto'g'ri payload formati")
            else:
                await update.message.reply_text("❌ Xato: Noto'g'ri payload formati")
            return

    # Agar payload yo'q bo'lsa odatiy start
    else:
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
            await update.message.reply_text("Tizimda vaqtinchalik xatolik yuz berdi. Iltimos, keyinroq urunib ko'ring.")

async def show_simple_message(update, instance_id, student_id):
    """Oddiy formatdagi xabar"""
    message = f"""
✅ Savol so'rovi muvaffaqiyatli yuborildi

👨‍🎓 Student ID: {student_id}
🆔 Savol ID: {instance_id}

Savolingiz o'qituvchiga yuborildi. Tez orada javob olasiz.
"""
    await update.message.reply_text(message)

async def show_detailed_message(update, instance_id, student_id, subject_name_uz, 
                               chapter_name_uz, topic_name_uz, total_answers, 
                               correct_answers, score):
    """Batafsil xabar"""
    percentage = (correct_answers / total_answers * 100) if total_answers > 0 else 0
    
    message = f"""
🎯 Savol so'rovi muvaffaqiyatli yuborildi

📋 Ma'lumotlar:
├─ 👨‍🎓 Student ID: {student_id}
├─ 🆔 Savol ID: {instance_id}

📚 Mavzu ma'lumotlari:
├─ 📖 Fan: {subject_name_uz}
├─ 📚 Bo'lim: {chapter_name_uz}
└─ 📝 Mavzu: {topic_name_uz}

📊 Test natijasi:
├─ ❌ Jami savollar: {total_answers}
├─ ✅ To'g'ri javoblar: {correct_answers}
├─ 📈 Foiz: {percentage:.1f}%
└─ ⭐ Ball: {score}

✅ Savolingiz o'qituvchiga yuborildi.
"""
    await update.message.reply_text(message)
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
