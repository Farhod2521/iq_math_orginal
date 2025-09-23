import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from config import BOT_TOKEN
from teacher import handle_teacher_callback
from urllib.parse import quote

# Log konfiguratsiyasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

API_URL = "https://api.iqmath.uz/api/v1/func_student/id-independent"


def get_teacher_chat_ids():
    try:
        url = "https://api.iqmath.uz/api/v1/auth/teacher-telegram-id/list/"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # {"telegram_ids": [1858379541, 79451684]}
            telegram_ids = data.get("telegram_ids", [])
            # intga aylantirib olish
            return [int(tg_id) for tg_id in telegram_ids]
        else:
            print("API xato:", response.status_code)
            return []
    except Exception as e:
        print("APIga ulanib bo‘lmadi:", e)
        return []

# endi shu funksiyani chaqirib listni olamiz
TEACHER_CHAT_IDS = get_teacher_chat_ids()

class BotManager:
    def __init__(self, bot_token):
        self.application = ApplicationBuilder().token(bot_token).build()
        self.bot = self.application.bot
        
    def setup_handlers(self):
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        self.application.add_handler(CallbackQueryHandler(handle_teacher_callback))
        self.application.add_error_handler(self.error_handler)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_id = update.effective_user.id
        print(f"Foydalanuvchi {telegram_id} /start buyrug'ini yubordi")

        args = context.args
        if args:
            payload = args[0]  # masalan "209_83"
            if "_" in payload:
                try:
                    help_request_id, student_id = payload.split("_")
                    print(f"Payload: help_request_id={help_request_id}, student_id={student_id}")
                except ValueError:
                    await update.message.reply_text("Xato payload formati.")
                    return

                # API chaqiramiz
                try:
                    resp = requests.get(f"{API_URL}/{help_request_id}/", timeout=10)
                    print(f"Start API javobi: {resp.status_code}")
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        print(f"Start API ma'lumotlari: {data}")

                        # 🔹 Ma'lumotlarni API dan olamiz
                        subject = data.get("subject_name_uz", "-")
                        chapters = ", ".join(data.get("chapter_name_uz", [])) if data.get("chapter_name_uz") else "-"
                        topics = ", ".join(data.get("topic_name_uz", [])) if data.get("topic_name_uz") else "-"

                        # 🔹 STATUS ni olib emoji bilan qo'shamiz
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
                            status_body = status

                        # 🔹 result massivdan birinchi elementni olamiz
                        result = data.get("result", [])
                        if result:
                            result_data = result[0] if isinstance(result, list) else result
                            score = result_data.get("score", 0)
                            total_answers = result_data.get("total_answers", 0)
                            correct_answers = result_data.get("correct_answers", 0)
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

        # payload bo'lmasa - oddiy javob
        await update.message.reply_text("Assalomu alaykum! Xush kelibsiz.")

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        print(f"Callback data: {callback_data}")
        
        if callback_data.startswith("send_"):
            # Yuborish tugmasi bosilganda
            _, help_request_id, student_id = callback_data.split("_")
            print(f"Yuborish: help_request_id={help_request_id}, student_id={student_id}")
            
            try:
                # Student ma'lumotlarini olish
                student_full_name = "O'quvchi"
                try:
                    # Student API manzilini to'g'rilaymiz
                    student_api_url = f"https://api.iqmath.uz/api/v1/students/{student_id}/"
                    student_resp = requests.get(student_api_url, timeout=5)
                    print(f"Student API javobi: {student_resp.status_code}")
                    
                    if student_resp.status_code == 200:
                        student_data = student_resp.json()
                        student_full_name = student_data.get('full_name', 'O\'quvchi')
                        print(f"Student nomi: {student_full_name}")
                    else:
                        print(f"Student ma'lumotlari topilmadi, default nom ishlatiladi")
                except Exception as e:
                    print(f"Student ma'lumotlarini olishda xatolik: {e}")
                
                # send_question_to_telegram funksiyasini chaqiramiz
                success = await self.send_question_to_telegram(
                    student_id=student_id,
                    student_full_name=student_full_name,
                    question_id=help_request_id,
                )
                
                # Foydalanuvchaga xabar beramiz
                if success:
                    await query.edit_message_text(
                        text=query.message.text + "\n\n✅ <b>Murojaat o'qituvchilarga yuborildi!</b>",
                        parse_mode="HTML"
                    )
                else:
                    await query.edit_message_text(
                        text=query.message.text + "\n\n❌ <b>Xatolik yuz berdi. Qayta urinib ko'ring.</b>",
                        parse_mode="HTML"
                    )
                    
            except Exception as e:
                print(f"Button handler xatolik: {e}")
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

    async def send_question_to_telegram(self, student_id, student_full_name, question_id):
        """
        O'qituvchilarga savolni yuborish funksiyasi
        """
        try:
            print(f"Savol yuborish boshlandi: student_id={student_id}, question_id={question_id}")
            
            # 1. Savol ma'lumotlarini API dan olish
            resp = requests.get(f"{API_URL}/{question_id}/", timeout=10)
            print(f"API javobi: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"API dan ma'lumot olishda xatolik: {resp.status_code}")
                return False
            
            data = resp.json()
            print(f"API ma'lumotlari: {data}")
            
            # 2. Ma'lumotlarni olish
            subject_name = data.get("subject_name_uz", "-")
            chapters = data.get("chapter_name_uz", [])
            topics = data.get("topic_name_uz", [])
            
            chapter_name = ", ".join(chapters) if chapters else "-"
            topic_name = ", ".join(topics) if topics else "-"
            
            # 3. Test natijalarini olish
            result = data.get("result", [])
            if result:
                result_data = result[0] if isinstance(result, list) else result
                score = result_data.get("score", 0)
                total_answers = result_data.get("total_answers", 0)
                correct_answers = result_data.get("correct_answers", 0)
                percentage = (correct_answers / total_answers * 100) if total_answers else 0
            else:
                score = total_answers = correct_answers = percentage = 0
            
            # 4. URL encode qilish
            student_name_encoded = quote(student_full_name)
            student_id_encoded = quote(str(student_id))
            
            url = f"https://iqmath.uz/dashboard/teacher/student-examples/{question_id}?student_name={student_name_encoded}&student_id={student_id_encoded}"
            
            # 5. Rang-barang matn (HTML format)
            text = (
                "📥 <b>Yangi savol keldi!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>O'quvchi:</b> {student_full_name} (ID: {student_id})\n"
                f"🆔 <b>Savol ID:</b> {question_id}\n\n"
                "📚 <b>Mavzu ma'lumotlari:</b>\n"
                f"• 📖 Fan: <b>{subject_name}</b>\n"
                f"• 📚 Bo'lim: <b>{chapter_name}</b>\n"
                f"• 📝 Mavzu: <b>{topic_name}</b>\n\n"
                "📊 <b>Test natijasi:</b>\n"
                f"• ❓ Jami savollar: <b>{total_answers}</b>\n"
                f"• ✅ To'g'ri javoblar: <b>{correct_answers}</b>\n"
                f"• 📈 Foiz: <b>{percentage:.1f}%</b>\n"
                f"• ⭐ Ball: <b>{score}</b>\n\n"
                "ℹ️ <i>Iltimos savolni ko'rib chiqing va javob bering</i>"
            )
            
            # 6. Inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton("✅ Javob berish", callback_data=f"assign_{question_id}"),
                ],
                [
                    InlineKeyboardButton("🔗 Savolga o'tish", url=url)
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # 7. Barcha o'qituvchilarga xabarni yuborish
            success_count = 0
            for chat_id in TEACHER_CHAT_IDS:
                try:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                    success_count += 1
                    print(f"Xabar {chat_id} ga yuborildi")
                except Exception as e:
                    print(f"Xabar {chat_id} ga yuborishda xatolik: {e}")
            
            print(f"Jami {success_count} ta o'qituvchiga xabar yuborildi")
            return success_count > 0
            
        except Exception as e:
            print(f"send_question_to_telegram funksiyasida xatolik: {e}")
            return False

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f'Xatolik: {context.error}', exc_info=context.error)

    def run(self):
        self.setup_handlers()
        logger.info("Bot ishga tushdi...")
        self.application.run_polling()

def main():
    bot_manager = BotManager(BOT_TOKEN)
    bot_manager.run()

if __name__ == '__main__':
    main()