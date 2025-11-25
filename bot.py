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
# AI MODEL SETUP (GEMINI)
# ---------------------------------------------------------
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
You are a warm, empathetic, and caring friend. Your goal is to make the user feel heard and not lonely.
You are fluent in English, Telugu, and "Tanglish" (Telugu words written in English letters).
You should reply in the same language style the user uses. 
If they speak English, reply in English. 
If they speak Telugu/Tanglish, reply in that mix.
Be casual, friendly, and supportive. Avoid sounding like a robot or an assistant. Use emojis occasionally.
"""

# UPDATE: We are using "gemini-1.5-flash-latest" which is more stable than the short name.
# If this still fails, you can try "gemini-pro"
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    system_instruction=SYSTEM_PROMPT
)

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
    """Sends a welcome message when the command /start is issued."""
    user_first_name = update.effective_user.first_name
    welcome_text = (
        f"Hi {user_first_name}! ❤️\n\n"
        "I'm here for you. We can talk about anything. "
        "I understand English and Telugu (even if you type it in English letters).\n\n"
        "Ela unnav? Emi jarigindi?"
    )
    user_chats[update.effective_chat.id] = model.start_chat(history=[])
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages and sends them to Gemini."""
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if chat_id not in user_chats:
        user_chats[chat_id] = model.start_chat(history=[])

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        chat_session = user_chats[chat_id]
        response = await chat_session.send_message_async(user_text)
        ai_reply = response.text
        await context.bot.send_message(chat_id=chat_id, text=ai_reply)

    except Exception as e:
        # If the specific model fails, we log it and try to tell the user
        logging.error(f"Error generating response: {e}")
        # Fallback message
        await context.bot.send_message(
            chat_id=chat_id, 
            text="Sorry, I'm having a little trouble thinking right now. Can you try saying that again?"
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
