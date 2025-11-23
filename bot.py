import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from threading import Thread
from flask import Flask

# Flask app for health check
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

# Telegram bot code
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
        system_instruction = "You are a compassionate Telugu-English speaking AI friend. Reply in the same language mix as the user. Be empathetic and caring."
        history = get_history(user_id)
        payload = {
            "contents": [{"role": "user", "parts": [{"text": system_instruction}]}, *history],
            "generationConfig": {"temperature": 0.8, "maxOutputTokens": 200}
        }
        response = requests.post(GEMINI_API_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            reply = data['candidates'][0]['content']['parts'][0]['text']
            add_message(user_id, "model", reply)
            return reply
        return "Please try again."
    except:
        return "I am here to listen."

async def start(update, context):
    await update.message.reply_text("Hi! I am your Telugu AI friend!")

async def help_cmd(update, context):
    await update.message.reply_text("Chat with me in Telugu or English!")

async def clear_cmd(update, context):
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text("Chat cleared!")

async def handle_message(update, context):
    await update.message.chat.send_action("typing")
    reply = get_ai_response(update.message.text, update.effective_user.id)
    await update.message.reply_text(reply)

def run_bot():
    telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_cmd))
    telegram_app.add_handler(CommandHandler("clear", clear_cmd))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Telegram bot running...")
    telegram_app.run_polling()

if __name__ == '__main__':
    # Run Flask in a separate thread
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))).start()
    # Run Telegram bot
    run_bot()
