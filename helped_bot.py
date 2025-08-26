import os
import django
import requests
import sys
import urllib.parse
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters, CommandHandler
from asgiref.sync import sync_to_async
import tempfile

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

# Yangi API URL lar
CHECK_TELEGRAM_ID_API = "https://api.iqmath.uz/api/v1/auth/check-telegram-id/"
UPDATE_TELEGRAM_ID_API = "https://api.iqmath.uz/api/v1/auth/update-telegram-id/"

# ================= TELEGRAM SERVICE FUNCTIONS =================

def send_question_to_telegram(student_full_name, question_id, result_json, student_id):
    """
    Savolni barcha o'qituvchilarga yuborish
    """
    student_name_encoded = urllib.parse.quote(student_full_name)
    student_name_encoded = urllib.parse.quote(str(student_id))
    url = f"https://mentor.iqmath.uz/dashboard/teacher/student-examples/{question_id}?student_name={student_name_encoded}"

    result = result_json[0] if result_json else {}
    total = result.get("total_answers", "-")
    correct = result.get("correct_answers", "-")
    score = result.get("score", "-")

    text = (
        f"📥 <b>Yangi savol!</b>\n"
        f"👤 <b>O'quvchi:</b>{student_id}--{student_full_name}\n"
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

# ================= YANGI FUNKSIYALAR =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi bilan ishlovchi funksiya"""
    user = update.effective_user
    print(f"🚀 Start bosildi: {user.id}, {user.first_name}")
    
    # Telegram ID ni API ga yuborib tekshiramiz
    try:
        response = requests.post(
            CHECK_TELEGRAM_ID_API,
            json={"telegram_id": user.id},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            role = data.get("role")
            
            if role == "teacher":
                # O'qituvchi uchun menu
                keyboard = [
                    [InlineKeyboardButton("📬 Menga kelgan murojaatlar", callback_data='teacher_applications')],
                    [InlineKeyboardButton("📊 Murojaatlar statistikasi", callback_data='teacher_stats')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"👨‍🏫 Assalomu alaykum, {data.get('data', {}).get('full_name', 'O\'qituvchi')}!\n"
                    f"O'qituvchi paneliga xush kelibsiz.",
                    reply_markup=reply_markup
                )
                
            elif role == "student":
                # O'quvchi uchun menu
                keyboard = [
                    [InlineKeyboardButton("📬 Men yuborgan murojaatlar", callback_data='student_applications')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"👨‍🎓 Assalomu alaykum, {data.get('data', {}).get('full_name', 'O\'quvchi')}!\n"
                    f"O'quvchi paneliga xush kelibsiz.",
                    reply_markup=reply_markup
                )
                
            else:
                # Role aniqlanmagan yoki boshqa holat
                await ask_for_phone(update, context)
                
        elif response.status_code == 404:
            # Foydalanuvchi topilmadi, telefon raqam so'raymiz
            await ask_for_phone(update, context)
        else:
            # Boshqa xatolik
            await update.message.reply_text("❌ Server xatosi. Iltimos, keyinroq urunib ko'ring.")
            
    except Exception as e:
        print(f"❌ Start funksiyasida xatolik: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, keyinroq urunib ko'ring.")

async def ask_for_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Telefon raqam so'rovchi funksiya"""
    # Kontakt yuborish tugmasi
    keyboard = [[KeyboardButton("📞 Telefon raqamni yuborish", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "👋 Assalomu alaykum! Botdan foydalanish uchun ro'yxatdan o'tishingiz kerak.\n\n"
        "Iltimos, telefon raqamingizni yuboring:",
        reply_markup=reply_markup
    )
    
    # Holatni saqlaymiz
    context.user_data['waiting_for_phone'] = True

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi kontakt yuborganda ishlaydigan funksiya"""
    if 'waiting_for_phone' not in context.user_data:
        return
    
    contact = update.message.contact
    phone_number = contact.phone_number
    telegram_id = update.effective_user.id
    
    # + ni olib tashlaymiz agar mavjud bo'lsa
    if phone_number.startswith('+'):
        phone_number = phone_number[1:]
    
    print(f"📞 Telefon raqam qabul qilindi: {phone_number}, Telegram ID: {telegram_id}")
    
    # API ga telefon va telegram_id ni yuboramiz
    try:
        response = requests.post(
            UPDATE_TELEGRAM_ID_API,
            json={
                "phone": phone_number,
                "telegram_id": telegram_id
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            role = data.get("role")
            
            if role == "teacher":
                keyboard = [
                    [InlineKeyboardButton("📬 Menga kelgan murojaatlar", callback_data='teacher_applications')],
                    [InlineKeyboardButton("📊 Murojaatlar statistikasi", callback_data='teacher_stats')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"👨‍🏫 Assalomu alaykum, {data.get('data', {}).get('full_name', 'O\'qituvchi')}!\n"
                    f"O'qituvchi paneliga xush kelibsiz.",
                    reply_markup=reply_markup
                )
                
            elif role == "student":
                keyboard = [
                    [InlineKeyboardButton("📬 Men yuborgan murojaatlar", callback_data='student_applications')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"👨‍🎓 Assalomu alaykum, {data.get('data', {}).get('full_name', 'O\'quvchi')}!\n"
                    f"O'quvchi paneliga xush kelibsiz.",
                    reply_markup=reply_markup
                )
                
            else:
                await update.message.reply_text(
                    "❌ Profilingiz topilmadi. Iltimos, avval veb-saytda ro'yxatdan o'ting."
                )
                
        elif response.status_code == 404:
            await update.message.reply_text(
                "❌ Telefon raqamingiz topilmadi. Iltimos, avval veb-saytda ro'yxatdan o'ting."
            )
        else:
            await update.message.reply_text(
                "❌ Xatolik yuz berdi. Iltimos, keyinroq urunib ko'ring."
            )
            
        # Holatni tozalaymiz
        if 'waiting_for_phone' in context.user_data:
            del context.user_data['waiting_for_phone']
            
    except Exception as e:
        print(f"❌ Kontaktni qayta ishlashda xatolik: {e}")
        await update.message.reply_text(
            "❌ Xatolik yuz berdi. Iltimos, keyinroq urunib ko'ring."
        )

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

@sync_to_async
def get_student_telegram_id(student_id):
    """Student ID orqali student telegram ID sini olish"""
    try:
        print(f"🔍 Student ID: {student_id} uchun Telegram ID so'ralmoqda")
        response = requests.post(
            TELEGRAM_ID_API,
            json={"student_id": student_id},
            timeout=5
        )
        print(f"📡 Telegram ID API javobi: {response.status_code}, {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            telegram_id = data.get("telegram_id")
            print(f"✅ Telegram ID topildi: {telegram_id}")
            return telegram_id
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
                'teacher_name': teacher_name,
                'teacher_id': telegram_id
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
                            "Talabaga javob yuborish uchun istalgan turdagi kontent yuboring:\n" +
                            "📝 Matn xabari\n🖼 Rasm\n🎥 Video\n🎵 Audio\n\n" +
                            "Yoki shu xabarga 'reply' qilib yuboring, so'ngra '📤 Javobni yuborish' tugmasini bosing.",
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
            print(help_request_id)
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
                'teacher_name': teacher_name,
                'teacher_id': telegram_id
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
                            "Talabaga javob yuborish uchun istalgan turdagi kontent yuboring:\n" +
                            "📝 Matn xabari\n🖼 Rasm\n🎥 Video\n🎵 Audio\n\n" +
                            "Yoki shu xabarga 'reply' qilib yuboring, so'ngra '📤 Javobni yuborish' tugmasini bosing.",
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

        # API orqali telegram_id olish
        try:
            response = requests.post(
                "https://api.iqmath.uz/api/v1/func_student/student/student_id/telegram_id/",
                json={"topic_help_id": help_request_id},
                timeout=5
            )
            if response.status_code == 200:
                telegram_id = response.json().get("telegram_id")
                assignment['student_telegram_id'] = telegram_id
            else:
                await query.message.reply_text("❌ Telegram ID topilmadi.")
                return
        except requests.RequestException as e:
            await query.message.reply_text("❌ Server bilan bog‘lanishda xatolik.")
            return
        
        student_telegram_id = telegram_id
        
        if not student_telegram_id:
            # Agar student telegram ID bo'lmasa, qayta urinib ko'ramiz
            student_id = assignment.get('student_id')
            print(help_request_id)
            if student_id:
                student_telegram_id = await get_student_telegram_id(student_id)
            
            if not student_telegram_id:
                await query.message.reply_text("❌ Talabaning Telegram ID sini topib bo'lmadi")
                return
        
        # Har xil turdagi javoblarni yuborish
        teacher_name = assignment.get('teacher_name', 'O\'qituvchi')
        teacher_id = assignment.get('teacher_id', query.from_user.id)
        
        try:
            if 'answer_text' in context.user_data:
                # Matnli javob
                answer_text = context.user_data['answer_text']
                await context.bot.send_message(
                    chat_id=student_telegram_id,
                    text=f"👨‍🏫 {teacher_name}dan javob:\n\n{answer_text}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❓ Yana savolim bor", callback_data=f"reply_{help_request_id}_{teacher_id}")]
                    ])
                )
            
            elif 'answer_photo' in context.user_data:
                # Rasmli javob
                photo_file_id = context.user_data['answer_photo']
                caption = context.user_data.get('answer_caption', f"👨‍🏫 {teacher_name}dan javob")
                await context.bot.send_photo(
                    chat_id=student_telegram_id,
                    photo=photo_file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❓ Yana savolim bor", callback_data=f"reply_{help_request_id}_{teacher_id}")]
                    ])
                )
            
            elif 'answer_video' in context.user_data:
                # Videoli javob
                video_file_id = context.user_data['answer_video']
                caption = context.user_data.get('answer_caption', f"👨‍🏫 {teacher_name}dan javob")
                await context.bot.send_video(
                    chat_id=student_telegram_id,
                    video=video_file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❓ Yana savolim bor", callback_data=f"reply_{help_request_id}_{teacher_id}")]
                    ])
                )
            
            elif 'answer_audio' in context.user_data:
                # Audioli javob
                audio_file_id = context.user_data['answer_audio']
                caption = context.user_data.get('answer_caption', f"👨‍🏫 {teacher_name}dan javob")
                await context.bot.send_audio(
                    chat_id=student_telegram_id,
                    audio=audio_file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❓ Yana savolim bor", callback_data=f"reply_{help_request_id}_{teacher_id}")]
                    ])
                )
            
            elif 'answer_document' in context.user_data:
                # Hujjatli javob
                document_file_id = context.user_data['answer_document']
                caption = context.user_data.get('answer_caption', f"👨‍🏫 {teacher_name}dan javob")
                await context.bot.send_document(
                    chat_id=student_telegram_id,
                    document=document_file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❓ Yana savolim bor", callback_data=f"reply_{help_request_id}_{teacher_id}")]
                    ])
                )
            
            else:
                await query.message.reply_text("❌ Avval javob yuboring")
                return
            
            await query.message.reply_text("✅ Javobingiz talabaga yuborildi")
            
            # Ma'lumotlarni tozalash
            for key in ['answer_text', 'answer_photo', 'answer_video', 'answer_audio', 'answer_document', 'answer_caption']:
                if key in context.user_data:
                    del context.user_data[key]
            
            # Faol topshiriqni saqlab qolamiz, chunki talaba yana savol berishi mumkin
            context.user_data['active_assignment']['last_teacher_id'] = query.from_user.id
            
        except Exception as e:
            print(f"❌ Javob yuborishda xatolik: {e}")
            await query.message.reply_text("❌ Javob yuborishda xatolik yuz berdi")
    
    elif data.startswith("reply_"):
        # Talaba yana savol berish tugmasini bosganda
        parts = data.split("_")
        help_request_id = int(parts[1])
        teacher_id = int(parts[2])
        
        # Talabaga javob yozish uchun so'rov yuboramiz
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="❓ Savolingizni yozing. O'qituvchi sizga javob beradi:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_question")]
            ])
        )
        
        # Talabaning holatini saqlaymiz
        context.user_data['waiting_for_question'] = {
            'help_request_id': help_request_id,
            'teacher_id': teacher_id,
            'student_id': query.from_user.id
        }
    
    elif data == "cancel_question":
        # Talaba savol berishni bekor qilganda
        if 'waiting_for_question' in context.user_data:
            del context.user_data['waiting_for_question']
        await query.message.edit_text("✅ Savol berish bekor qilindi.")
    
    # Yangi tugmalar uchun handlerlar
    elif data == 'teacher_applications':
        await query.message.reply_text("📬 Menga kelgan murojaatlar bo'limi. Hozircha bu funksiya ishlamaydi.")
    
    elif data == 'teacher_stats':
        await query.message.reply_text("📊 Murojaatlar statistikasi bo'limi. Hozircha bu funksiya ishlamaydi.")
    
    elif data == 'student_applications':
        await query.message.reply_text("📬 Men yuborgan murojaatlar bo'limi. Hozircha bu funksiya ishlamaydi.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Agar talaba savol yozayotgan bo'lsa
    if 'waiting_for_question' in context.user_data and update.message.from_user.id == context.user_data['waiting_for_question']['student_id']:
        question_data = context.user_data['waiting_for_question']
        help_request_id = question_data['help_request_id']
        teacher_id = question_data['teacher_id']
        
        # Talabaning xabarini o'qituvchiga yuboramiz
        try:
            if update.message.text:
                await context.bot.send_message(
                    chat_id=teacher_id,
                    text=f"❓ Talabadan qo'shimcha savol:\n\n{update.message.text}\n\n" +
                         f"🆔 Savol ID: {help_request_id}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Javob berish", callback_data=f"send_{help_request_id}")]
                    ])
                )
            
            elif update.message.photo:
                caption = update.message.caption or f"❓ Talabadan qo'shimcha savol (🆔 Savol ID: {help_request_id})"
                await context.bot.send_photo(
                    chat_id=teacher_id,
                    photo=update.message.photo[-1].file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Javob berish", callback_data=f"send_{help_request_id}")]
                    ])
                )
            
            elif update.message.video:
                caption = update.message.caption or f"❓ Talabadan qo'shimcha savol (🆔 Savol ID: {help_request_id})"
                await context.bot.send_video(
                    chat_id=teacher_id,
                    video=update.message.video.file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Javob berish", callback_data=f"send_{help_request_id}")]
                    ])
                )
            
            elif update.message.audio:
                caption = update.message.caption or f"❓ Talabadan qo'shimcha savol (🆔 Savol ID: {help_request_id})"
                await context.bot.send_audio(
                    chat_id=teacher_id,
                    audio=update.message.audio.file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Javob berish", callback_data=f"send_{help_request_id}")]
                    ])
                )
            
            elif update.message.document:
                caption = update.message.caption or f"❓ Talabadan qo'shimcha savol (🆔 Savol ID: {help_request_id})"
                await context.bot.send_document(
                    chat_id=teacher_id,
                    document=update.message.document.file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Javob berish", callback_data=f"send_{help_request_id}")]
                    ])
                )
            
            await update.message.reply_text("✅ Savolingiz o'qituvchiga yuborildi. Tez orada javob olasiz.")
            
            # Holatni tozalaymiz
            del context.user_data['waiting_for_question']
            
        except Exception as e:
            print(f"❌ Savolni yuborishda xatolik: {e}")
            await update.message.reply_text("❌ Savolni yuborishda xatolik yuz berdi.")
    
    # Agar xabar reply bo'lsa va active_assignment mavjud bo'lsa (o'qituvchi javob yozyapti)
    elif update.message.reply_to_message and 'active_assignment' in context.user_data and update.message.from_user.id in TEACHER_CHAT_IDS:
        help_request_id = context.user_data['active_assignment']['help_request_id']
        
        # Matnli javob
        if update.message.text:
            context.user_data['answer_text'] = update.message.text
            await update.message.reply_text(
                "✅ Matnli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Rasmli javob
        elif update.message.photo:
            context.user_data['answer_photo'] = update.message.photo[-1].file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Rasmli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Videoli javob
        elif update.message.video:
            context.user_data['answer_video'] = update.message.video.file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Videoli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Audioli javob
        elif update.message.audio:
            context.user_data['answer_audio'] = update.message.audio.file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Audioli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Hujjatli javob
        elif update.message.document:
            context.user_data['answer_document'] = update.message.document.file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Hujjatli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
    
    # Agar oddiy xabar bo'lsa va active_assignment mavjud bo'lsa (o'qituvchi javob yozyapti)
    elif 'active_assignment' in context.user_data and update.message.from_user.id in TEACHER_CHAT_IDS:
        help_request_id = context.user_data['active_assignment']['help_request_id']
        
        # Matnli javob
        if update.message.text:
            context.user_data['answer_text'] = update.message.text
            await update.message.reply_text(
                "✅ Matnli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Rasmli javob
        elif update.message.photo:
            context.user_data['answer_photo'] = update.message.photo[-1].file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Rasmli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Videoli javob
        elif update.message.video:
            context.user_data['answer_video'] = update.message.video.file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Videoli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Audioli javob
        elif update.message.audio:
            context.user_data['answer_audio'] = update.message.audio.file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Audioli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Hujjatli javob
        elif update.message.document:
            context.user_data['answer_document'] = update.message.document.file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Hujjatli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Document filter ni alohida qo'shing
    document_filter = filters.Document.ALL if hasattr(filters, 'Document') else filters.DOCUMENT
    application.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VIDEO | filters.AUDIO | document_filter, 
        handle_message
    ))
    
    print("✅ Bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()import os
import django
import requests
import sys
import urllib.parse
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters, CommandHandler
from asgiref.sync import sync_to_async
import tempfile

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

# Yangi API URL lar
CHECK_TELEGRAM_ID_API = "https://api.iqmath.uz/api/v1/auth/check-telegram-id/"
UPDATE_TELEGRAM_ID_API = "https://api.iqmath.uz/api/v1/auth/update-telegram-id/"

# ================= TELEGRAM SERVICE FUNCTIONS =================

def send_question_to_telegram(student_full_name, question_id, result_json, student_id):
    """
    Savolni barcha o'qituvchilarga yuborish
    """
    student_name_encoded = urllib.parse.quote(student_full_name)
    student_name_encoded = urllib.parse.quote(str(student_id))
    url = f"https://mentor.iqmath.uz/dashboard/teacher/student-examples/{question_id}?student_name={student_name_encoded}"

    result = result_json[0] if result_json else {}
    total = result.get("total_answers", "-")
    correct = result.get("correct_answers", "-")
    score = result.get("score", "-")

    text = (
        f"📥 <b>Yangi savol!</b>\n"
        f"👤 <b>O'quvchi:</b>{student_id}--{student_full_name}\n"
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

# ================= YANGI FUNKSIYALAR =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi bilan ishlovchi funksiya"""
    user = update.effective_user
    print(f"🚀 Start bosildi: {user.id}, {user.first_name}")
    
    # Telegram ID ni API ga yuborib tekshiramiz
    try:
        response = requests.post(
            CHECK_TELEGRAM_ID_API,
            json={"telegram_id": user.id},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            role = data.get("role")
            
            if role == "teacher":
                # O'qituvchi uchun menu
                keyboard = [
                    [InlineKeyboardButton("📬 Menga kelgan murojaatlar", callback_data='teacher_applications')],
                    [InlineKeyboardButton("📊 Murojaatlar statistikasi", callback_data='teacher_stats')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"👨‍🏫 Assalomu alaykum, {data.get('data', {}).get('full_name', 'O\'qituvchi')}!\n"
                    f"O'qituvchi paneliga xush kelibsiz.",
                    reply_markup=reply_markup
                )
                
            elif role == "student":
                # O'quvchi uchun menu
                keyboard = [
                    [InlineKeyboardButton("📬 Men yuborgan murojaatlar", callback_data='student_applications')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"👨‍🎓 Assalomu alaykum, {data.get('data', {}).get('full_name', 'O\'quvchi')}!\n"
                    f"O'quvchi paneliga xush kelibsiz.",
                    reply_markup=reply_markup
                )
                
            else:
                # Role aniqlanmagan yoki boshqa holat
                await ask_for_phone(update, context)
                
        elif response.status_code == 404:
            # Foydalanuvchi topilmadi, telefon raqam so'raymiz
            await ask_for_phone(update, context)
        else:
            # Boshqa xatolik
            await update.message.reply_text("❌ Server xatosi. Iltimos, keyinroq urunib ko'ring.")
            
    except Exception as e:
        print(f"❌ Start funksiyasida xatolik: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, keyinroq urunib ko'ring.")

async def ask_for_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Telefon raqam so'rovchi funksiya"""
    # Kontakt yuborish tugmasi
    keyboard = [[KeyboardButton("📞 Telefon raqamni yuborish", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "👋 Assalomu alaykum! Botdan foydalanish uchun ro'yxatdan o'tishingiz kerak.\n\n"
        "Iltimos, telefon raqamingizni yuboring:",
        reply_markup=reply_markup
    )
    
    # Holatni saqlaymiz
    context.user_data['waiting_for_phone'] = True

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi kontakt yuborganda ishlaydigan funksiya"""
    if 'waiting_for_phone' not in context.user_data:
        return
    
    contact = update.message.contact
    phone_number = contact.phone_number
    telegram_id = update.effective_user.id
    
    # + ni olib tashlaymiz agar mavjud bo'lsa
    if phone_number.startswith('+'):
        phone_number = phone_number[1:]
    
    print(f"📞 Telefon raqam qabul qilindi: {phone_number}, Telegram ID: {telegram_id}")
    
    # API ga telefon va telegram_id ni yuboramiz
    try:
        response = requests.post(
            UPDATE_TELEGRAM_ID_API,
            json={
                "phone": phone_number,
                "telegram_id": telegram_id
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            role = data.get("role")
            
            if role == "teacher":
                keyboard = [
                    [InlineKeyboardButton("📬 Menga kelgan murojaatlar", callback_data='teacher_applications')],
                    [InlineKeyboardButton("📊 Murojaatlar statistikasi", callback_data='teacher_stats')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"👨‍🏫 Assalomu alaykum, {data.get('data', {}).get('full_name', 'O\'qituvchi')}!\n"
                    f"O'qituvchi paneliga xush kelibsiz.",
                    reply_markup=reply_markup
                )
                
            elif role == "student":
                keyboard = [
                    [InlineKeyboardButton("📬 Men yuborgan murojaatlar", callback_data='student_applications')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"👨‍🎓 Assalomu alaykum, {data.get('data', {}).get('full_name', 'O\'quvchi')}!\n"
                    f"O'quvchi paneliga xush kelibsiz.",
                    reply_markup=reply_markup
                )
                
            else:
                await update.message.reply_text(
                    "❌ Profilingiz topilmadi. Iltimos, avval veb-saytda ro'yxatdan o'ting."
                )
                
        elif response.status_code == 404:
            await update.message.reply_text(
                "❌ Telefon raqamingiz topilmadi. Iltimos, avval veb-saytda ro'yxatdan o'ting."
            )
        else:
            await update.message.reply_text(
                "❌ Xatolik yuz berdi. Iltimos, keyinroq urunib ko'ring."
            )
            
        # Holatni tozalaymiz
        if 'waiting_for_phone' in context.user_data:
            del context.user_data['waiting_for_phone']
            
    except Exception as e:
        print(f"❌ Kontaktni qayta ishlashda xatolik: {e}")
        await update.message.reply_text(
            "❌ Xatolik yuz berdi. Iltimos, keyinroq urunib ko'ring."
        )

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

@sync_to_async
def get_student_telegram_id(student_id):
    """Student ID orqali student telegram ID sini olish"""
    try:
        print(f"🔍 Student ID: {student_id} uchun Telegram ID so'ralmoqda")
        response = requests.post(
            TELEGRAM_ID_API,
            json={"student_id": student_id},
            timeout=5
        )
        print(f"📡 Telegram ID API javobi: {response.status_code}, {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            telegram_id = data.get("telegram_id")
            print(f"✅ Telegram ID topildi: {telegram_id}")
            return telegram_id
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
                'teacher_name': teacher_name,
                'teacher_id': telegram_id
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
                            "Talabaga javob yuborish uchun istalgan turdagi kontent yuboring:\n" +
                            "📝 Matn xabari\n🖼 Rasm\n🎥 Video\n🎵 Audio\n\n" +
                            "Yoki shu xabarga 'reply' qilib yuboring, so'ngra '📤 Javobni yuborish' tugmasini bosing.",
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
            print(help_request_id)
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
                'teacher_name': teacher_name,
                'teacher_id': telegram_id
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
                            "Talabaga javob yuborish uchun istalgan turdagi kontent yuboring:\n" +
                            "📝 Matn xabari\n🖼 Rasm\n🎥 Video\n🎵 Audio\n\n" +
                            "Yoki shu xabarga 'reply' qilib yuboring, so'ngra '📤 Javobni yuborish' tugmasini bosing.",
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

        # API orqali telegram_id olish
        try:
            response = requests.post(
                "https://api.iqmath.uz/api/v1/func_student/student/student_id/telegram_id/",
                json={"topic_help_id": help_request_id},
                timeout=5
            )
            if response.status_code == 200:
                telegram_id = response.json().get("telegram_id")
                assignment['student_telegram_id'] = telegram_id
            else:
                await query.message.reply_text("❌ Telegram ID topilmadi.")
                return
        except requests.RequestException as e:
            await query.message.reply_text("❌ Server bilan bog‘lanishda xatolik.")
            return
        
        student_telegram_id = telegram_id
        
        if not student_telegram_id:
            # Agar student telegram ID bo'lmasa, qayta urinib ko'ramiz
            student_id = assignment.get('student_id')
            print(help_request_id)
            if student_id:
                student_telegram_id = await get_student_telegram_id(student_id)
            
            if not student_telegram_id:
                await query.message.reply_text("❌ Talabaning Telegram ID sini topib bo'lmadi")
                return
        
        # Har xil turdagi javoblarni yuborish
        teacher_name = assignment.get('teacher_name', 'O\'qituvchi')
        teacher_id = assignment.get('teacher_id', query.from_user.id)
        
        try:
            if 'answer_text' in context.user_data:
                # Matnli javob
                answer_text = context.user_data['answer_text']
                await context.bot.send_message(
                    chat_id=student_telegram_id,
                    text=f"👨‍🏫 {teacher_name}dan javob:\n\n{answer_text}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❓ Yana savolim bor", callback_data=f"reply_{help_request_id}_{teacher_id}")]
                    ])
                )
            
            elif 'answer_photo' in context.user_data:
                # Rasmli javob
                photo_file_id = context.user_data['answer_photo']
                caption = context.user_data.get('answer_caption', f"👨‍🏫 {teacher_name}dan javob")
                await context.bot.send_photo(
                    chat_id=student_telegram_id,
                    photo=photo_file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❓ Yana savolim bor", callback_data=f"reply_{help_request_id}_{teacher_id}")]
                    ])
                )
            
            elif 'answer_video' in context.user_data:
                # Videoli javob
                video_file_id = context.user_data['answer_video']
                caption = context.user_data.get('answer_caption', f"👨‍🏫 {teacher_name}dan javob")
                await context.bot.send_video(
                    chat_id=student_telegram_id,
                    video=video_file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❓ Yana savolim bor", callback_data=f"reply_{help_request_id}_{teacher_id}")]
                    ])
                )
            
            elif 'answer_audio' in context.user_data:
                # Audioli javob
                audio_file_id = context.user_data['answer_audio']
                caption = context.user_data.get('answer_caption', f"👨‍🏫 {teacher_name}dan javob")
                await context.bot.send_audio(
                    chat_id=student_telegram_id,
                    audio=audio_file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❓ Yana savolim bor", callback_data=f"reply_{help_request_id}_{teacher_id}")]
                    ])
                )
            
            elif 'answer_document' in context.user_data:
                # Hujjatli javob
                document_file_id = context.user_data['answer_document']
                caption = context.user_data.get('answer_caption', f"👨‍🏫 {teacher_name}dan javob")
                await context.bot.send_document(
                    chat_id=student_telegram_id,
                    document=document_file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❓ Yana savolim bor", callback_data=f"reply_{help_request_id}_{teacher_id}")]
                    ])
                )
            
            else:
                await query.message.reply_text("❌ Avval javob yuboring")
                return
            
            await query.message.reply_text("✅ Javobingiz talabaga yuborildi")
            
            # Ma'lumotlarni tozalash
            for key in ['answer_text', 'answer_photo', 'answer_video', 'answer_audio', 'answer_document', 'answer_caption']:
                if key in context.user_data:
                    del context.user_data[key]
            
            # Faol topshiriqni saqlab qolamiz, chunki talaba yana savol berishi mumkin
            context.user_data['active_assignment']['last_teacher_id'] = query.from_user.id
            
        except Exception as e:
            print(f"❌ Javob yuborishda xatolik: {e}")
            await query.message.reply_text("❌ Javob yuborishda xatolik yuz berdi")
    
    elif data.startswith("reply_"):
        # Talaba yana savol berish tugmasini bosganda
        parts = data.split("_")
        help_request_id = int(parts[1])
        teacher_id = int(parts[2])
        
        # Talabaga javob yozish uchun so'rov yuboramiz
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="❓ Savolingizni yozing. O'qituvchi sizga javob beradi:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_question")]
            ])
        )
        
        # Talabaning holatini saqlaymiz
        context.user_data['waiting_for_question'] = {
            'help_request_id': help_request_id,
            'teacher_id': teacher_id,
            'student_id': query.from_user.id
        }
    
    elif data == "cancel_question":
        # Talaba savol berishni bekor qilganda
        if 'waiting_for_question' in context.user_data:
            del context.user_data['waiting_for_question']
        await query.message.edit_text("✅ Savol berish bekor qilindi.")
    
    # Yangi tugmalar uchun handlerlar
    elif data == 'teacher_applications':
        await query.message.reply_text("📬 Menga kelgan murojaatlar bo'limi. Hozircha bu funksiya ishlamaydi.")
    
    elif data == 'teacher_stats':
        await query.message.reply_text("📊 Murojaatlar statistikasi bo'limi. Hozircha bu funksiya ishlamaydi.")
    
    elif data == 'student_applications':
        await query.message.reply_text("📬 Men yuborgan murojaatlar bo'limi. Hozircha bu funksiya ishlamaydi.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Agar talaba savol yozayotgan bo'lsa
    if 'waiting_for_question' in context.user_data and update.message.from_user.id == context.user_data['waiting_for_question']['student_id']:
        question_data = context.user_data['waiting_for_question']
        help_request_id = question_data['help_request_id']
        teacher_id = question_data['teacher_id']
        
        # Talabaning xabarini o'qituvchiga yuboramiz
        try:
            if update.message.text:
                await context.bot.send_message(
                    chat_id=teacher_id,
                    text=f"❓ Talabadan qo'shimcha savol:\n\n{update.message.text}\n\n" +
                         f"🆔 Savol ID: {help_request_id}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Javob berish", callback_data=f"send_{help_request_id}")]
                    ])
                )
            
            elif update.message.photo:
                caption = update.message.caption or f"❓ Talabadan qo'shimcha savol (🆔 Savol ID: {help_request_id})"
                await context.bot.send_photo(
                    chat_id=teacher_id,
                    photo=update.message.photo[-1].file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Javob berish", callback_data=f"send_{help_request_id}")]
                    ])
                )
            
            elif update.message.video:
                caption = update.message.caption or f"❓ Talabadan qo'shimcha savol (🆔 Savol ID: {help_request_id})"
                await context.bot.send_video(
                    chat_id=teacher_id,
                    video=update.message.video.file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Javob berish", callback_data=f"send_{help_request_id}")]
                    ])
                )
            
            elif update.message.audio:
                caption = update.message.caption or f"❓ Talabadan qo'shimcha savol (🆔 Savol ID: {help_request_id})"
                await context.bot.send_audio(
                    chat_id=teacher_id,
                    audio=update.message.audio.file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Javob berish", callback_data=f"send_{help_request_id}")]
                    ])
                )
            
            elif update.message.document:
                caption = update.message.caption or f"❓ Talabadan qo'shimcha savol (🆔 Savol ID: {help_request_id})"
                await context.bot.send_document(
                    chat_id=teacher_id,
                    document=update.message.document.file_id,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Javob berish", callback_data=f"send_{help_request_id}")]
                    ])
                )
            
            await update.message.reply_text("✅ Savolingiz o'qituvchiga yuborildi. Tez orada javob olasiz.")
            
            # Holatni tozalaymiz
            del context.user_data['waiting_for_question']
            
        except Exception as e:
            print(f"❌ Savolni yuborishda xatolik: {e}")
            await update.message.reply_text("❌ Savolni yuborishda xatolik yuz berdi.")
    
    # Agar xabar reply bo'lsa va active_assignment mavjud bo'lsa (o'qituvchi javob yozyapti)
    elif update.message.reply_to_message and 'active_assignment' in context.user_data and update.message.from_user.id in TEACHER_CHAT_IDS:
        help_request_id = context.user_data['active_assignment']['help_request_id']
        
        # Matnli javob
        if update.message.text:
            context.user_data['answer_text'] = update.message.text
            await update.message.reply_text(
                "✅ Matnli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Rasmli javob
        elif update.message.photo:
            context.user_data['answer_photo'] = update.message.photo[-1].file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Rasmli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Videoli javob
        elif update.message.video:
            context.user_data['answer_video'] = update.message.video.file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Videoli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Audioli javob
        elif update.message.audio:
            context.user_data['answer_audio'] = update.message.audio.file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Audioli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Hujjatli javob
        elif update.message.document:
            context.user_data['answer_document'] = update.message.document.file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Hujjatli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
    
    # Agar oddiy xabar bo'lsa va active_assignment mavjud bo'lsa (o'qituvchi javob yozyapti)
    elif 'active_assignment' in context.user_data and update.message.from_user.id in TEACHER_CHAT_IDS:
        help_request_id = context.user_data['active_assignment']['help_request_id']
        
        # Matnli javob
        if update.message.text:
            context.user_data['answer_text'] = update.message.text
            await update.message.reply_text(
                "✅ Matnli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Rasmli javob
        elif update.message.photo:
            context.user_data['answer_photo'] = update.message.photo[-1].file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Rasmli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Videoli javob
        elif update.message.video:
            context.user_data['answer_video'] = update.message.video.file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Videoli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Audioli javob
        elif update.message.audio:
            context.user_data['answer_audio'] = update.message.audio.file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Audioli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
        
        # Hujjatli javob
        elif update.message.document:
            context.user_data['answer_document'] = update.message.document.file_id
            if update.message.caption:
                context.user_data['answer_caption'] = update.message.caption
            await update.message.reply_text(
                "✅ Hujjatli javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )

# ================= ASOSIY FUNKSIYA =================

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Yangi handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    
    # Avvalgi handlerlar
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Document filter ni alohida qo'shing
    document_filter = filters.Document.ALL if hasattr(filters, 'Document') else filters.DOCUMENT
    application.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VIDEO | filters.AUDIO | document_filter, 
        handle_message
    ))
    
    print("✅ Bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()