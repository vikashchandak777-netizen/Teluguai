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

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# AI SETUP
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash") # Trying standard model again

# FLASK SERVER
app = Flask(__name__)
@app.route('/')
def home(): return "I am alive!"
def run_web_server(): app.run(host='0.0.0.0', port=PORT)
def keep_alive(): t = Thread(target=run_web_server); t.start()

# TELEGRAM LOGIC
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hi! I am online. Send me a message.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # We send the raw message without history first to test the connection
        response = model.generate_content(user_text)
        await context.bot.send_message(chat_id=chat_id, text=response.text)

    except Exception as e:
        # THIS IS THE IMPORTANT PART: 
        # We send the ACTUAL error to Telegram so we can read it.
        error_message = str(e)
        print(f"ERROR: {error_message}") # Print to logs
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ ERROR FROM GOOGLE:\n\n{error_message}")

if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.run_polling()
