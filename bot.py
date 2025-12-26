import os, json, re, datetime, asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT = os.getenv("TARGET_CHAT")  # مثل: @configs_freeiran
SOURCES = [
    "https://t.me/s/V2RAYROZ",
    "https://t.me/s/V2ray_Alpha",
    "https://t.me/s/v2rayngvpn",
]
STATE_FILE = "last_messages.json"
MAX_LEN = 3800  # امن برای HTML
# ===========================================

HEADER = (
    "╔════════════════════╗\n"
    "🔥🔥 CONFIG DROP 🔥🔥\n"
    "╚════════════════════╝\n\n"
    "🛡 کانفیگ‌های امن و تست‌شده\n"
    "⚡ کپی با یک کلیک | بدون محدودیت\n\n"
)

def footer(ts):
    return (
        "\n\n╔════════════════════╗\n"
        f"⏱ {ts}\n"
        "📡 @configs_freeiran\n"
        "🌐 configfree.github.io\n"
        "╚════════════════════╝"
    )

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)

def fetch_channel(url):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    posts = soup.select("div.tgme_widget_message")
    messages = []
    for p in posts:
        mid = p.get("data-post")
        if not mid:
            continue
        text = p.get_text("\n", strip=True)
        messages.append((mid, text))
    return messages  # جدید → قدیم

def extract_configs(text):
    pattern = r'(vmess://[^\s]+|vless://[^\s]+|trojan://[^\s]+|ss://[^\s]+)'
    return re.findall(pattern, text)

def build_messages(configs):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    messages = []
    cur = HEADER + "<code>"
    for cfg in configs:
        piece = cfg + "\n"
        if len(cur) + len(piece) + len("</code>") + len(footer(now)) > MAX_LEN:
            cur = cur.rstrip("\n") + "</code>" + footer(now)
            messages.append(cur)
            cur = HEADER + "<code>" + piece
        else:
            cur += piece
    if cur.strip() != HEADER.strip() + "<code>":
        cur = cur.rstrip("\n") + "</code>" + footer(now)
        messages.append(cur)
    return messages

async def main():
    bot = Bot(BOT_TOKEN)
    state = load_state()
    all_new_configs = []

    for src in SOURCES:
        last = state.get(src)
        msgs = fetch_channel(src)
        for mid, text in msgs:
            if last and mid == last:
                break
            all_new_configs.extend(extract_configs(text))
        if msgs:
            state[src] = msgs[0][0]

    if not all_new_configs:
        print("📭 پیام جدیدی نیست")
        save_state(state)
        return

    messages = build_messages(all_new_configs)
    sent = 0
    for m in messages:
        await bot.send_message(
            chat_id=TARGET_CHAT,
            text=m,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        sent += 1
        await asyncio.sleep(1)  # امن برای تلگرام

    save_state(state)
    print(f"✅ پایان کار | پیام‌های ارسال‌شده: {sent}")

if __name__ == "__main__":
    asyncio.run(main())
