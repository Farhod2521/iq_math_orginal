import os
import django
import requests
import sys
import urllib.parse
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from asgiref.sync import sync_to_async

# Loyiha yo'lini qo'shish
sys.path.append('/home/user/backend/iq_math_orginal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

try:
    django.setup()
    print("✅ Django ishga tushdi")
except Exception as e:
    print(f"❌ Django xatosi: {e}")
    sys.exit(1)

from django_app.app_student.models import HelpRequestMessageLog

BOT_TOKEN = "7826335243:AAGXTZvtzJ8e8g35Hrx_Swy7mwmRPd3T7Po"
BACKEND_ASSIGN_API = "https://api.iqmath.uz/api/v1/func_student/student/telegram/assign-teacher/"
TELEGRAM_ID_API = "https://api.iqmath.uz/api/v1/func_student/student/student_id/telegram_id/"
TEACHER_CHAT_IDS = [1858379541, 5467533504]  # O'qituvchilar chat ID lari

# ================= TELEGRAM SERVICE FUNCTIONS =================

def send_question_to_telegram(student_full_name, question_id, result_json):
    """
    Savolni barcha o'qituvchilarga yuborish
    """
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
        f"⭐️ Ball: <b>{score}</b>\n\n"
    )

    # Keyboard format
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Javob berish", "callback_data": f"assign_{question_id}"},
            ],
            [
                {"text": "🔗 Savolga o'tish", "url": url}
            ]
        ]
    }

    # Har bir o'qituvchiga yuboramiz
    for chat_id in TEACHER_CHAT_IDS:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
            "disable_web_page_preview": True
        }

        try:
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data=payload,
                timeout=10
            )

            if response.status_code == 200:
                res_data = response.json()
                message_id = res_data["result"]["message_id"]

                # Bazaga log yozish
                HelpRequestMessageLog.objects.create(
                    help_request_id=question_id,
                    chat_id=chat_id,
                    message_id=message_id
                )
                print(f"✅ Xabar yuborildi: chat_id={chat_id}, message_id={message_id}")
            else:
                print(f"❌ Xatolik: {response.status_code}, {response.text}")
                
        except Exception as e:
            print(f"❌ Xabar yuborishda xatolik: {e}")

# ================= BOT HANDLER FUNCTIONS =================

@sync_to_async
def get_logs(help_request_id):
    return list(HelpRequestMessageLog.objects.filter(help_request_id=help_request_id))

@sync_to_async
def update_message_log(help_request_id, chat_id, teacher_name):
    try:
        log = HelpRequestMessageLog.objects.get(help_request_id=help_request_id, chat_id=chat_id)
        log.teacher_name = teacher_name
        log.save()
        return True
    except:
        return False

