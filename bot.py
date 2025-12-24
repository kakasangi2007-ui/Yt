import os
import json
import asyncio
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.types import Message
from telegram import Bot

# ================= تنظیمات =================

SOURCE_CHANNELS = [
    "V2RAYROZ",
    "V2ray_Alpha",
    "v2rayngvpn"
]

DESTINATION_CHANNEL = "@configs_freeiran"

LAST_IDS_FILE = "last_ids.json"

BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

# ==========================================


def load_last_ids():
    if os.path.exists(LAST_IDS_FILE):
        with open(LAST_IDS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_last_ids(data):
    with open(LAST_IDS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def extract_configs(text: str):
    if not text:
        return []

    configs = []
    for part in text.split():
        if part.lower().startswith((
            "vmess://",
            "vless://",
            "ss://",
            "trojan://",
            "hy2://"
        )):
            configs.append(part.strip())
    return configs


async def main():
    last_ids = load_last_ids()

    client = TelegramClient("session", API_ID, API_HASH)
    bot = Bot(BOT_TOKEN)

    await client.start()

    for channel in SOURCE_CHANNELS:
        entity = await client.get_entity(channel)
        last_id = last_ids.get(channel, 0)

        messages = await client.get_messages(entity, limit=30)

        new_messages = []
        for msg in messages:
            if not isinstance(msg, Message):
                continue
            if msg.id <= last_id:
                break
            new_messages.append(msg)

        if not new_messages:
            continue

        # ذخیره آخرین پیام دیده‌شده
        last_ids[channel] = new_messages[0].id

        for msg in reversed(new_messages):
            configs = extract_configs(msg.text or "")
            if not configs:
                continue

            configs_block = "\n".join(configs)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            text = (
                "🌟 <b>کانفیگ جدید</b> 🌟\n\n"
                "🔗 <b>کانفیگ (کپی‌شدنی):</b>\n"
                f"<code>{configs_block}</code>\n\n"
                "🟢 فیلترشکن\n"
                "🌐 <b>وبسایت برای کانفیگ‌های بیشتر:</b>\n"
                "https://configfree.github.io/Configfree/\n\n"
                "📌 <b>کانال ما:</b> @configs_freeiran\n"
                f"⏱ <b>زمان:</b> {now}\n"
                "============================"
            )

            # محدودیت تلگرام
            if len(text) > 4000:
                continue

            await bot.send_message(
                chat_id=DESTINATION_CHANNEL,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )

            await asyncio.sleep(1)

    await client.disconnect()
    save_last_ids(last_ids)


if __name__ == "__main__":
    asyncio.run(main())
