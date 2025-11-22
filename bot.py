import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# Read tokens securely from environment variables
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
        
        system_instruction = "You are a compassionate Telugu-English speaking AI friend. Reply in the same language mix as the user. If user speaks Telugu, reply in Telugu. If user mixes Telugu and English, reply in the same mix. Be empathetic, kind, and friendly."

        history = get_history(user_id)
        
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": system_instruction}]},
                *history
            ],
            "generationConfig": {"temperature": 0.8, "maxOutputTokens": 200}
        }
        
        response = requests.post(GEMINI_API_URL, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            reply = data['candidates'][0]['content']['parts'][0]['text']
            add_message(user_id, "model", reply)
            return reply
        elif response.status_code == 429:
            return "Please wait a moment and try again."
        else:
            return "Sorry, something went wrong."
    except Exception:
        return "I am here to listen. Tell me more."

async def start(update, context):
    user_name = update.effective_user.first_name
    welcome_text = f"Hi {user_name}! I am your Telugu AI friend. Talk to me in Telugu, English, or both!"
    await update.message.reply_text(welcome_text)

async def help_cmd(update, context):
    help_text = "Chat freely with me in Telugu and English. Commands: /start /help /clear"
    await update.message.reply_text(help_text)

async def clear_cmd(update, context):
    user_id = update.effective_user.id
    user_conversations[user_id] = []
    await update.message.reply_text("Chat history cleared. Let's start fresh!")

async def handle_message(update, context):
    user_id = update.effective_user.id
    text = update.message.text
    await update.message.chat.send_action("typing")
    reply = get_ai_response(text, user_id)
    await update.message.reply_text(reply)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot running...")
    app.run_polling()

if __name__ == '__main__':
    main()
