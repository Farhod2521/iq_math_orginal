from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def teacher_menu(update, context):
    user_data = context.user_data.get('user_info')
    full_name = user_data['data']['full_name']
    
    keyboard = [
        [InlineKeyboardButton("Menga kelgan murojaatlar", callback_data='teacher_applications')],
        [InlineKeyboardButton("Kelgan murojatlar bo'yicha statistika", callback_data='teacher_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"Assalomu alaykum {full_name}! Xush kelibsiz!",
        reply_markup=reply_markup
    )

def handle_teacher_callback(update, context):
    query = update.callback_query
    query.answer()
    
    if query.data == 'teacher_applications':
        # Handle applications
        query.edit_message_text(text="Sizga kelgan murojaatlar ro'yxati...")
    elif query.data == 'teacher_stats':
        # Handle statistics
        query.edit_message_text(text="Murojaatlar statistikasi...")