import logging
import requests
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,

    MessageHandler,
)
from config import API_URL, BOT_TOKEN
from teacher import teacher_menu, handle_teacher_callback

# Log konfiguratsiyasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext):
    telegram_id = update.effective_user.id
    logger.info(f"Foydalanuvchi {telegram_id} /start buyrug'ini yubordi")
    
    try:
        response = requests.post(API_URL, json={"telegram_id": telegram_id}, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            context.user_data['user_info'] = data
            
            if data['role'] == 'teacher':
                teacher_menu(update, context)
            elif data['role'] == 'student':
                update.message.reply_text("Assalomu alaykum student! Xush kelibsiz!")
        else:
            update.message.reply_text("Siz ro'yxatdan o'tmagansiz. Iltimos, avval ro'yxatdan o'ting.")
    except requests.exceptions.RequestException as e:
        logger.error(f"API so'rovida xatolik: {e}")
        update.message.reply_text("Tizimda vaqtinchalik xatolik yuz berdi. Iltimos, keyinroq urunib ko'ring.")

def error_handler(update: Update, context: CallbackContext):
    """Xatoliklarni log qilish"""
    logger.error(f'Xatolik: {context.error}', exc_info=context.error)

def main():
    # Botni ishga tushirish
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handlerlar
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CallbackQueryHandler(handle_teacher_callback))
    
    # Xatolik handleri
    dp.add_error_handler(error_handler)

    logger.info("Bot ishga tushdi...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()