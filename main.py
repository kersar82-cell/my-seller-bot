import telebot
import requests
import os

# Render Environment Variables (এগুলো রেন্ডারে সেট করবেন)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GIST_ID = os.getenv("GIST_ID")
ADMIN_ID = "7541488098" # আপনার ফিক্সড আইডি

bot = telebot.TeleBot(BOT_TOKEN)

def get_and_remove_key():
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    try:
        # ১. গিটহাব থেকে সব চাবি নামিয়ে আনা
        response = requests.get(url, headers=headers).json()
        file_name = list(response['files'].keys())[0]
        content = response['files'][file_name]['content']
        keys_list = content.strip().split('\n')

        if not keys_list or (len(keys_list) == 1 and keys_list[0] == ""):
            return "❌ দুঃখিত! সব চাবি শেষ হয়ে গেছে। এডমিনকে জানান।"

        # ২. প্রথম চাবিটি নেওয়া এবং লিস্ট থেকে সরানো
        selected_key = keys_list[0]
        remaining_keys = "\n".join(keys_list[1:]) # প্রথমটি বাদে বাকিগুলো

        # ৩. গিটহাবে আপডেট করা (যাতে এই চাবি আর কেউ না পায়)
        data = {"files": {file_name: {"content": remaining_keys}}}
        requests.patch(url, headers=headers, json=data)
        
        return selected_key
    except Exception as e:
        return f"⚠️ এরর: {str(e)}"

@bot.message_handler(commands=['start'])
def start(message):
    # ইউজার বা এডমিন যেই আসুক, তাকে বাটন দেখাবে
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🚀 Get 24h Access Key")
    bot.reply_to(message, "স্বাগতম! নিচের বাটনে ক্লিক করে আপনার চাবি সংগ্রহ করুন।", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🚀 Get 24h Access Key")
def send_key(message):
    user_id = str(message.from_user.id)
    
    # আপনি চাইলে এখানে পেমেন্ট ভেরিফিকেশন যোগ করতে পারেন। 
    # আপাতত এটি সরাসরি চাবি দিয়ে দিচ্ছে।
    
    bot.reply_to(message, "⏳ চাবি জেনারেট হচ্ছে, দয়া করে অপেক্ষা করুন...")
    
    key = get_and_remove_key()
    
    if "DINAN-" in key or "TOKEN-" in key: # আপনার কি-এর ফরম্যাট অনুযায়ী
        bot.send_message(message.chat.id, f"✅ আপনার ওয়ান-টাইম চাবি:\n\n`{key}`\n\nএটি ২৪ ঘণ্টার জন্য কার্যকর।")
        # এডমিনকে নোটিফিকেশন দেওয়া
        bot.send_message(ADMIN_ID, f"📢 ইউজার {user_id} একটি চাবি সংগ্রহ করেছে।")
    else:
        bot.reply_to(message, key)

bot.polling()
