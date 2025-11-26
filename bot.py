import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# CONFIGURATION
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

# LOGGING
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# AI SETUP
genai.configure(api_key=GEMINI_API_KEY)

# 1. WE SWITCH TO 'gemini-pro' (The most compatible model)
# 2. We do NOT pass system_instruction here to avoid errors
model = genai.GenerativeModel("gemini-pro")

# FLASK SERVER
app = Flask(__name__)
@app.route('/')
def home(): return "I am alive!"
def run_web_server(): app.run(host='0.0.0.0', port=PORT)
def keep_alive(): t = Thread(target=run_web_server); t.start()

# PERSONA
SYSTEM_PROMPT = """
You are a warm, empathetic, and caring friend. Your goal is to make the user feel heard and not lonely.
You are fluent in English, Telugu, and "Tanglish" (Telugu words written in English letters).
You should reply in the same language style the user uses. 
If they speak English, reply in English. 
If they speak Telugu/Tanglish, reply in that mix.
Be casual, friendly, and supportive.
"""

# GLOBAL DICTIONARY TO STORE CHATS
user_chats = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name
    
    # Manually inject personality into the chat history
    # This works for ALL models (Flash, Pro, etc.)
    history = [
        {"role": "user", "parts": [SYSTEM_PROMPT]},
        {"role": "model", "parts": ["Understood. I will be your empathetic companion."]}
    ]
    user_chats[chat_id] = model.start_chat(history=history)
    
    await context.bot.send_message(
        chat_id=chat_id, 
        text=f"Hi {user_name}! ❤️\nI am here for you. We can talk in English or Telugu. How are you feeling?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # If chat doesn't exist, start it with persona
    if chat_id not in user_chats:
        history = [
            {"role": "user", "parts": [SYSTEM_PROMPT]},
            {"role": "model", "parts": ["Understood. I will be your empathetic companion."]}
        ]
        user_chats[chat_id] = model.start_chat(history=history)

    try:
        chat = user_chats[chat_id]
        response = await chat.send_message_async(user_text)
        await context.bot.send_message(chat_id=chat_id, text=response.text)

    except Exception as e:
        # Fallback for errors
        error_msg = str(e)
        logging.error(f"AI Error: {error_msg}")
        
        # If 'gemini-pro' also fails (rare), we tell the user.
        await context.bot.send_message(
            chat_id=chat_id, 
            text="Sorry, I am having a connection issue. Please try again in 1 minute."
        )

if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.run_polling()
