import requests
import urllib.parse
import json
from django_app.app_student.models import HelpRequestMessageLog  # Log modeli

BOT_TOKEN = '7826335243:AAGXTZvtzJ8e8g35Hrx_Swy7mwmRPd3T7Po'

# Bu yerda barcha o‘qituvchilarning telegram_id'lari bo‘ladi  79451684
TEACHER_CHAT_IDS = [1858379541]  # misol uchun

def send_question_to_telegram(student_full_name, question_id, result_json):
    student_name_encoded = urllib.parse.quote(student_full_name)
    url = f"https://mentor.iqmath.uz/dashboard/teacher/student-examples/{question_id}?student_name={student_name_encoded}"

    result = result_json[0] if result_json else {}
    total = result.get("total_answers", "-")
    correct = result.get("correct_answers", "-")
    score = result.get("score", "-")

    text = (
        f"📥 <b>Yangi savol!</b>\n"
        f"👤 <b>O‘quvchi:</b> {student_full_name}\n"
        f"🆔 <b>Savol ID:</b> {question_id}\n\n"
        f"📊 <b>Natija:</b>\n"
        f"➕ To‘g‘ri: <b>{correct}</b> / {total}\n"
        f"⭐️ Ball: <b>{score}</b>\n\n"
        f"🕘 <i>Kim birinchi bo‘lib javob bersa, savol unga biriktiriladi</i>"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Javob berish", "callback_data": f"assign_{question_id}"},
            ],
            [
                {"text": "🔗 Savolga o‘tish", "url": url}
            ]
        ]
    }

    # Har bir o‘qituvchiga yuboramiz
    for chat_id in TEACHER_CHAT_IDS:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
            "disable_web_page_preview": True
        }

        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=payload
        )

        if response.ok:
            res_data = response.json()
            message_id = res_data["result"]["message_id"]

            # Bazaga log yozish
            HelpRequestMessageLog.objects.create(
                help_request_id=question_id,
                chat_id=chat_id,
                message_id=message_id
            )
