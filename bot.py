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

# --- DIAGNOSTIC BLOCK ---
# This will print what your key can actually see!
print("\n\n----------------- GOOGLE API SCANNER -----------------")
try:
    print(f"Scanning models for Key ending in: ...{GEMINI_API_KEY[-5:]}")
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ AVAILABLE: {m.name}")
            available_models.append(m.name)
    
    if not available_models:
        print("❌ NO MODELS FOUND! Your API Key project might be empty or restricted.")
except Exception as e:
    print(f"❌ SCANNER ERROR: {e}")
print("------------------------------------------------------\n\n")
# ------------------------

# We try the most standard model first
model = genai.GenerativeModel("gemini-1.5-flash")

# FLASK SERVER
app = Flask(__name__)
@app.route('/')
def home(): return "I am alive!"
def run_web_server(): app.run(host='0.0.0.0', port=PORT)
def keep_alive(): t = Thread(target=run_web_server); t.start()

# PERSONA
SYSTEM_PROMPT = "You are a warm, empathetic friend. Reply in English or Telugu/Tanglish based on user input."

# CHAT STORE
user_chats = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    history = [
        {"role": "user", "parts": [SYSTEM_PROMPT]},
        {"role": "model", "parts": ["Understood."]}
    ]
    user_chats[chat_id] = model.start_chat(history=history)
    await context.bot.send_message(chat_id=chat_id, text="Hi! I am testing my connection now. Send me a message.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    if chat_id not in user_chats:
        user_chats[chat_id] = model.start_chat(history=[])

    try:
        chat = user_chats[chat_id]
        response = await chat.send_message_async(user_text)
        await context.bot.send_message(chat_id=chat_id, text=response.text)

    except Exception as e:
        error_msg = str(e)
        logging.error(f"AI Error: {error_msg}")
        await context.bot.send_message(
            chat_id=chat_id, 
            text=f"⚠️ STILL FAILING: {error_msg}\n\nCheck Render Logs for the 'SCANNER' list."
        )

if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.run_polling()
