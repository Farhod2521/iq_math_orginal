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
    response = requests.post(API_URL, json={"telegram_id": telegram_id})
    
    if response.status_code == 200:
        data = response.json()
        context.user_data['user_info'] = data
        
        if data['role'] == 'teacher':
            teacher_menu(update, context)
        elif data['role'] == 'student':
            # Handle student role (you can implement this similarly)
            update.message.reply_text("Assalomu alaykum student! Xush kelibsiz!")
    else:
        update.message.reply_text("Siz ro'yxatdan o'tmagansiz. Iltimos, avval ro'yxatdan o'ting.")

def error_handler(update: Update, context: CallbackContext):
    """Log errors caused by updates."""
    print(f'Update {update} caused error {context.error}')

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
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