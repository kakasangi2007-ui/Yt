import requests
import re
import os
import json
import asyncio
from telegram import Bot
from telegram.error import TelegramError

# ========== تنظیمات ==========
SOURCE_CHANNELS = [
    {"url": "https://t.me/s/V2RAYROZ", "last_id": ""},
    {"url": "https://t.me/s/V2ray_Alpha", "last_id": ""}, 
    {"url": "https://t.me/s/v2rayngvpn", "last_id": ""}
]
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DESTINATION_CHANNEL = "@configs_freeiran"
LAST_MESSAGE_FILE = "last_messages.json"

def load_last_messages():
    if os.path.exists(LAST_MESSAGE_FILE):
        try:
            with open(LAST_MESSAGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for channel in SOURCE_CHANNELS:
                    channel_name = channel["url"].split('/')[-1]
                    if channel_name in data:
                        channel["last_id"] = data[channel_name]
                print("📂 تاریخچه پیام‌ها بارگیری شد")
        except:
            pass
    return SOURCE_CHANNELS

def save_last_messages(channels):
    data = {}
    for channel in channels:
        channel_name = channel["url"].split('/')[-1]
        data[channel_name] = channel["last_id"]
    
    try:
        with open(LAST_MESSAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def extract_message_id_and_configs(html_content):
    messages_data = []
    
    message_pattern = r'data-post="([^"]+)"[^>]*>(.*?)</div>\s*</div>\s*</div>'
    messages = re.findall(message_pattern, html_content, re.DOTALL)
    
    for post_id, message_html in messages:
        config_patterns = [
            r'(vmess://[a-zA-Z0-9+/=%:.-]+)',
            r'(vless://[a-zA-Z0-9+/=%:.-]+)',
            r'(ss://[a-zA-Z0-9+/=%:.-]+)',
            r'(trojan://[a-zA-Z0-9+/=%:.-]+)',
            r'(hy2://[a-zA-Z0-9+/=%:.-]+)'
        ]
        
        configs_in_message = []
        for pattern in config_patterns:
            found = re.findall(pattern, message_html)
            configs_in_message.extend(found)
        
        if configs_in_message:
            messages_data.append({
                "post_id": post_id,
                "configs": configs_in_message
            })
    
    return messages_data

async def send_configs_from_new_messages(bot, messages_data):
    if not messages_data:
        return 0
    
    total_configs_sent = 0
    
    for message in messages_data:
        if not message["configs"]:
            continue
        
        message_text = "🌟 *کانفیگ جدید* 🌟\n\n"
        message_text += "🔗 کانفیگ (کپی‌شدنی):\n\n"
        
        for config in message["configs"]:
            message_text += f"`{config}`\n\n"
        
        message_text += "🌐 وبسایت برای کانفیگ‌های بیشتر:\n"
        message_text += "https://configfree.github.io/Configfree/\n\n"
        message_text += "📌 کانال ما: @configs_freeiran\n"
        message_text += "============================"
        
        try:
            await bot.send_message(
                chat_id=DESTINATION_CHANNEL,
                text=message_text,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            total_configs_sent += len(message["configs"])
            print(f"  ✅ {len(message['configs'])} کانفیگ ارسال شد")
            await asyncio.sleep(1)
        except TelegramError as e:
            print(f"  ❌ خطا در ارسال: {e}")
    
    return total_configs_sent

async def check_channel_for_new_messages(bot, channel):
    channel_name = channel["url"].split('/')[-1]
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        response = requests.get(channel["url"], headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"  ❌ خطای HTTP {response.status_code} برای {channel_name}")
            return 0, channel
        
        all_messages = extract_message_id_and_configs(response.text)
        
        if not all_messages:
            print(f"  📭 هیچ پیامی با کانفیگ یافت نشد")
            return 0, channel
        
        new_messages = []
        if channel["last_id"]:
            for msg in all_messages:
                if msg["post_id"] == channel["last_id"]:
                    break
                new_messages.append(msg)
        else:
            new_messages = [all_messages[0]] if all_messages else []
        
        if new_messages:
            channel["last_id"] = new_messages[0]["post_id"]
            print(f"  📨 {len(new_messages)} پیام جدید یافت شد")
            
            sent_count = await send_configs_from_new_messages(bot, new_messages)
            return sent_count, channel
        else:
            print(f"  📭 پیام جدیدی یافت نشد")
            return 0, channel
            
    except Exception as e:
        print(f"  ❌ خطا در بررسی {channel_name}: {e}")
        return 0, channel

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN تنظیم نشده!")
        return
    
    print("🤖 ربات استخراج کانفیگ از پیام‌های جدید")
    print("📡 در حال اتصال به تلگرام...")
    
    try:
        bot = Bot(token=BOT_TOKEN)
        me = await bot.get_me()
        print(f"✅ ربات متصل شد: @{me.username}")
    except Exception as e:
        print(f"❌ خطا در اتصال به تلگرام: {e}")
        return
    
    channels = load_last_messages()
    
    print(f"\n🔍 بررسی {len(channels)} کانال برای پیام‌های جدید...")
    
    total_configs_sent = 0
    
    for channel in channels:
        print(f"\n📭 کانال: {channel['url'].split('/')[-1]}")
        
        sent_count, updated_channel = await check_channel_for_new_messages(bot, channel)
        total_configs_sent += sent_count
        
        channel["last_id"] = updated_channel["last_id"]
        
        await asyncio.sleep(2)
    
    save_last_messages(channels)
    
    print(f"\n{'='*50}")
    print(f"📊 نتیجه نهایی:")
    print(f"   کل کانفیگ‌های ارسال شده: {total_configs_sent}")
    print(f"{'='*50}")
    
    if total_configs_sent > 0:
        print("✅ کار با موفقیت انجام شد!")
    else:
        print("📭 هیچ پیام جدیدی یافت نشد")

if __name__ == "__main__":
    asyncio.run(main())
