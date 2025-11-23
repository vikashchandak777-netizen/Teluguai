import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from flask import Flask, request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Bot credentials
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PORT = int(os.getenv('PORT', 10000))
WEBHOOK_URL = os.getenv('RENDER_EXTERNAL_URL', '')

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

user_conversations = {}
telegram_app = None

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
        system_instruction = "You are a compassionate Telugu-English AI friend. Reply in same language as user."
        history = get_history(user_id)
        
        payload = {
            "contents": [{"role": "user", "parts": [{"text": system_instruction}]}, *history],
            "generationConfig": {"temperature": 0.8, "maxOutputTokens": 200}
        }
        
        response = requests.post(GEMINI_API_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            reply = data['candidates'][0]['content']['parts'][0]['text']
            add_message(user_id, "model", reply)
            return reply
        return "Please try again."
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "I am here to listen."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! I am your Telugu-English AI friend!")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Chat with me in Telugu or English!")

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text("Chat cleared!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    reply = get_ai_response(update.message.text, update.effective_user.id)
    await update.message.reply_text(reply)

@app.route('/')
def home():
    return "Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
async def webhook():
    """Handle incoming updates from Telegram"""
    try:
        json_data = request.get_json()
        update = Update.de_json(json_data, telegram_app.bot)
        await telegram_app.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

def setup_application():
    """Setup telegram application"""
    global telegram_app
    
    telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_cmd))
    telegram_app.add_handler(CommandHandler("clear", clear_cmd))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Set webhook
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}"
        logger.info(f"Setting webhook to: {webhook_url}")
        telegram_app.bot.set_webhook(url=webhook_url)
    
    return telegram_app

if __name__ == '__main__':
    setup_application()
    logger.info(f"Starting Flask server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
