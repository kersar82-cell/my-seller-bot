import telebot
import requests
import os
import sqlite3
import threading
from flask import Flask

# --- রেন্ডার পোর্ট ফিক্স ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- কনফিগারেশন ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GIST_ID = "c334b01cace2fb30dd1ec31454dddf0c" # আপনার দেওয়া আইডি
ADMIN_ID = "7541488098"
NAGAD_NUMBER = "01XXXXXXXXX" # আপনার নগদ নাম্বার দিন

bot = telebot.TeleBot(BOT_TOKEN)

# --- ডাটাবেস সেটআপ ---
def init_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance REAL DEFAULT 0.0)')
    conn.commit()
    conn.close()

init_db()

# --- কি (Key) নামানোর আপডেট করা ফাংশন ---
def get_and_remove_key():
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        if response.status_code != 200:
            return "ERROR_AUTH" # টোকেন বা পারমিশন সমস্যা
        
        # আপনার ফাইলের নাম keys.txt কিনা চেক করা
        file_name = "keys.txt"
        if file_name not in data['files']:
            file_name = list(data['files'].keys())[0] # যদি নাম অন্য কিছু হয়
            
        content = data['files'][file_name]['content']
        keys_list = [k.strip() for k in content.split('\n') if k.strip()]

        if not keys_list:
            return "EMPTY"

        selected_key = keys_list[0]
        remaining_keys = "\n".join(keys_list[1:])
        
        # গিটহাবে আপডেট করা
        update_data = {"files": {file_name: {"content": remaining_keys}}}
        update_res = requests.patch(url, headers=headers, json=update_data)
        
        if update_res.status_code == 200:
            return selected_key
        else:
            return "UPDATE_FAILED"
    except Exception as e:
        print(f"Error: {e}")
        return "CONNECTION_ERROR"

# --- মেনু বাটন ---
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚀 Get 24h Access Key")
    markup.row("💰 Balance", "💳 Deposit")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()
    bot.reply_to(message, "👋 স্বাগতম! আপনার সেলার বট এখন তৈরি।", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def check_balance(message):
    user_id = str(message.from_user.id)
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    balance = res[0] if res else 0.0
    bot.reply_to(message, f"👤 আইডি: `{user_id}`\n💰 ব্যালেন্স: {balance} BDT")

@bot.message_handler(func=lambda m: m.text == "💳 Deposit")
def deposit(message):
    bot.reply_to(message, f"💳 **নগদ ডিপোজিট**\n\nনাম্বার: `{NAGAD_NUMBER}`\nটাকা পাঠিয়ে স্ক্রিনশট ও আইডি দিন: @Dinanhaji", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🚀 Get 24h Access Key")
def handle_key(message):
    user_id = str(message.from_user.id)
    # ব্যালেন্স চেক
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    balance = res[0] if res else 0.0

    if balance < 0: # দাম ২০ টাকা
        bot.reply_to(message, "❌ ব্যালেন্স নেই (দাম ২০ টাকা)। আগে ডিপোজিট করুন।")
        conn.close()
        return

    bot.reply_to(message, "⏳ চাবি সংগ্রহ করা হচ্ছে...")
    key_result = get_and_remove_key()

    if key_result in ["CONNECTION_ERROR", "ERROR_AUTH", "UPDATE_FAILED"]:
        bot.send_message(message.chat.id, "⚠️ কানেকশন এরর! GITHUB_TOKEN চেক করুন।")
    elif key_result == "EMPTY":
        bot.send_message(message.chat.id, "❌ স্টকে চাবি নেই!")
    else:
        cursor.execute('UPDATE users SET balance = balance - 20 WHERE user_id = ?', (user_id,))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ সফল!\n🔑 চাবি: `{key_result}`\n💰 নতুন ব্যালেন্স: {balance - 20} BDT")
    conn.close()

# --- এডমিন কমান্ড: /add আইডি টাকা ---
@bot.message_handler(commands=['add'])
def add_money(message):
    if str(message.from_user.id) != ADMIN_ID: return
    try:
        _, target, amount = message.text.split()
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (float(amount), target))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ {target} আইডিতে {amount} টাকা যোগ হয়েছে।")
    except:
        bot.reply_to(message, "❌ ফরম্যাট: `/add 12345 50`")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
    
