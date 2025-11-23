import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from threading import Thread
from flask import Flask
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Telegram Bot is running!", 200

@flask_app.route('/health')
def health():
    return "OK", 200

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PORT = int(os.getenv('PORT', 10000))

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
        system_instruction = "You are a compassionate Telugu-English speaking AI friend. Reply in the same language as user. Be empathetic and caring."
        history = get_history(user_id)
        
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": system_instruction}]},
                *history
            ],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 200
            }
        }
        
        response = requests.post(GEMINI_API_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            reply = data['candidates'][0]['content']['parts'][0]['text']
            add_message(user_id, "model", reply)
            return reply
        else:
            return "Sorry, please try again in a moment."
    except Exception as e:
        logger.error(f"Error in AI response: {e}")
        return "I am here to listen. Tell me more."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Hi {user_name}! I am your Telugu-English AI friend. Talk to me!"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Chat with me in Telugu, English, or mix both!"
    )

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_conversations[user_id] = []
    await update.message.reply_text("Chat history cleared!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    await update.message.chat.send_action("typing")
    reply = get_ai_response(text, user_id)
    await update.message.reply_text(reply)

def run_bot():
    """Run the Telegram bot"""
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_cmd))
        application.add_handler(CommandHandler("clear", clear_cmd))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("Starting Telegram bot...")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Error running bot: {e}")

def run_flask():
    """Run Flask web server for Render"""
    flask_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

if __name__ == '__main__':
    
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Flask server started on port {PORT}")
    
    run_bot()
