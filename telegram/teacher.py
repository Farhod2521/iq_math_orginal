from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

async def teacher_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data.get('user_info')
    full_name = user_data['data']['full_name']
    
    keyboard = [
        [
            InlineKeyboardButton("📬 Menga kelgan murojaatlar", callback_data='teacher_applications')
        ],
        [
            InlineKeyboardButton("📊 Murojaatlar statistikasi", callback_data='teacher_stats')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Assalomu alaykum {full_name}!\nXush kelibsiz! Quyidagi menyudan foydalaning:",
        reply_markup=reply_markup
    )

async def handle_teacher_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'teacher_applications':
        await query.edit_message_text(text="📬 Sizga kelgan murojaatlar ro'yxati...")
    elif query.data == 'teacher_stats':
        await query.edit_message_text(text="📊 Murojaatlar statistikasi...")