async def get_student_telegram_id(student_id):
    """Student ID orqali student telegram ID sini olish"""
    try:
        response = requests.post(
            TELEGRAM_ID_API,
            json={"student_id": student_id},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("telegram_id")
        return None
    except Exception as e:
        print(f"❌ Telegram ID olishda xatolik: {e}")
        return None

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    print(f"🔔 Tugma bosildi: {data}")
    
    if data.startswith("assign_"):
        help_request_id = int(data.split("_")[1])
        teacher_name = f"{query.from_user.first_name} {query.from_user.last_name or ''}".strip()
        telegram_id = query.from_user.id
        
        print(f"👨‍🏫 O'qituvchi {teacher_name} ({telegram_id}) {help_request_id}-savolga javob berishni boshladi")
        
        try:
            print(f"🌐 Backend API ga so'rov yuborilmoqda: {BACKEND_ASSIGN_API}")
            response = requests.post(
                BACKEND_ASSIGN_API,
                json={
                    "help_request_id": help_request_id,
                    "telegram_id": telegram_id,
                    "teacher_name": teacher_name
                },
                timeout=10
            )
            
            print(f"📨 Backend javob kodi: {response.status_code}")
            print(f"📨 Backend javob matni: {response.text}")
            
            if response.status_code != 200:
                await query.message.reply_text("❌ Server xatosi")
                return
            
            # JSON javobini tekshirish
            try:
                result = response.json()
            except json.JSONDecodeError:
                print(f"❌ Noto'g'ri JSON formati: {response.text}")
                await query.message.reply_text("❌ Serverdan noto'g'ri javob qaytdi")
                return
                
        except Exception as e:
            error_msg = f"❌ Serverga ulanishda xatolik: {e}"
            print(error_msg)
            await query.message.reply_text("❌ Serverga ulanishda xatolik")
            return
        
        if result.get("success"):
            print(f"✅ Backend muvaffaqiyatli javob berdi. Teacher: {result.get('teacher_name')}")
            
            # Student ID ni olish
            student_id = result.get("student_id")
            
            # Student telegram ID sini olish
            student_telegram_id = await get_student_telegram_id(student_id) if student_id else None
            
            if not student_telegram_id:
                print("❌ Student telegram ID topilmadi")
            
            # O'qituvchi ma'lumotlarini saqlaymiz
            context.user_data['active_assignment'] = {
                'help_request_id': help_request_id,
                'student_id': student_id,
                'student_telegram_id': student_telegram_id,
                'teacher_name': teacher_name
            }
            
            # Loglarni olamiz
            logs = await get_logs(help_request_id)
            print(f"📋 {len(logs)} ta log topildi")
            
            url = f"https://iqmath.uz/dashboard/teacher/student-examples/{help_request_id}"
            
            # Xabarlarni yangilaymiz
            success_count = 0
            for log in logs:
                try:
                    if log.chat_id == query.message.chat_id:
                        # Javob bergan o'qituvchi uchun
                        new_text = query.message.text.replace("📥 Yangi savol!", "✅ Siz javob berayapsiz")
                        
                        new_markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton("👨‍🏫 Siz javob berayapsiz", callback_data=f"assigned_{help_request_id}")],
                            [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")],
                            [InlineKeyboardButton("🔗 Savolga o'tish", url=url)]
                        ])
                        
                        await context.bot.edit_message_text(
                            chat_id=log.chat_id,
                            message_id=log.message_id,
                            text=new_text,
                            reply_markup=new_markup,
                            parse_mode="HTML"
                        )
                        print(f"✏️ Javob bergan o'qituvchi xabari yangilandi: {log.chat_id}")
                        
                        # Yo'riqnoma xabarini yuboramiz
                        await query.message.reply_text(
                            "✅ Endi siz bu savolga javob berayapsiz.\n\n" +
                            "Talabaga javob yuborish uchun shu xabarga 'reply' qilib yozing yoki " +
                            "to'g'ridan-to'g'ri yozib, keyin 'Javobni yuborish' tugmasini bosing.",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                            ])
                        )
                    else:
                        # Boshqa o'qituvchilar uchun
                        new_text = query.message.text.replace("📥 Yangi savol!", f"👨‍🏫 {teacher_name} javob beryapti")
                        
                        other_teachers_markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton("👨‍🏫 Javob berilmoqda", callback_data=f"taken_{help_request_id}")],
                            [InlineKeyboardButton("🔄 O'zim javob qilaman", callback_data=f"takeover_{help_request_id}")],
                            [InlineKeyboardButton("🔗 Savolga o'tish", url=url)]
                        ])
                        
                        await context.bot.edit_message_text(
                            chat_id=log.chat_id,
                            message_id=log.message_id,
                            text=new_text,
                            reply_markup=other_teachers_markup,
                            parse_mode="HTML"
                        )
                        print(f"✏️ Boshqa o'qituvchi xabari yangilandi: {log.chat_id}")
                    
                    success_count += 1
                        
                except Exception as e:
                    print(f"❌ Xabar yangilashda xatolik (chat_id: {log.chat_id}): {e}")
            
            print(f"✅ {success_count}/{len(logs)} ta xabar yangilandi")
            
        else:
            error_msg = result.get("message", "❌ Noma'lum xatolik")
            print(f"❌ Backend xatosi: {error_msg}")
            await query.message.reply_text(error_msg)
    
    elif data.startswith("takeover_"):
        # O'zim javob qilaman tugmasi bosilganda
        help_request_id = int(data.split("_")[1])
        teacher_name = f"{query.from_user.first_name} {query.from_user.last_name or ''}".strip()
        telegram_id = query.from_user.id
        
        print(f"👨‍🏫 O'qituvchi {teacher_name} ({telegram_id}) {help_request_id}-savolni o'ziga olmoqchi")
        
        try:
            print(f"🌐 Backend API ga so'rov yuborilmoqda: {BACKEND_ASSIGN_API}")
            response = requests.post(
                BACKEND_ASSIGN_API,
                json={
                    "help_request_id": help_request_id,
                    "telegram_id": telegram_id,
                    "teacher_name": teacher_name
                },
                timeout=10
            )
            
            print(f"📨 Backend javob kodi: {response.status_code}")
            print(f"📨 Backend javob matni: {response.text}")
            
            if response.status_code != 200:
                await query.message.reply_text("❌ Server xatosi")
                return
            
            # JSON javobini tekshirish
            try:
                result = response.json()
            except json.JSONDecodeError:
                print(f"❌ Noto'g'ri JSON formati: {response.text}")
                await query.message.reply_text("❌ Serverdan noto'g'ri javob qaytdi")
                return
                
        except Exception as e:
            error_msg = f"❌ Serverga ulanishda xatolik: {e}"
            print(error_msg)
            await query.message.reply_text("❌ Serverga ulanishda xatolik")
            return
        
        if result.get("success"):
            print(f"✅ Backend muvaffaqiyatli javob berdi. Teacher: {result.get('teacher_name')}")
            
            # Student ID ni olish
            student_id = result.get("student_id")
            
            # Student telegram ID sini olish
            student_telegram_id = await get_student_telegram_id(student_id) if student_id else None
            
            if not student_telegram_id:
                print("❌ Student telegram ID topilmadi")
            
            # O'qituvchi ma'lumotlarini saqlaymiz
            context.user_data['active_assignment'] = {
                'help_request_id': help_request_id,
                'student_id': student_id,
                'student_telegram_id': student_telegram_id,
                'teacher_name': teacher_name
            }
            
            # Loglarni olamiz
            logs = await get_logs(help_request_id)
            print(f"📋 {len(logs)} ta log topildi")
            
            url = f"https://iqmath.uz/dashboard/teacher/student-examples/{help_request_id}"
            
            # Xabarlarni yangilaymiz
            success_count = 0
            for log in logs:
                try:
                    if log.chat_id == query.message.chat_id:
                        # Javob bergan o'qituvchi uchun
                        new_text = query.message.text.replace("👨‍🏫", "✅ Siz javob berayapsiz")
                        
                        new_markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton("👨‍🏫 Siz javob berayapsiz", callback_data=f"assigned_{help_request_id}")],
                            [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")],
                            [InlineKeyboardButton("🔗 Savolga o'tish", url=url)]
                        ])
                        
                        await context.bot.edit_message_text(
                            chat_id=log.chat_id,
                            message_id=log.message_id,
                            text=new_text,
                            reply_markup=new_markup,
                            parse_mode="HTML"
                        )
                        print(f"✏️ Javob bergan o'qituvchi xabari yangilandi: {log.chat_id}")
                        
                        # Yo'riqnoma xabarini yuboramiz
                        await query.message.reply_text(
                            "✅ Endi siz bu savolga javob berayapsiz.\n\n" +
                            "Talabaga javob yuborish uchun shu xabarga 'reply' qilib yozing yoki " +
                            "to'g'ridan-to'g'ri yozib, keyin 'Javobni yuborish' tugmasini bosing.",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                            ])
                        )
                    else:
                        # Boshqa o'qituvchilar uchun
                        new_text = query.message.text.replace("👨‍🏫", f"👨‍🏫 {teacher_name} javob beryapti")
                        
                        other_teachers_markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton("👨‍🏫 Javob berilmoqda", callback_data=f"taken_{help_request_id}")],
                            [InlineKeyboardButton("🔄 O'zim javob qilaman", callback_data=f"takeover_{help_request_id}")],
                            [InlineKeyboardButton("🔗 Savolga o'tish", url=url)]
                        ])
                        
                        await context.bot.edit_message_text(
                            chat_id=log.chat_id,
                            message_id=log.message_id,
                            text=new_text,
                            reply_markup=other_teachers_markup,
                            parse_mode="HTML"
                        )
                        print(f"✏️ Boshqa o'qituvchi xabari yangilandi: {log.chat_id}")
                    
                    success_count += 1
                        
                except Exception as e:
                    print(f"❌ Xabar yangilashda xatolik (chat_id: {log.chat_id}): {e}")
            
            print(f"✅ {success_count}/{len(logs)} ta xabar yangilandi")
            
        else:
            error_msg = result.get("message", "❌ Noma'lum xatolik")
            print(f"❌ Backend xatosi: {error_msg}")
            await query.message.reply_text(error_msg)
    
    elif data.startswith("send_"):
        help_request_id = int(data.split("_")[1])
        assignment = context.user_data.get('active_assignment', {})
        
        if assignment.get('help_request_id') != help_request_id:
            await query.message.reply_text("❌ Siz bu savolga javob berish huquqiga ega emassiz")
            return
        
        student_telegram_id = assignment.get('student_telegram_id')
        
        if not student_telegram_id:
            # Agar student telegram ID bo'lmasa, qayta urinib ko'ramiz
            student_id = assignment.get('student_id')
            if student_id:
                student_telegram_id = await get_student_telegram_id(student_id)
            
            if not student_telegram_id:
                await query.message.reply_text("❌ Talabaning Telegram ID sini topib bo'lmadi")
                return
        
        if 'answer_text' not in context.user_data:
            await query.message.reply_text("❌ Avval javob matnini yuboring")
            return
        
        answer_text = context.user_data['answer_text']
        teacher_name = assignment.get('teacher_name', 'O\'qituvchi')
        
        try:
            await context.bot.send_message(
                chat_id=student_telegram_id,
                text=f"👨‍🏫 {teacher_name}dan javob:\n\n{answer_text}"
            )
            await query.message.reply_text("✅ Javobingiz talabaga yuborildi")
            
            # Ma'lumotlarni tozalash
            if 'answer_text' in context.user_data:
                del context.user_data['answer_text']
            if 'active_assignment' in context.user_data:
                del context.user_data['active_assignment']
            
        except Exception as e:
            print(f"❌ Javob yuborishda xatolik: {e}")
            await query.message.reply_text("❌ Javob yuborishda xatolik yuz berdi")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Agar xabar reply bo'lsa va active_assignment mavjud bo'lsa
    if update.message.reply_to_message and 'active_assignment' in context.user_data:
        context.user_data['answer_text'] = update.message.text
        help_request_id = context.user_data['active_assignment']['help_request_id']
        
        await update.message.reply_text(
            "✅ Javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
            ])
        )
    else:
        # Agar oddiy xabar bo'lsa, uni e'tiborsiz qoldirish
        pass

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()