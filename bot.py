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

MAX_CONFIGS_PER_RUN = 10  # تعداد برای ارسال به کانال
MAX_CONFIGS_JSON = 100    # تعداد برای فایل JSON
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
    """ذخیره دقیقاً ۱۰۰ کانفیگ در JSON"""
    try:
        # اگر کمتر از ۱۰۰ تا بود، با None پر کن
        if len(configs) < MAX_CONFIGS_JSON:
            logger.warning(f"⚠️ فقط {len(configs)} کانفیگ موجود است، با None پر می‌شود")
            configs = configs + [None] * (MAX_CONFIGS_JSON - len(configs))
        
        # اگر بیشتر از ۱۰۰ بود، فقط ۱۰۰ تای آخر را بردار
        elif len(configs) > MAX_CONFIGS_JSON:
            configs = configs[-MAX_CONFIGS_JSON:]
            logger.info(f"✂️ تعداد کانفیگ‌ها به {MAX_CONFIGS_JSON} کاهش یافت")
        
        # ذخیره در فایل
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(configs, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ دقیقاً {len(configs)} کانفیگ در {JSON_FILE} ذخیره شد")
        return True
    except Exception as e:
        logger.error(f"❌ خطا در ذخیره JSON: {e}")
        return False

# ---------- Fetch Functions ----------
def fetch_all_configs_from_channel(url, max_configs=100):
    """دریافت ۱۰۰ کانفیگ آخر (برای JSON) - کاملاً جدا"""
    logger.info(f"📡 دریافت کانفیگ‌ها از {url} برای فایل JSON")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        posts = soup.select("div.tgme_widget_message")
        
        all_configs = []
        for p in posts:
            text = p.get_text("\n", strip=True)
            configs = extract_configs(text)
            for cfg in configs:
                if is_config_valid(cfg):
                    all_configs.append(cfg)
        
        logger.info(f"✅ {len(all_configs)} کانفیگ از صفحه دریافت شد")
        return all_configs[-max_configs:] if all_configs else []
    except Exception as e:
        logger.error(f"❌ خطا در دریافت: {e}")
        return []

def fetch_channel_posts(url):
    """دریافت پست‌های کانال (برای state و ارسال) - کاملاً جدا"""
    logger.info(f"📡 دریافت پست‌ها از {url} برای ارسال به کانال")
    try:
        r = requests.get(url, timeout=30)
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
        
        logger.info(f"✅ {len(messages)} پست دریافت شد")
        return messages
    except Exception as e:
        logger.error(f"❌ خطا در دریافت پست‌ها: {e}")
        return []

# ---------- Extract ----------
def extract_configs(text):
    pattern = r'(vmess://[^\s]+|vless://[^\s]+|trojan://[^\s]+|ss://[^\s]+|ssr://[^\s]+)'
    configs = re.findall(pattern, text)
    if configs:
        logger.debug(f"🔍 {len(configs)} کانفیگ در متن پیدا شد")
    return configs

# ---------- Validate ----------
def is_valid_vmess(cfg):
    try:
        raw = cfg.replace("vmess://", "")
        raw += "=" * (4 - len(raw) % 4)
        data = json.loads(base64.b64decode(raw).decode())
        return all(k in data for k in ("add", "port", "id"))
    except:
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
    
    # ============================================================
    # بخش ۱: دریافت و ذخیره ۱۰۰ کانفیگ آخر در JSON (کاملاً جدا)
    # ============================================================
    logger.info("📥 بخش ۱: دریافت ۱۰۰ کانفیگ آخر برای فایل JSON...")
    
    all_configs_for_json = []
    for src in SOURCES:
        configs = fetch_all_configs_from_channel(src, MAX_CONFIGS_JSON)
        all_configs_for_json.extend(configs)
        logger.info(f"📊 از {src}: {len(configs)} کانفیگ دریافت شد")
    
    # حذف تکراری برای JSON
    seen_json = set()
    unique_configs_json = []
    for cfg in all_configs_for_json:
        if cfg not in seen_json:
            seen_json.add(cfg)
            unique_configs_json.append(cfg)
    
    logger.info(f"🔄 بعد از حذف تکراری: {len(unique_configs_json)} کانفیگ برای JSON")
    
    # گرفتن ۱۰۰ تای آخر و ذخیره
    json_configs = unique_configs_json[-MAX_CONFIGS_JSON:] if unique_configs_json else []
    
    # اطمینان از دقیقاً ۱۰۰ تا بودن
    if len(json_configs) < MAX_CONFIGS_JSON:
        json_configs = json_configs + [None] * (MAX_CONFIGS_JSON - len(json_configs))
        logger.warning(f"⚠️ تعداد کانفیگ‌ها به {len(json_configs)} رسید (با None پر شد)")
    elif len(json_configs) > MAX_CONFIGS_JSON:
        json_configs = json_configs[-MAX_CONFIGS_JSON:]
        logger.info(f"✂️ تعداد کانفیگ‌ها به {MAX_CONFIGS_JSON} کاهش یافت")
    
    # ذخیره در فایل JSON
    if save_json_configs(json_configs):
        actual_configs = [c for c in json_configs if c is not None]
        logger.info(f"✅ فایل {JSON_FILE} با {len(actual_configs)} کانفیگ واقعی به‌روز شد")
        if actual_configs:
            logger.info(f"📝 نمونه کانفیگ اول: {actual_configs[0][:50]}...")
    else:
        logger.error(f"❌ خطا در ذخیره {JSON_FILE}")
    
    # ============================================================
    # بخش ۲: دریافت و ارسال ۱۰ کانفیگ جدید به کانال (کاملاً جدا)
    # ============================================================
    logger.info("📤 بخش ۲: دریافت کانفیگ‌های جدید برای ارسال به کانال...")
    
    state = load_state()
    all_new_configs = []
    
    for src in SOURCES:
        last_id = state.get(src)
        posts = fetch_channel_posts(src)  # ✅ تابع درست برای پست‌ها
        
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
        
        if posts:
            state[src] = posts[0][0]
            logger.info(f"💾 وضعیت به‌روز شد: {state[src]}")
        
        logger.info(f"📊 از {src}: {new_count} کانفیگ جدید پیدا شد")
    
    logger.info(f"📊 تعداد کل کانفیگ‌های جدید: {len(all_new_configs)}")
    
    # ارسال به کانال
    if all_new_configs:
        # حذف تکراری برای ارسال
        seen_send = set()
        unique_send = []
        for cfg in all_new_configs:
            if cfg not in seen_send:
                seen_send.add(cfg)
                unique_send.append(cfg)
        
        send_configs = unique_send[-MAX_CONFIGS_PER_RUN:]
        logger.info(f"📤 ارسال {len(send_configs)} کانفیگ به کانال")
        
        messages = build_messages(send_configs)
        bot = Bot(BOT_TOKEN)
        
        for i, msg in enumerate(messages, 1):
            try:
                await bot.send_message(
                    chat_id=TARGET_CHAT,
                    text=msg,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
                logger.info(f"✅ پیام {i} از {len(messages)} ارسال شد")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"❌ خطا در ارسال پیام {i}: {e}")
        
        save_state(state)
    else:
        logger.info("ℹ️ کانفیگ جدیدی برای ارسال وجود ندارد")
    
    logger.info("="*50)
    logger.info("🏁 اجرای ربات با موفقیت به پایان رسید")

if __name__ == "__main__":
    asyncio.run(main())
