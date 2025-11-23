import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

user_conversations = {}

def get_history(user_id):
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    return user_conversations[user_id]

def add_message(user_id, role, content):
    history = get_history(user_id)
    history.append({"role": role, "parts": [{"text": content}]})
    if len(history) > 10:
        user_conversations[user_id] = history[-10:]

def get_ai_response(message, user_id):
    try:
        add_message(user_id, "user", message)
        history = get_history(user_id)
        
        payload = {
            "contents": history,
            "generationConfig": {"temperature": 0.8, "maxOutputTokens": 200}
        }
        
        response = requests.post(GEMINI_API_URL, json=payload, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            reply = data['candidates'][0]['content']['parts'][0]['text']
            add_message(user_id, "model", reply)
            return reply
        return "Sorry, please try again."
    except Exception as e:
        logger.error(f"Error: {e}")
        return "I am here to listen."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Hi {user_name}! I am your Telugu-English AI friend. Talk to me!"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Chat with me in Telugu, English, or mix both!")

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text("Chat cleared!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    reply = get_ai_response(update.message.text, update.effective_user.id)
    await update.message.reply_text(reply)

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("clear", clear_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Telugu AI Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
