import os
import django
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from asgiref.sync import sync_to_async

import sys
sys.path.append('/home/user/backend/iq_math_orginal')

# Django sozlamasi
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

try:
    django.setup()
    print("✅ Django muvaffaqiyatli ishga tushdi")
except Exception as e:
    print(f"❌ Django ishga tushirishda xatolik: {e}")
    sys.exit(1)

from django_app.app_student.models import HelpRequestMessageLog

BOT_TOKEN = "7826335243:AAGXTZvtzJ8e8g35Hrx_Swy7mwmRPd3T7Po"
BACKEND_ASSIGN_API = "https://api.iqmath.uz/api/v1/func_student/student/telegram/assign-teacher/"
TELEGRAM_ID_API = "https://api.iqmath.uz/api/v1/func_student/student/student_id/telegram_id/"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
    except HelpRequestMessageLog.DoesNotExist:
        logger.error(f"Log topilmadi: help_request_id={help_request_id}, chat_id={chat_id}")
        return False
    except Exception as e:
        logger.error(f"Log yangilashda xatolik: {e}")
        return False

async def get_student_telegram_id(student_id):
    try:
        response = requests.post(TELEGRAM_ID_API, json={"student_id": student_id})
        if response.status_code == 200:
            result = response.json()
            return result.get("telegram_id")
        else:
            logger.error(f"Telegram ID API javob kodi: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Telegram ID olishda xatolik: {e}")
        return None

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Callback data: {data}")
    
    if data.startswith("assign_"):
        help_request_id = int(data.split("_")[1])
        telegram_id = query.from_user.id
        teacher_name = f"{query.from_user.first_name} {query.from_user.last_name or ''}".strip()
        
        logger.info(f"O'qituvchi {teacher_name} ({telegram_id}) {help_request_id} savoliga javob berishni boshladi")
        
        try:
            response = requests.post(BACKEND_ASSIGN_API, data={
                "help_request_id": help_request_id,
                "telegram_id": telegram_id
            })
            result = response.json()
            logger.info(f"Backend API javobi: {result}")
        except Exception as e:
            error_msg = f"❌ Server bilan bog'lanib bo'lmadi: {e}"
            await query.message.reply_text(error_msg)
            logger.error(error_msg)
            return
        
        if result.get("success"):
            student_id = result.get("student_id", "noma'lum")
            
            # O'qituvchi ma'lumotlarini contextda saqlaymiz
            context.user_data['active_assignment'] = {
                'help_request_id': help_request_id,
                'student_id': student_id,
                'teacher_name': teacher_name
            }
            
            logs = await get_logs(help_request_id)
            url = f"https://iqmath.uz/dashboard/teacher/student-examples/{help_request_id}?student_name=Oquvchi"
            
            # Javob bergan o'qituvchi uchun yangi tugmalar
            new_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("👨‍🏫 Siz javob berayapsiz", callback_data=f"assigned_{help_request_id}")],
                [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")],
                [InlineKeyboardButton("🔗 Savolga o'tish", url=url)]
            ])
            
            # Loglarni yangilash
            await update_message_log(help_request_id, query.message.chat_id, teacher_name)
            
            for log in logs:
                try:
                    # Boshqa o'qituvchilarga xabar yuboramiz
                    if log.chat_id != query.message.chat_id:
                        # Boshqa o'qituvchilar uchun yangi tugmalar
                        other_teachers_markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton("👨‍🏫 Javob berilmoqda", callback_data=f"taken_{help_request_id}")],
                            [InlineKeyboardButton("🔗 Savolga o'tish", url=url)]
                        ])
                        
                        # Matnni yangilash
                        original_text = query.message.text
                        new_text = original_text.replace("📥 Yangi savol!", f"👨‍🏫 {teacher_name} javob beryapti")
                        
                        await context.bot.edit_message_text(
                            chat_id=log.chat_id,
                            message_id=log.message_id,
                            text=new_text,
                            reply_markup=other_teachers_markup,
                            parse_mode="HTML"
                        )
                    else:
                        # Javob bergan o'qituvchi uchun matnni yangilash
                        original_text = query.message.text
                        new_text = original_text.replace("📥 Yangi savol!", "✅ Siz javob berayapsiz")
                        
                        await context.bot.edit_message_text(
                            chat_id=log.chat_id,
                            message_id=log.message_id,
                            text=new_text,
                            reply_markup=new_markup,
                            parse_mode="HTML"
                        )
                        
                        # Qo'shimcha yo'riqnoma xabari
                        instruction_text = (
                            f"✅ Endi siz bu savolga javob berayapsiz.\n\n"
                            f"Talabaga javob yuborish uchun:\n"
                            f"1. Quyidagi '📤 Javobni yuborish' tugmasini bosing\n"
                            f"2. Yoki shu xabarga 'reply' qilib javob yozing\n"
                            f"3. Keyin '📤 Javobni yuborish' tugmasini bosing"
                        )
                        
                        await query.message.reply_text(
                            instruction_text,
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                            ])
                        )
                        
                except Exception as e:
                    logger.error(f"Xabar yangilashda xatolik (chat_id: {log.chat_id}): {e}")
            
            await query.message.reply_text(
                f"💡 Eslatma: Talabaga javob yozish uchun 'reply' funksiyasidan foydalanishingiz mumkin. "
                f"Bu siz bir vaqtda bir nechta savollarga javob yozayotganingizda qaysi javob qaysi savolga ekanligini bilishingizga yordam beradi."
            )
            
        else:
            error_msg = result.get("message", "❌ Xatolik yuz berdi")
            await query.message.reply_text(error_msg)
            logger.error(f"Backend API xatosi: {error_msg}")
    
    elif data.startswith("send_"):
        help_request_id = int(data.split("_")[1])
        assignment = context.user_data.get('active_assignment', {})
        
        if assignment.get('help_request_id') != help_request_id:
            await query.message.reply_text("❌ Siz bu savolga javob berish huquqiga ega emassiz.")
            return
        
        student_id = assignment.get('student_id')
        student_telegram_id = await get_student_telegram_id(student_id)
        
        if not student_telegram_id:
            await query.message.reply_text("❌ Talabaning Telegram ID sini topib bo'lmadi.")
            return
        
        # Foydalanuvchi javobini olish
        if 'answer_text' not in context.user_data:
            await query.message.reply_text(
                "❌ Avval javob matnini yuboring. Quyidagi usullardan birini tanlang:\n\n"
                "1. Shu xabarga 'reply' qilib javob yozing\n"
                "2. To'g'ridan-to'g'ri javob yozib, keyin '📤 Javobni yuborish' tugmasini bosing",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )
            return
        
        answer_text = context.user_data['answer_text']
        teacher_name = assignment.get('teacher_name', 'O\'qituvchi')
        
        # Talabaga javobni yuborish
        try:
            await context.bot.send_message(
                chat_id=student_telegram_id,
                text=f"👨‍🏫 {teacher_name}dan javob:\n\n{answer_text}"
            )
            await query.message.reply_text("✅ Javobingiz talabaga yuborildi.")
            
            # Contextni tozalash
            if 'answer_text' in context.user_data:
                del context.user_data['answer_text']
            if 'active_assignment' in context.user_data:
                del context.user_data['active_assignment']
            
            # Barcha loglarni yangilash - javob yuborilganligi haqida
            logs = await get_logs(help_request_id)
            for log in logs:
                try:
                    await context.bot.edit_message_text(
                        chat_id=log.chat_id,
                        message_id=log.message_id,
                        text=query.message.text.replace("✅ Siz javob berayapsiz", "✅ Javob yuborildi")
                                                  .replace("👨‍🏫 Javob berilmoqda", "✅ Javob yuborildi")
                                                  .replace("📥 Yangi savol!", "✅ Javob yuborildi"),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Yakuniy xabar yangilashda xatolik: {e}")
            
        except Exception as e:
            error_msg = f"❌ Javob yuborishda xatolik: {e}"
            await query.message.reply_text(error_msg)
            logger.error(error_msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Agar reply qilingan bo'lsa
    if update.message.reply_to_message:
        reply_text = update.message.reply_to_message.text or ""
        
        # Agar reply qilingan xabar savol haqida bo'lsa
        if ("savol" in reply_text.lower() or "javob" in reply_text.lower()) and "yangi savol" not in reply_text.lower():
            # Contextda faol assignment bormi tekshiramiz
            active_assignment = context.user_data.get('active_assignment', {})
            if active_assignment:
                context.user_data['answer_text'] = update.message.text
                help_request_id = active_assignment['help_request_id']
                
                await update.message.reply_text(
                    "✅ Javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                    ])
                )
            else:
                await update.message.reply_text(
                    "ℹ️ Avval savolga javob berishni boshlashingiz kerak. "
                    "Savol xabaridagi '✅ Javob berish' tugmasini bosing."
                )

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlerlarni qo'shamiz
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Bot ishga tushdi... kutyapti.")
    application.run_polling()

if __name__ == "__main__":
    main()