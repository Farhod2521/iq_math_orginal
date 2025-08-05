import requests
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
    MessageHandler,
    filters
)
from config import API_URL, BOT_TOKEN
from teacher import teacher_menu, handle_teacher_callback

def start(update: Update, context: CallbackContext):
    telegram_id = update.effective_user.id
    
    # Check user role via API
    try:
        response = requests.post(API_URL, json={"telegram_id": telegram_id})
        
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
        update.message.reply_text("Xatolik yuz berdi. Iltimos, keyinroq urunib ko'ring.")
        print(f"API request failed: {e}")

def error_handler(update: Update, context: CallbackContext):
    """Log errors caused by updates."""
    print(f'Update {update} caused error {context.error}')

def main():
    # Yangi versiyada use_context kerak emas
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    # Add handlers
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CallbackQueryHandler(handle_teacher_callback))
    dp.add_error_handler(error_handler)

    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()