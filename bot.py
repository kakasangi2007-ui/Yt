import requests
import re
import os
import json
import asyncio
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

# ========== تنظیمات ==========
SOURCE_CHANNELS = [
    "https://t.me/s/V2RAYROZ",
    "https://t.me/s/V2ray_Alpha",
    "https://t.me/s/v2rayngvpn"
]

DESTINATION_CHANNEL = "@configs_freeiran"
BOT_TOKEN = os.environ.get("BOT_TOKEN")
LAST_MESSAGE_FILE = "last_messages.json"

# ====================================

def load_last_messages():
    if os.path.exists(LAST_MESSAGE_FILE):
        with open(LAST_MESSAGE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_last_messages(data):
    with open(LAST_MESSAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_messages(html_content):
    """پیام‌ها را با data-post استخراج می‌کند"""
    messages = []
    pattern = r'<div class="tgme_widget_message[^>]*data-post="([^"]+)"[^>]*>(.*?)<div class="tgme_widget_message_footer"'
    for post_id, message_html in re.findall(pattern, html_content, re.DOTALL):
        text_match = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', message_html, re.DOTALL)
        if text_match:
            raw_text = text_match.group(1)
            clean_text = re.sub(r'<[^>]+>', '', raw_text).strip()
            messages.append({"post_id": post_id, "clean_text": clean_text})
    return messages

def extract_configs(text):
    """همه کانفیگ‌ها را استخراج می‌کند"""
    configs = []
    for part in text.split():
        if part.lower().startswith(('vmess://','vless://','ss://','trojan://','hy2://')):
            configs.append(part.strip())
    return configs

async def send_message(bot, configs):
    """ارسال یک پیام با همه کانفیگ‌ها در یک بلاک"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code_block = "\n".join(configs)
    message_text = (
        "🌟 <b>کانفیگ جدید</b> 🌟\n\n"
        "🔗 <b>کانفیگ (کپی‌شدنی):</b>\n"
        f"<code>{code_block}</code>\n\n"
        "🟢 فیلترشکن\n"
        "🌐 <b>وبسایت برای کانفیگ‌های بیشتر:</b>\n"
        "https://configfree.github.io/Configfree/\n\n"
        "📌 <b>کانال ما:</b> @configs_freeiran\n"
        f"⏱ <b>زمان:</b> {now}\n"
        "============================"
    )
    if len(message_text) > 4000:
        print("⚠️ پیام خیلی طولانی، ارسال نشد")
        return
    try:
        await bot.send_message(chat_id=DESTINATION_CHANNEL, text=message_text,
                               parse_mode="HTML", disable_web_page_preview=True)
    except TelegramError as e:
        print(f"❌ خطا در ارسال پیام: {e}")

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN تنظیم نشده!")
        return

    bot = Bot(BOT_TOKEN)
    last_messages = load_last_messages()

    for url in SOURCE_CHANNELS:
        print(f"📡 بررسی کانال: {url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"❌ خطای HTTP {resp.status_code}")
                continue

            messages = extract_messages(resp.text)
            if not messages:
                print("📭 هیچ پیامی یافت نشد")
                continue

            # پیدا کردن پیام‌های جدید
            last_id = last_messages.get(url, "")
            new_messages = []
            for msg in messages:
                if msg["post_id"] == last_id:
                    break
                new_messages.append(msg)

            if not new_messages:
                print("📭 پیام جدیدی یافت نشد")
                continue

            # به‌روز کردن آخرین پیام
            last_messages[url] = new_messages[0]["post_id"]

            # ارسال هر پیام جدید جداگانه
            for msg in reversed(new_messages):
                configs = extract_configs(msg["clean_text"])
                if configs:
                    await send_message(bot, configs)
                    await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ خطا در بررسی کانال {url}: {e}")

    save_last_messages(last_messages)
    print("✅ پایان کار")

if __name__ == "__main__":
    asyncio.run(main())
