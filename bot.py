import requests
import os
import json
import time
from bs4 import BeautifulSoup
from telegram import Bot

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DEST_CHANNEL = "@configs_freeiran"
STATE_FILE = "last_messages.json"

SOURCE_CHANNELS = [
    "https://t.me/s/V2RAYROZ",
    "https://t.me/s/V2ray_Alpha",
    "https://t.me/s/v2rayngvpn"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def extract_messages(html):
    soup = BeautifulSoup(html, "html.parser")
    messages = []

    for msg in soup.select("div.tgme_widget_message"):
        post_id = msg.get("data-post")
        text_div = msg.select_one("div.tgme_widget_message_text")
        if not post_id or not text_div:
            continue

        text = text_div.get_text("\n", strip=True)
        messages.append({
            "id": post_id,
            "text": text
        })

    return messages

def extract_configs(text):
    lines = text.splitlines()
    configs = []

    for l in lines:
        l = l.strip()
        if l.startswith((
            "vmess://", "vless://", "trojan://",
            "ss://", "hy2://",
            "VMESS://", "VLESS://", "TROJAN://"
        )):
            configs.append(l)

    return configs

def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not set")
        return

    bot = Bot(token=BOT_TOKEN)
    state = load_state()
    total_sent = 0

    for url in SOURCE_CHANNELS:
        print(f"📡 بررسی کانال: {url}")

        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                print("⛔ HTTP error")
                continue

            messages = extract_messages(r.text)
            if not messages:
                print("📭 هیچ پیامی یافت نشد")
                continue

            last_id = state.get(url)
            new_messages = []

            for msg in messages:
                if msg["id"] == last_id:
                    break
                new_messages.append(msg)

            if not new_messages:
                print("📭 پیام جدیدی نیست")
                continue

            state[url] = new_messages[0]["id"]

            for msg in reversed(new_messages):
                configs = extract_configs(msg["text"])
                if not configs:
                    continue

                body = (
                    "🌟 <b>کانفیگ جدید</b> 🌟\n\n"
                    "🔗 <b>کانفیگ (کپی‌شدنی):</b>\n"
                    "<code>" + "\n".join(configs) + "</code>\n\n"
                    "🌐 https://configfree.github.io/Configfree/\n"
                    "📌 @configs_freeiran\n"
                    f"⏱ {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    "============================"
                )

                bot.send_message(
                    chat_id=DEST_CHANNEL,
                    text=body,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )

                total_sent += 1
                time.sleep(1)

        except Exception as e:
            print("⚠️ خطا ولی برنامه متوقف نشد:", e)

    save_state(state)
    print(f"✅ پایان کار | پیام‌های ارسال‌شده: {total_sent}")

if __name__ == "__main__":
    main()
