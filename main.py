import telebot
import requests
import os
import threading
from flask import Flask

# --- ফেক ওয়েব সার্ভার সেটআপ (রেন্ডারের পোর্ট এরর ফিক্স করার জন্য) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running Live!"

def run_flask():
    # রেন্ডার অটোমেটিক একটি পোর্ট দেয়, সেটি ব্যবহার করা হচ্ছে
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- আপনার আসল বটের কোড ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GIST_ID = os.getenv("GIST_ID")
ADMIN_ID = "7541488098"

bot = telebot.TeleBot(BOT_TOKEN)

def get_and_remove_key():
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        response = requests.get(url, headers=headers).json()
        file_name = list(response['files'].keys())[0]
        content = response['files'][file_name]['content']
        keys_list = content.strip().split('\n')

        if not keys_list or (len(keys_list) == 1 and keys_list[0] == ""):
            return "❌ সব চাবি শেষ!"

        selected_key = keys_list[0]
        remaining_keys = "\n".join(keys_list[1:])
        data = {"files": {file_name: {"content": remaining_keys}}}
        requests.patch(url, headers=headers, json=data)
        return selected_key
    except:
        return "⚠️ কানেকশন এরর!"

@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🚀 Get 24h Access Key")
    bot.reply_to(message, "স্বাগতম! চাবি নিতে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 Get 24h Access Key")
def send_key(message):
    bot.reply_to(message, "⏳ চাবি জেনারেট হচ্ছে...")
    key = get_and_remove_key()
    bot.send_message(message.chat.id, f"✅ আপনার চাবি:\n\n`{key}`")

# --- মেইন রান লজিক ---
if __name__ == "__main__":
    # ১. আলাদা থ্রেডে ফ্ল্যাক্স সার্ভার চালু করা (যাতে রেন্ডার পোর্ট খুঁজে পায়)
    threading.Thread(target=run_flask).start()
    
    # ২. আপনার টেলিগ্রাম বট চালু করা
    print("Bot is starting...")
    bot.infinity_polling()
