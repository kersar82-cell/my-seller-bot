import telebot
import requests
import os
import sqlite3
import threading
from flask import Flask

# --- ফেক সার্ভার (রেন্ডারের জন্য) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- সেটিংস ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GIST_ID = os.getenv("GIST_ID")
ADMIN_ID = "7541488098"
NAGAD_NUMBER = "017XXXXXXXX" # আপনার নগদ নাম্বার এখানে দিন

bot = telebot.TeleBot(BOT_TOKEN)

# --- ডাটাবেস সেটআপ (ইউজার ব্যালেন্সের জন্য) ---
def init_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance REAL DEFAULT 0.0)')
    conn.commit()
    conn.close()

init_db()

def get_balance(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (str(user_id),))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0.0

# --- মেইন মেনু বাটন ---
def main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚀 Get 24h Access Key")
    markup.row("💰 Balance", "💳 Deposit")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    # ডাটাবেসে ইউজার অ্যাড করা (যদি না থাকে)
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, "স্বাগতম! নিচের মেনু থেকে অপশন সিলেক্ট করুন।", reply_markup=main_keyboard())

# --- ব্যালেন্স চেক ---
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def check_bal(message):
    bal = get_balance(message.from_user.id)
    bot.reply_to(message, f"👤 আপনার বর্তমান ব্যালেন্স: {bal} BDT")

# --- ডিপোজিট সিস্টেম (নগদ) ---
@bot.message_handler(func=lambda m: m.text == "💳 Deposit")
def deposit_info(message):
    text = (f"💳 **নগদ ডিপোজিট**\n\n"
            f"নিচের নাম্বারে টাকা 'Send Money' করুন:\n"
            f"📱 নাম্বার: `{NAGAD_NUMBER}`\n\n"
            f"টাকা পাঠানোর পর ট্রানজেকশন আইডি (TrxID) এডমিনকে পাঠান: @Dinanhaji")
    bot.reply_to(message, text, parse_mode="Markdown")

# --- কি (Key) কেনা লজিক (টাকা কাটবে) ---
@bot.message_handler(func=lambda m: m.text == "🚀 Get 24h Access Key")
def buy_key(message):
    user_id = str(message.from_user.id)
    balance = get_balance(user_id)
    
    KEY_PRICE = 20.0 # প্রতি চাবির দাম ২০ টাকা (আপনি কমাতে/বাড়াতে পারেন)
    
    if balance < KEY_PRICE:
        bot.reply_to(message, f"❌ আপনার ব্যালেন্স পর্যাপ্ত নয়! চাবির দাম {KEY_PRICE} টাকা। আগে ডিপোজিট করুন।")
        return

    bot.reply_to(message, "⏳ ব্যালেন্স চেক হচ্ছে এবং চাবি তোলা হচ্ছে...")
    
    # চাবি তোলার ফাংশন (আগের Gist লজিক)
    key = get_and_remove_key() # এই ফাংশনটি আগের মতো থাকবে
    
    if "DINAN-" in key:
        # ব্যালেন্স কাটা
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (KEY_PRICE, user_id))
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, f"✅ সফল! আপনার ব্যালেন্স থেকে {KEY_PRICE} টাকা কাটা হয়েছে।\n\nআপনার চাবি: `{key}`")
    else:
        bot.reply_to(message, "⚠️ দুঃখিত! সিস্টেমে কোনো চাবি নেই। এডমিনকে জানান।")

# --- বাকি কোড (get_and_remove_key এবং infinity_polling) আগের মতোই থাকবে ---
@bot.message_handler(commands=['add'])
def add_money(message):
    if str(message.from_user.id) != ADMIN_ID: return
    
    try:
        # কমান্ড ফরম্যাট: /add [user_id] [amount]
        args = message.text.split()
        target_user = args[1]
        amount = float(args[2])
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, target_user))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ ইউজার {target_user} এর একাউন্টে {amount} টাকা যোগ করা হয়েছে।")
        bot.send_message(target_user, f"🎉 আপনার একাউন্টে {amount} টাকা ডিপোজিট সফল হয়েছে!")
    except:
        bot.reply_to(message, "❌ ফরম্যাট ভুল! লিখুন: `/add 123456 50`")

# --- মেইন রান লজিক ---
if __name__ == "__main__":
    # ১. আলাদা থ্রেডে ফ্ল্যাক্স সার্ভার চালু করা (যাতে রেন্ডার পোর্ট খুঁজে পায়)
    threading.Thread(target=run_flask).start()
    
    # ২. আপনার টেলিগ্রাম বট চালু করা
    print("Bot is starting...")
    bot.infinity_polling()
