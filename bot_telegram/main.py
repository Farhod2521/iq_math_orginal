import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from config import API_URL, BOT_TOKEN
from teacher import teacher_menu, handle_teacher_callback
from .helped_bot import  send_question_to_telegram
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
                        status_body = "📩 O'qtuvchiga yuborildi"
                    elif status == "reviewing":
                        header = "⏳ Muhokama bo'lmoqda"
                        footer = "💬 O'qituvchi sizning murojaatingizni ko'rib chiqmoqda."
                        status_body = "⏳ Muhokama bo'lmoqda"
                    elif status == "answered":
                        header = "✅ Javob berilgan"
                        footer = "💬 Sizning murojaatingizga javob berildi!"
                        status_body = "✅ Javob berilgan"
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
                        f"<b>{header}</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📖 <b>Fan:</b> {subject}\n"
                        f"📚 <b>Bo'lim:</b> {chapters}\n"
                        f"📝 <b>Mavzu:</b> {topics}\n"
                        f"📌 <b>Holati:</b> {status_body}\n\n"
                        f"📊 <b>Test natijasi</b>\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"❌ <b>Jami savollar:</b> {total_answers}\n"
                        f"✅ <b>To'g'ri javoblar:</b> {correct_answers}\n"
                        f"📈 <b>Foiz:</b> {percentage:.1f}%\n"
                        f"⭐️ <b>Ball:</b> {score}\n\n"
                        f"<b>{footer}</b>"
                    )
                    keyboard = [
                        [
                            InlineKeyboardButton("✅ Yuborish", callback_data=f"send_{help_request_id}_{student_id}"),
                            InlineKeyboardButton("❌ Bekor qilish", callback_data=f"cancel_{help_request_id}_{student_id}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)

                else:
                    await update.message.reply_text("Ma'lumot topilmadi.")

            except requests.exceptions.RequestException as e:
                print(f"API xatolik: {e}")
                await update.message.reply_text("Tizimda xatolik yuz berdi.")
            return

    # payload bo‘lmasa – oddiy javob
    await update.message.reply_text("Assalomu alaykum! Xush kelibsiz.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    print(f"Callback data: {callback_data}")
    
    if callback_data.startswith("send_"):
        # Yuborish tugmasi bosilganda
        _, help_request_id, student_id = callback_data.split("_")
        
        # 🔥 send_question_to_telegram funksiyasini chaqiramiz
        try:
            # Student ma'lumotlarini olish
            student_resp = requests.get(f"{API_URL}/students/{student_id}/", timeout=5)
            if student_resp.status_code == 200:
                student_data = student_resp.json()
                student_full_name = student_data.get('full_name', '')
                
                # send_question_to_telegram funksiyasini chaqiramiz
                send_question_to_telegram(
                    student_id=student_id,
                    student_full_name=student_full_name,
                    question_id=help_request_id,
                )
                
                # Foydalanuvchaga xabar beramiz
                await query.edit_message_text(
                    text=query.message.text + "\n\n✅ <b>Murojaat o'qituvchiga yuborildi!</b>",
                    parse_mode="HTML"
                )
            else:
                await query.edit_message_text(
                    text=query.message.text + "\n\n❌ <b>Xatolik yuz berdi. Qayta urinib ko'ring.</b>",
                    parse_mode="HTML"
                )
                
        except Exception as e:
            print(f"Xatolik: {e}")
            await query.edit_message_text(
                text=query.message.text + "\n\n❌ <b>Xatolik yuz berdi. Qayta urinib ko'ring.</b>",
                parse_mode="HTML"
            )
    
    elif callback_data.startswith("cancel_"):
        # Bekor qilish tugmasi bosilganda
        await query.edit_message_text(
            text=query.message.text + "\n\n❌ <b>Murojaat bekor qilindi.</b>",
            parse_mode="HTML"
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f'Xatolik: {context.error}', exc_info=context.error)


def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(handle_teacher_callback))
    application.add_error_handler(error_handler)

    logger.info("Bot ishga tushdi...")
    application.run_polling()


if __name__ == '__main__':
    main()
