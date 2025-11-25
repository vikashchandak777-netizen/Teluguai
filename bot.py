import os
import logging
import asyncio
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

# ---------------------------------------------------------
# LOGGING SETUP
# ---------------------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ---------------------------------------------------------
# AI MODEL SETUP (Universal Fix)
# ---------------------------------------------------------
genai.configure(api_key=GEMINI_API_KEY)

# We use the older, more reliable "gemini-pro" model to avoid 404 errors.
# We also do NOT pass system_instruction to the constructor to avoid compatibility issues.
model = genai.GenerativeModel("gemini-pro")

# We define the personality here, and we will "inject" it into the chat history manually.
SYSTEM_PROMPT = """
You are a warm, empathetic, and caring friend. Your goal is to make the user feel heard and not lonely.
You are fluent in English, Telugu, and "Tanglish" (Telugu words written in English letters).
You should reply in the same language style the user uses. 
If they speak English, reply in English. 
If they speak Telugu/Tanglish, reply in that mix.
Be casual, friendly, and supportive. Avoid sounding like a robot or an assistant. Use emojis occasionally.
"""

# Store chat history in memory
user_chats = {}

# ---------------------------------------------------------
# FLASK KEEP-ALIVE SERVER
# ---------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "I am alive! The bot is running."

def run_web_server():
    app.run(host='0.0.0.0', port=PORT)

def keep_alive():
    t = Thread(target=run_web_server)
    t.start()

# ---------------------------------------------------------
# TELEGRAM BOT LOGIC
# ---------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message and initializes the chat with the persona."""
    user_first_name = update.effective_user.first_name
    chat_id = update.effective_chat.id
    
    welcome_text = (
        f"Hi {user_first_name}! ❤️\n\n"
        "I'm here for you. We can talk about anything. "
        "I understand English and Telugu (even if you type it in English letters).\n\n"
        "Ela unnav? Emi jarigindi?"
    )

    # MAGIC FIX: We inject the personality into the history manually.
    # This works on ALL model versions, even if they don't support system_instructions.
    initial_history = [
        {"role": "user", "parts": [SYSTEM_PROMPT]},
        {"role": "model", "parts": ["Understood. I will be your empathetic companion."]}
    ]
    
    user_chats[chat_id] = model.start_chat(history=initial_history)
    await context.bot.send_message(chat_id=chat_id, text=welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages."""
    chat_id = update.effective_chat.id
    user_text = update.message.text

    # If chat session doesn't exist, create it with the persona injection
    if chat_id not in user_chats:
        initial_history = [
            {"role": "user", "parts": [SYSTEM_PROMPT]},
            {"role": "model", "parts": ["Understood. I will be your empathetic companion."]}
        ]
        user_chats[chat_id] = model.start_chat(history=initial_history)

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        chat_session = user_chats[chat_id]
        response = await chat_session.send_message_async(user_text)
        ai_reply = response.text
        await context.bot.send_message(chat_id=chat_id, text=ai_reply)

    except Exception as e:
        logging.error(f"Error: {e}")
        # If even gemini-pro fails, it usually means the API Key is invalid.
        await context.bot.send_message(
            chat_id=chat_id, 
            text="I'm having trouble connecting to my brain. Please check the API Key."
        )

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == '__main__':
    keep_alive()
    
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        print("Error: TELEGRAM_TOKEN and GEMINI_API_KEY must be set.")
        exit(1)

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    start_handler = CommandHandler('start', start)
    msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)

    application.add_handler(start_handler)
    application.add_handler(msg_handler)

    print(f"Bot is running on port {PORT}...")
    application.run_polling()
