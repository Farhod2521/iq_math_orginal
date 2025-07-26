import requests
import urllib.parse
import json

BOT_TOKEN = '7826335243:AAGXTZvtzJ8e8g35Hrx_Swy7mwmRPd3T7Po'
TEACHER_CHAT_ID = 1858379541  # o‘qituvchi yoki guruh ID

def send_question_to_telegram(student_full_name, question_id):
    student_name_encoded = urllib.parse.quote(student_full_name)
    url = f"https://mentor.iqmath.uz/dashboard/teacher/student-examples/{question_id}?student_name={student_name_encoded}"
    
    text = (
        f"📥 <b>Yangi savol!</b>\n"
        f"👤 <b>O‘quvchi:</b> {student_full_name}\n"
        f"🆔 <b>Savol ID:</b> {question_id}"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🔗 Savolga o‘tish",
                    "url": url
                }
            ]
        ]
    }

    payload = {
        "chat_id": TEACHER_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(keyboard),
        "disable_web_page_preview": True
    }

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=payload
    )

    return response.ok
