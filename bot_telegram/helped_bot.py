import os
import django
import requests
import sys
import urllib.parse
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from asgiref.sync import sync_to_async

# Django sozlash
sys.path.append('/home/user/backend/iq_math_orginal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

django.setup()

from django_app.app_student.models import HelpRequestMessageLog

BOT_TOKEN = "7826335243:AAGXTZvtzJ8e8g35Hrx_Swy7mwmRPd3T7Po"
BACKEND_ASSIGN_API = "https://api.iqmath.uz/api/v1/func_student/student/telegram/assign-teacher/"
TELEGRAM_ID_API = "https://api.iqmath.uz/api/v1/func_student/student/student_id/telegram_id/"
TEACHER_CHAT_IDS = [1858379541, 5467533504]

# Savolni yuborish
def send_question_to_telegram(student_full_name, question_id, result_json):
    student_name_encoded = urllib.parse.quote(student_full_name)
    url = f"https://mentor.iqmath.uz/dashboard/teacher/student-examples/{question_id}?student_name={student_name_encoded}"

    result = result_json[0] if result_json else {}
    total = result.get("total_answers", "-")
    correct = result.get("correct_answers", "-")
    score = result.get("score", "-")

    text = (
        f"📥 <b>Yangi savol!</b>\n"
        f"👤 <b>O'quvchi:</b> {student_full_name}\n"
        f"🆔 <b>Savol ID:</b> {question_id}\n\n"
        f"📊 <b>Natija:</b>\n"
        f"➕ To'g'ri: <b>{correct}</b> / {total}\n"
        f"⭐️ Ball: <b>{score}</b>\n"
    )

    keyboard = {
        "inline_keyboard": [
            [ {"text": "✅ Javob berish", "callback_data": f"assign_{question_id}"} ],
            [ {"text": "🔗 Savolga o'tish", "url": url} ]
        ]
    }

    for chat_id in TEACHER_CHAT_IDS:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
            "disable_web_page_preview": True
        }
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)
        if r.status_code == 200:
            message_id = r.json()["result"]["message_id"]
            HelpRequestMessageLog.objects.create(
                help_request_id=question_id,
                chat_id=chat_id,
                message_id=message_id
            )

@sync_to_async
def get_logs(help_request_id):
    return list(HelpRequestMessageLog.objects.filter(help_request_id=help_request_id))

async def get_student_telegram_id(student_id):
    try:
        r = requests.post(TELEGRAM_ID_API, json={"student_id": student_id}, timeout=5)
        if r.status_code == 200:
            return r.json().get("telegram_id")
    except:
        return None
    return None

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("assign_") or data.startswith("takeover_"):
        help_request_id = int(data.split("_")[1])
        teacher_name = f"{query.from_user.first_name} {query.from_user.last_name or ''}".strip()
        telegram_id = query.from_user.id

        resp = requests.post(BACKEND_ASSIGN_API, data={
            "help_request_id": help_request_id,
            "telegram_id": telegram_id
        })
        if resp.status_code != 200 or not resp.json().get("success"):
            await query.message.reply_text("❌ Xatolik. Backenddan muvaffaqiyatli javob kelmadi.")
            return

        student_id = resp.json().get("student_id")
        context.user_data['active_assignment'] = {
            'help_request_id': help_request_id,
            'student_id': student_id,
            'teacher_name': teacher_name
        }

        logs = await get_logs(help_request_id)
        url = f"https://iqmath.uz/dashboard/teacher/student-examples/{help_request_id}"

        for log in logs:
            try:
                if log.chat_id == query.message.chat_id:
                    await context.bot.edit_message_text(
                        chat_id=log.chat_id,
                        message_id=log.message_id,
                        text=f"✅ Siz javob berayapsiz\n\n{query.message.text}",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")],
                            [InlineKeyboardButton("🔗 Savolga o'tish", url=url)]
                        ]),
                        parse_mode="HTML"
                    )
                else:
                    await context.bot.edit_message_text(
                        chat_id=log.chat_id,
                        message_id=log.message_id,
                        text=f"👨‍🏫 {teacher_name} javob beryapti\n\n{query.message.text}",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("O'zim javob qilaman", callback_data=f"takeover_{help_request_id}")],
                            [InlineKeyboardButton("🔗 Savolga o'tish", url=url)]
                        ]),
                        parse_mode="HTML"
                    )
            except Exception as e:
                print(f"Edit xatolik: {e}")

    elif data.startswith("send_"):
        help_request_id = int(data.split("_")[1])
        assignment = context.user_data.get('active_assignment', {})
        if assignment.get('help_request_id') != help_request_id:
            await query.message.reply_text("❌ Bu savol sizga biriktirilmagan")
            return

        student_telegram_id = await get_student_telegram_id(assignment['student_id'])
        if not student_telegram_id:
            await query.message.reply_text("❌ Talaba Telegram ID topilmadi")
            return

        answer_text = context.user_data.get('answer_text')
        if not answer_text:
            await query.message.reply_text("❌ Avval reply qilib javob yozing")
            return

        await context.bot.send_message(
            chat_id=student_telegram_id,
            text=f"👨‍🏫 {assignment['teacher_name']}dan javob:\n\n{answer_text}"
        )
        await query.message.reply_text("✅ Javob yuborildi!")
        context.user_data.pop('answer_text', None)
        context.user_data.pop('active_assignment', None)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message and 'active_assignment' in context.user_data:
        context.user_data['answer_text'] = update.message.text
        help_request_id = context.user_data['active_assignment']['help_request_id']
        await update.message.reply_text(
            "✅ Javob qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
            ])
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
