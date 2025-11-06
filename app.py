import os
import requests
import datetime
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ACCESS_KEY = os.getenv("ACCESS_KEY")
CACHE_FILE = "usage_cache.json"
API_CACHE_FILE = "api_cache.json"
DAILY_LIMIT = 20
SARF_TODAY_URL = "https://sarf-today.com/app_api/cur_market.json"

# ----------------- Cache helpers -----------------
def ensure_cache_files():
    """Ensure both cache files exist and print status."""
    for file in [CACHE_FILE, API_CACHE_FILE]:
        if not os.path.exists(file):
            with open(file, "w") as f:
                json.dump({}, f)
            print(f"🆕 Created new cache file: {file}")
        else:
            print(f"✅ Cache file found: {file}")

def load_cache(file):
    try:
        with open(file, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"⚠️ Failed to load cache from {file}: {e}")
        return {}

def save_cache(cache, file):
    try:
        with open(file, "w") as f:
            json.dump(cache, f, indent=2)
        print(f"💾 Cache updated → {file}")
    except Exception as e:
        print(f"❌ Failed to save cache {file}: {e}")

def increment_usage(currency):
    today = datetime.date.today().isoformat()
    cache = load_cache(CACHE_FILE)
    if today not in cache:
        cache[today] = {}
    if currency not in cache[today]:
        cache[today][currency] = 0

    if cache[today][currency] >= DAILY_LIMIT:
        print(f"⚠️ Daily limit reached for {currency}")
        return False

    cache[today][currency] += 1
    save_cache(cache, CACHE_FILE)
    print(f"🔢 Usage count for {currency}: {cache[today][currency]}/{DAILY_LIMIT}")
    return True

# ----------------- API helpers with caching -----------------
def get_sarf_today_rate(currency):
    today = datetime.date.today().isoformat()
    cache = load_cache(API_CACHE_FILE)

    if today not in cache:
        cache[today] = {}

    if currency in cache[today]:
        print(f"📦 Using cached market rate for {currency}: {cache[today][currency]}")
        return cache[today][currency]

    print(f"🌐 Fetching market rate for {currency} from Sarf-Today API...")
    try:
        response = requests.get(SARF_TODAY_URL, timeout=10)
        data = response.json()
        for item in data:
            if item["name"] == currency:
                rate = float(item["ask"])
                cache[today][currency] = rate
                save_cache(cache, API_CACHE_FILE)
                print(f"✅ Got {currency} rate: {rate}")
                return rate
    except Exception as e:
        print("❌ Sarf-Today API error:", e)
    return None

def get_currencylayer_rates():
    today = datetime.date.today().isoformat()
    cache = load_cache(API_CACHE_FILE)

    if today not in cache:
        cache[today] = {}

    if "USD" in cache[today] and "AED" in cache[today]:
        print("📦 Using cached official rates")
        return cache[today]["USD"], cache[today]["AED"]

    print("🌐 Fetching official rates from exchangerate.host ...")
    try:
        response = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=AED,EGP", timeout=10)
        data = response.json()
        if data.get("success", True):
            usd_rate = round(data["rates"]["EGP"], 4)
            aed_rate = round(data["rates"]["EGP"] / data["rates"]["AED"], 4)
            cache[today]["USD"] = usd_rate
            cache[today]["AED"] = aed_rate
            save_cache(cache, API_CACHE_FILE)
            print(f"✅ Updated official rates: USD={usd_rate}, AED={aed_rate}")
            return usd_rate, aed_rate
    except Exception as e:
        print("❌ Currency API error:", e)
    return None, None

# ----------------- Telegram handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to *CurrencyBot Egypt!*\n\n"
        "Use `/rate` to get 🇺🇸 USD & 🇦🇪 AED → 🇪🇬 EGP live rates.\n"
        f"Daily limit: {DAILY_LIMIT} requests per currency."
    )

async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not increment_usage("USD") or not increment_usage("AED"):
        await update.message.reply_text(
            "⚠️ *Daily query limit reached.* Please try again tomorrow."
        )
        return

    usd_market = get_sarf_today_rate("USD")
    aed_market = get_sarf_today_rate("AED")
    usd_official, aed_official = get_currencylayer_rates()

    message = "💱 *Live Exchange Rates*\n\n"

    message += "🇺🇸 *USD → EGP*\n"
    if usd_market:
        message += f"  • Market: `{usd_market:.2f}` EGP\n"
    if usd_official:
        message += f"  • Official: `{usd_official}` EGP\n"
    message += "\n"

    message += "🇦🇪 *AED → EGP*\n"
    if aed_market:
        message += f"  • Market: `{aed_market:.2f}` EGP\n"
    if aed_official:
        message += f"  • Official: `{aed_official}` EGP\n"

    await update.message.reply_text(message, parse_mode="Markdown")

# ----------------- Main -----------------
def main():
    ensure_cache_files()

    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set. Exiting...")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rate", rate))

    print("✅ Bot is running (polling mode)...")
    app.run_polling()

if __name__ == "__main__":
    main()
