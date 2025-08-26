import os
import django
import requests
import sys
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
    try:
        response = requests.post(TELEGRAM_ID_API, json={"student_id": student_id}, timeout=5)
        if response.status_code == 200:
            return response.json().get("telegram_id")
        return None
    except:
        return None

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    print(f"Tugma bosildi: {data}")
    
    if data.startswith("assign_"):
        help_request_id = int(data.split("_")[1])
        teacher_name = f"{query.from_user.first_name}"
        
        print(f"O'qituvchi {teacher_name} {help_request_id} savoliga javob berishni boshladi")
        
        try:
            response = requests.post(BACKEND_ASSIGN_API, data={
                "help_request_id": help_request_id,
                "telegram_id": query.from_user.id
            }, timeout=5)
            result = response.json()
            print(f"Backend javobi: {result}")
        except Exception as e:
            await query.message.reply_text("❌ Serverga ulanishda xatolik")
            print(f"Server xatosi: {e}")
            return
        
        if result.get("success"):
            student_id = result.get("student_id")
            
            context.user_data['active_assignment'] = {
                'help_request_id': help_request_id,
                'student_id': student_id,
                'teacher_name': teacher_name
            }
            
            logs = await get_logs(help_request_id)
            url = f"https://iqmath.uz/dashboard/teacher/student-examples/{help_request_id}"
            
            # Javob bergan o'qituvchi uchun yangi tugmalar
            new_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("👨‍🏫 Siz javob berayapsiz", callback_data=f"assigned_{help_request_id}")],
                [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")],
                [InlineKeyboardButton("🔗 Savolga o'tish", url=url)]
            ])
            
            await update_message_log(help_request_id, query.message.chat_id, teacher_name)
            
            for log in logs:
                try:
                    if log.chat_id != query.message.chat_id:
                        # Boshqa o'qituvchilar uchun yangi tugmalar
                        other_teachers_markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton("👨‍🏫 Javob berilmoqda", callback_data=f"taken_{help_request_id}")],
                            [InlineKeyboardButton("🔗 Savolga o'tish", url=url)]
                        ])
                        
                        new_text = query.message.text.replace("📥 Yangi savol!", f"👨‍🏫 {teacher_name} javob beryapti")
                        
                        await context.bot.edit_message_text(
                            chat_id=log.chat_id,
                            message_id=log.message_id,
                            text=new_text,
                            reply_markup=other_teachers_markup,
                            parse_mode="HTML"
                        )
                    else:
                        new_text = query.message.text.replace("📥 Yangi savol!", "✅ Siz javob berayapsiz")
                        
                        await context.bot.edit_message_text(
                            chat_id=log.chat_id,
                            message_id=log.message_id,
                            text=new_text,
                            reply_markup=new_markup,
                            parse_mode="HTML"
                        )
                        
                        await query.message.reply_text(
                            "✅ Endi siz bu savolga javob berayapsiz.\n\n" +
                            "Talabaga javob yuborish uchun shu xabarga 'reply' qilib yozing yoki " +
                            "to'g'ridan-to'g'ri yozib, keyin 'Javobni yuborish' tugmasini bosing.",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                            ])
                        )
                        
                except Exception as e:
                    print(f"Xabar yangilashda xatolik: {e}")
            
        else:
            await query.message.reply_text("❌ Xatolik yuz berdi")
    
    elif data.startswith("send_"):
        help_request_id = int(data.split("_")[1])
        assignment = context.user_data.get('active_assignment', {})
        
        if assignment.get('help_request_id') != help_request_id:
            await query.message.reply_text("❌ Siz bu savolga javob berish huquqiga ega emassiz")
            return
        
        student_id = assignment.get('student_id')
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
            
            if 'answer_text' in context.user_data:
                del context.user_data['answer_text']
            if 'active_assignment' in context.user_data:
                del context.user_data['active_assignment']
            
        except:
            await query.message.reply_text("❌ Javob yuborishda xatolik yuz berdi")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message and 'active_assignment' in context.user_data:
        reply_text = update.message.reply_to_message.text or ""
        
        if "savolga javob berayapsiz" in reply_text or "Javobni yuborish" in reply_text:
            context.user_data['answer_text'] = update.message.text
            
            help_request_id = context.user_data['active_assignment']['help_request_id']
            
            await update.message.reply_text(
                "✅ Javobingiz qabul qilindi. «📤 Javobni yuborish» tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Javobni yuborish", callback_data=f"send_{help_request_id}")]
                ])
            )

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot ishga tushdi...")
    application.run_polling()

if __name__ == "__main__":
    main()