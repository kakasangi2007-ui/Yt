import os, json, re, datetime, asyncio, base64, logging
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from urllib.parse import urlparse, urlunparse, quote

# ================== تنظیم لاگ ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT = os.getenv("TARGET_CHAT")

SOURCES = [
    "https://t.me/s/ConfigsHUB",
]

STATE_FILE = "last_messages.json"
MAX_LEN = 3800

CONFIG_NAME = "ConfigV2Ray_Free"
CHANNEL_USERNAME = "@ConfigV2Ray_Free"

HASHTAGS = "\n#config\n#v2ray"

MAX_CONFIGS_PER_RUN = 10
MAX_CONFIGS_JSON = 100
JSON_FILE = "configs.json"
# ===========================================

# ---------- Message Template ----------
HEADER = (
    "کانفیگ امروز V2Ray\n"
    "سازگار با اندروید و ویندوز\n"
    "تست‌شده | پایدار\n\n"
)

def footer(ts: str) -> str:
    return (
        f"\n—\n"
        f"{CHANNEL_USERNAME}\n"
        f"⏱ {ts}"
    )

# ---------- State ----------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)

# ---------- JSON Functions ----------
def save_json_configs(configs):
    """ذخیره کانفیگ‌ها با لاگ کامل"""
    try:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(configs, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ {len(configs)} کانفیگ در {JSON_FILE} ذخیره شد")
        return True
    except Exception as e:
        logger.error(f"❌ خطا در ذخیره JSON: {e}")
        return False

# ---------- Fetch ----------
def fetch_channel(url):
    logger.info(f"📡 در حال دریافت از {url}")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, "html.parser")
        posts = soup.select("div.tgme_widget_message")
        
        logger.info(f"✅ {len(posts)} پست از کانال دریافت شد")
        
        messages = []
        for p in posts:
            mid = p.get("data-post")
            if not mid:
                continue
            text = p.get_text("\n", strip=True)
            messages.append((mid, text))
        
        return messages
    except Exception as e:
        logger.error(f"❌ خطا در دریافت کانال: {e}")
        return []

# ---------- Extract ----------
def extract_configs(text):
    pattern = r'(vmess://[^\s]+|vless://[^\s]+|trojan://[^\s]+|ss://[^\s]+|ssr://[^\s]+)'
    configs = re.findall(pattern, text)
    if configs:
        logger.info(f"🔍 {len(configs)} کانفیگ در متن پیدا شد")
    return configs

# ---------- Validate ----------
def is_valid_vmess(cfg):
    try:
        raw = cfg.replace("vmess://", "")
        # اضافه کردن padding مناسب
        raw += "=" * (4 - len(raw) % 4)
        data = json.loads(base64.b64decode(raw).decode())
        return all(k in data for k in ("add", "port", "id"))
    except Exception as e:
        logger.debug(f"❌ vmess نامعتبر: {str(e)[:50]}")
        return False

def is_valid_link(cfg):
    try:
        p = urlparse(cfg)
        return p.hostname and p.port
    except:
        return False

def is_valid_ss(cfg):
    try:
        raw = cfg.split("://", 1)[1].split("#", 1)[0]
        raw += "=" * (4 - len(raw) % 4)
        base64.b64decode(raw)
        return True
    except:
        return False

def is_config_valid(cfg):
    if cfg.startswith("vmess://"):
        return is_valid_vmess(cfg)
    if cfg.startswith(("vless://", "trojan://")):
        return is_valid_link(cfg)
    if cfg.startswith(("ss://", "ssr://")):
        return is_valid_ss(cfg)
    return False

# ---------- Rename ----------
def rename_vmess(cfg, name):
    try:
        raw = cfg.replace("vmess://", "")
        raw += "=" * (4 - len(raw) % 4)
        data = json.loads(base64.b64decode(raw).decode())
        data["ps"] = name
        new_raw = base64.b64encode(
            json.dumps(data, ensure_ascii=False).encode()
        ).decode()
        return "vmess://" + new_raw
    except:
        return cfg

def rename_by_fragment(cfg, name):
    try:
        p = urlparse(cfg)
        return urlunparse(p._replace(fragment=quote(name)))
    except:
        return cfg

