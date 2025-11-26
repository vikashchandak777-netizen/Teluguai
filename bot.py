import os
import logging
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
# AI MODEL SETUP
# ---------------------------------------------------------
genai.configure(api_key=GEMINI_API_KEY)

# We are using "gemini-2.5-flash" because it was GREEN in your scanner list.
model = genai.GenerativeModel("gemini-2.5-flash")

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
# BOT PERSONALITY & LOGIC
# ---------------------------------------------------------
SYSTEM_PROMPT = """
You are a warm, empathetic, and caring friend. Your goal is to make the user feel heard and not lonely.
You are fluent in English, Telugu, and "Tanglish" (Telugu words written in English letters).
You should reply in the same language style the user uses. 
If they speak English, reply in English. 
If they speak Telugu/Tanglish, reply in that mix.
Be casual, friendly, and supportive. Avoid sounding like a robot.
"""

# Store chat history in memory
user_chats = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name
    
    # Initialize chat with personality injection
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

    # Start chat if not exists
    if chat_id not in user_chats:
        history = [
            {"role": "user", "parts": [SYSTEM_PROMPT]},
            {"role": "model", "parts": ["Understood. I will be your empathetic companion."]}
        ]
        user_chats[chat_id] = model.start_chat(history=history)

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        chat = user_chats[chat_id]
        response = await chat.send_message_async(user_text)
        await context.bot.send_message(chat_id=chat_id, text=response.text)

    except Exception as e:
        # Graceful error handling
        logging.error(f"AI Error: {e}")
        await context.bot.send_message(
            chat_id=chat_id, 
            text="I'm listening, but my connection flickered. Can you tell me that again?"
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and handle it gracefully."""
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == '__main__':
    keep_alive()
    
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        print("Error: TELEGRAM_TOKEN and GEMINI_API_KEY must be set.")
        exit(1)

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # This fixes the "No error handlers registered" warning
    application.add_error_handler(error_handler)

    print(f"Bot is running on port {PORT}...")
    application.run_polling()
