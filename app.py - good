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
def load_cache(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_cache(cache, file):
    with open(file, "w") as f:
        json.dump(cache, f)

def increment_usage(currency):
    today = datetime.date.today().isoformat()
    cache = load_cache(CACHE_FILE)
    if today not in cache:
        cache[today] = {}
    if currency not in cache[today]:
        cache[today][currency] = 0

    if cache[today][currency] >= DAILY_LIMIT:
        return False
    cache[today][currency] += 1
    save_cache(cache, CACHE_FILE)
    return True

# ----------------- API helpers with caching -----------------
def get_sarf_today_rate(currency):
    today = datetime.date.today().isoformat()
    cache = load_cache(API_CACHE_FILE)

    if today not in cache:
        cache[today] = {}

    if currency in cache[today]:
        return cache[today][currency]  # return cached value

    # Fetch from API
    try:
        response = requests.get(SARF_TODAY_URL)
        data = response.json()
        for item in data:
            if item["name"] == currency:
                rate = float(item["ask"])
                cache[today][currency] = rate
                save_cache(cache, API_CACHE_FILE)
                return rate
    except Exception as e:
        print("Sarf-Today API error:", e)
    return None

def get_currencylayer_rates():
    today = datetime.date.today().isoformat()
    cache = load_cache(API_CACHE_FILE)

    if today not in cache:
        cache[today] = {}

    if "USD" in cache[today] and "AED" in cache[today]:
        return cache[today]["USD"], cache[today]["AED"]

    try:
        params = {"currencies": "AED,EGP", "access_key": ACCESS_KEY}
        response = requests.get("https://api.exchangerate.host/change", params=params)
        data = response.json()
        if data.get("success") and "quotes" in data:
            usdaed = data["quotes"]["USDAED"]["end_rate"]
            usdegp = data["quotes"]["USDEGP"]["end_rate"]
            usd_rate = round(usdegp, 4)
            aed_rate = round(usdegp / usdaed, 4)
            cache[today]["USD"] = usd_rate
            cache[today]["AED"] = aed_rate
            save_cache(cache, API_CACHE_FILE)
            return usd_rate, aed_rate
    except Exception as e:
        print("CurrencyLayer API error:", e)
    return None, None

# ----------------- Telegram handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to CurrencyBot Egypt!\n"
        "Use /rate to get USD & AED → EGP live rates (daily limit applies)."
    )

async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check daily limit
    if not increment_usage("USD") or not increment_usage("AED"):
        await update.message.reply_text(
            "⚠️ Daily query limit reached. Please try again tomorrow."
        )
        return

    usd_market = get_sarf_today_rate("USD")
    aed_market = get_sarf_today_rate("AED")
    usd_official, aed_official = get_currencylayer_rates()

    message = "💱 Live Exchange Rates\n\n"

    message += "🇺🇸 USD → EGP\n"
    if usd_market:
        message += f"  • Market: {usd_market:.2f} EGP\n"
    if usd_official:
        message += f"  • Official: {usd_official} EGP\n"
    message += "\n"

    message += "🇦🇪 AED → EGP\n"
    if aed_market:
        message += f"  • Market: {aed_market:.2f} EGP\n"
    if aed_official:
        message += f"  • Official: {aed_official} EGP\n"

    await update.message.reply_text(message)

# ----------------- Main -----------------
def main():
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
