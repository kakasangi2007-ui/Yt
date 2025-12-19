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

def extract_raw_messages(html_content):
    """متن خام پیام‌ها را بدون دستکاری استخراج می‌کند"""
    messages_data = []
    
    # الگوی بهبود یافته برای گرفتن کل پیام
    message_pattern = r'<div class="tgme_widget_message[^>]*data-post="([^"]+)"[^>]*>(.*?)<div class="tgme_widget_message_footer'
    messages = re.findall(message_pattern, html_content, re.DOTALL)
    
    for post_id, message_html in messages:
        # استخراج متن اصلی پیام
        text_pattern = r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>'
        text_match = re.search(text_pattern, message_html, re.DOTALL)
        
        if text_match:
            raw_text = text_match.group(1)
            
            # **مهم: بدون هیچ پردازشی، متن را همانطور که هست برمی‌گردانیم**
            # فقط تگ‌های HTML را حذف می‌کنیم
            clean_text = re.sub(r'<[^>]+>', '', raw_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            messages_data.append({
                "post_id": post_id,
                "raw_text": raw_text,  # متن اصلی با HTML
                "clean_text": clean_text  # متن بدون HTML
            })
    
    return messages_data

def find_all_configs_in_text(text):
    """همه کانفیگ‌ها را در متن پیدا می‌کند (بدون تغییر)"""
    configs = []
    
    # همه مواردی که با پروتکل شروع می‌شوند
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # کانفیگ‌های معروف
        if any(line.startswith(proto) for proto in [
            'vmess://', 'vless://', 'ss://', 'trojan://', 'hy2://',
            'VMESS://', 'VLESS://', 'SS://', 'TROJAN://', 'HY2://'
        ]):
            # کانفیگ کامل را بگیر (تا انتهای خط یا تا space)
            config = line.split()[0] if ' ' in line else line
            if len(config) > 10:  # حداقل طول
                configs.append(config)
        
        # لینک‌های subscribe
        elif 'http' in line.lower() and ('subscribe' in line.lower() or 'sub' in line.lower()):
            configs.append(line.split()[0] if ' ' in line else line)
    
    return configs

async def send_all_configs_together(bot, messages_data):
    """همه کانفیگ‌های جدید را در یک پیام ارسال می‌کند"""
    if not messages_data:
        return 0
    
    all_configs = []
    
    # جمع‌آوری همه کانفیگ‌ها از همه پیام‌های جدید
    for message in messages_data:
        configs = find_all_configs_in_text(message["clean_text"])
        all_configs.extend(configs)
    
    if not all_configs:
        print("  📭 هیچ کانفیگی در پیام‌ها یافت نشد")
        return 0
    
    # حذف تکراری‌ها (اما حفظ ترتیب)
    unique_configs = []
    seen = set()
    for config in all_configs:
        if config not in seen:
            seen.add(config)
            unique_configs.append(config)
    
    print(f"  📦 {len(unique_configs)} کانفیگ منحصر به فرد یافت شد")
    
    # ساخت یک پیام بزرگ با همه کانفیگ‌ها
    message_text = "<b>🌟 کانفیگ‌های جدید 🌟</b>\n\n"
    message_text += "<b>🔗 تمام کانفیگ‌ها (کپی‌شدنی):</b>\n\n"
    
    for i, config in enumerate(unique_configs, 1):
        message_text += f"<code>{config}</code>\n\n"
    
    message_text += "<b>🌐 وبسایت برای کانفیگ‌های بیشتر:</b>\n"
    message_text += "https://configfree.github.io/Configfree/\n\n"
    message_text += "<b>📌 کانال ما:</b> @configs_freeiran\n"
    message_text += "============================"
    
    # اگر پیام خیلی بزرگ شد، تقسیم کن
    if len(message_text) > 4000:
        print(f"  ⚠️ پیام بزرگ است ({len(message_text)} کاراکتر)، تقسیم می‌شود...")
        
        # پیام اول: هدر + 15 کانفیگ اول
        first_part = "<b>🌟 کانفیگ‌های جدید 🌟</b>\n\n"
        first_part += "<b>🔗 کانفیگ‌ها (قسمت ۱):</b>\n\n"
        
        for config in unique_configs[:15]:
            first_part += f"<code>{config}</code>\n\n"
        
        first_part += "<b>ادامه در پیام بعدی...</b>\n"
        first_part += "============================"
        
        # پیام دوم: بقیه کانفیگ‌ها
        second_part = "<b>🌟 کانفیگ‌های جدید 🌟</b>\n\n"
        second_part += "<b>🔗 کانفیگ‌ها (قسمت ۲):</b>\n\n"
        
        for config in unique_configs[15:30]:
            second_part += f"<code>{config}</code>\n\n"
        
        if len(unique_configs) > 30:
            second_part += f"\nو {len(unique_configs) - 30} کانفیگ دیگر...\n"
        
        second_part += "<b>🌐 وبسایت برای کانفیگ‌های بیشتر:</b>\n"
        second_part += "https://configfree.github.io/Configfree/\n\n"
        second_part += "<b>📌 کانال ما:</b> @configs_freeiran\n"
        second_part += "============================"
        
        try:
            # ارسال قسمت اول
            await bot.send_message(
                chat_id=DESTINATION_CHANNEL,
                text=first_part,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            await asyncio.sleep(1)
            
            # ارسال قسمت دوم
            await bot.send_message(
                chat_id=DESTINATION_CHANNEL,
                text=second_part,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            print(f"  ✅ کانفیگ‌ها در ۲ پیام ارسال شدند")
            return len(unique_configs)
            
        except TelegramError as e:
            print(f"  ❌ خطا در ارسال: {e}")
            return 0
    else:
        # ارسال در یک پیام
        try:
            await bot.send_message(
                chat_id=DESTINATION_CHANNEL,
                text=message_text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            print(f"  ✅ همه کانفیگ‌ها در یک پیام ارسال شد")
            return len(unique_configs)
        except TelegramError as e:
            print(f"  ❌ خطا در ارسال: {e}")
            return 0

async def check_channel_for_new_messages(bot, channel):
    """کانال را بررسی و کانفیگ‌های جدید را ارسال می‌کند"""
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
        
        # استخراج پیام‌های خام (بدون پردازش کانفیگ)
        all_messages = extract_raw_messages(response.text)
        
        if not all_messages:
            print(f"  📭 هیچ پیامی یافت نشد")
            return 0, channel
        
        # پیدا کردن پیام‌های جدید
        new_messages = []
        if channel["last_id"]:
            for msg in all_messages:
                if msg["post_id"] == channel["last_id"]:
                    break
                new_messages.append(msg)
        else:
            # اولین بار: فقط آخرین پیام
            new_messages = [all_messages[0]] if all_messages else []
        
        if new_messages:
            channel["last_id"] = new_messages[0]["post_id"]
            print(f"  📨 {len(new_messages)} پیام جدید یافت شد")
            
            # ارسال همه کانفیگ‌ها در یک پیام
            sent_count = await send_all_configs_together(bot, new_messages)
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
        print("📭 هیچ کانفیگ جدیدی یافت نشد")

if __name__ == "__main__":
    asyncio.run(main())