def rename_config(cfg):
    if cfg.startswith("vmess://"):
        return rename_vmess(cfg, CONFIG_NAME)
    return rename_by_fragment(cfg, CONFIG_NAME)

# ---------- Build Messages ----------
def build_messages(configs):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    messages = []

    cur = HEADER + "<blockquote><code>"
    msg_count = 0

    for cfg in configs:
        cfg = rename_config(cfg)
        piece = cfg + "\n"

        if len(cur) + len(piece) + len("</code></blockquote>") + len(footer(now)) > MAX_LEN:
            msg_count += 1
            tag = HASHTAGS if msg_count % 3 == 0 else ""

            cur = cur.rstrip("\n") + "</code></blockquote>" + tag + footer(now)
            messages.append(cur)
            cur = HEADER + "<blockquote><code>" + piece
        else:
            cur += piece

    if cur.strip():
        msg_count += 1
        tag = HASHTAGS if msg_count % 3 == 0 else ""
        cur = cur.rstrip("\n") + "</code></blockquote>" + tag + footer(now)
        messages.append(cur)

    return messages

# ---------- Main ----------
async def main():
    logger.info("="*50)
    logger.info("🚀 شروع اجرای ربات")
    
    # بررسی توکن
    if not BOT_TOKEN or not TARGET_CHAT:
        logger.error("❌ BOT_TOKEN یا TARGET_CHAT تعریف نشده!")
        return
    
    bot = Bot(BOT_TOKEN)
    state = load_state()
    all_new_configs = []

    # ====== جمع‌آوری کانفیگ‌ها ======
    for src in SOURCES:
        last_id = state.get(src)
        logger.info(f"📌 آخرین ID پردازش‌شده: {last_id}")
        
        posts = fetch_channel(src)
        
        if not posts:
            logger.warning(f"⚠️ هیچ پستی از {src} دریافت نشد")
            continue
            
        new_count = 0
        for mid, text in posts:
            if last_id and mid <= last_id:
                logger.info(f"⏭️ رد کردن پست تکراری: {mid}")
                break
                
            configs = extract_configs(text)
            for cfg in configs:
                if is_config_valid(cfg):
                    all_new_configs.append(cfg)
                    new_count += 1
                    logger.info(f"✅ کانفیگ جدید #{new_count} پیدا شد")
                else:
                    logger.debug(f"❌ کانفیگ نامعتبر: {cfg[:50]}...")

        if posts:
            state[src] = posts[0][0]
            logger.info(f"💾 وضعیت به‌روز شد: {state[src]}")

    logger.info(f"📊 تعداد کل کانفیگ‌های جدید: {len(all_new_configs)}")

    if not all_new_configs:
        logger.warning("⚠️ هیچ کانفیگ جدیدی پیدا نشد!")
        save_state(state)
        return

    # حذف تکراری
    seen = set()
    unique_configs = []
    for cfg in all_new_configs:
        if cfg not in seen:
            seen.add(cfg)
            unique_configs.append(cfg)
    
    logger.info(f"🔄 بعد از حذف تکراری: {len(unique_configs)} کانفیگ")

    # ====== ذخیره ۱۰۰ کانفیگ در JSON ======
    json_configs = unique_configs[-MAX_CONFIGS_JSON:]
    if save_json_configs(json_configs):
        logger.info(f"✅ فایل {JSON_FILE} با موفقیت ایجاد/به‌روز شد")
    else:
        logger.error(f"❌ ایجاد {JSON_FILE} ناموفق بود")

    # ====== ارسال ۱۰ کانفیگ به کانال ======
    send_configs = unique_configs[-MAX_CONFIGS_PER_RUN:]
    logger.info(f"📤 ارسال {len(send_configs)} کانفیگ به کانال")
    
    try:
        messages = build_messages(send_configs)
        for i, msg in enumerate(messages, 1):
            await bot.send_message(
                chat_id=TARGET_CHAT,
                text=msg,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            logger.info(f"✅ پیام {i} از {len(messages)} ارسال شد")
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"❌ خطا در ارسال پیام: {e}")

    save_state(state)
    logger.info("🏁 اجرای ربات به پایان رسید")

if __name__ == "__main__":
    asyncio.run(main())
