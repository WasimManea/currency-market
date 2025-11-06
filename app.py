import os
import json
import datetime
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ACCESS_KEY = os.getenv("ACCESS_KEY")
CACHE_FILE = "usage_cache.json"
DAILY_LIMIT = 20  # max queries per currency per day
SARF_TODAY_URL = "https://sarf-today.com/app_api/cur_market.json"

# -------------------------------
# Cache helpers
# -------------------------------
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r") as f:
        return json.load(f)

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

def increment_usage(currency):
    today = datetime.date.today().isoformat()
    cache = load_cache()
    if today not in cache:
        cache[today] = {}
    if currency not in cache[today]:
        cache[today][currency] = 0

    if cache[today][currency] >= DAILY_LIMIT:
        return False  # limit reached

    cache[today][currency] += 1
    save_cache(cache)
    return True

# -------------------------------
# API helpers
# -------------------------------
def get_sarf_today_rate(currency):
    try:
        response = requests.get(SARF_TODAY_URL)
        data = response.json()
        for item in data:
            if item["name"] == currency:
                return float(item["ask"])
    except Exception as e:
        print("Sarf-Today API error:", e)
    return None

def get_currencylayer_rates():
    try:
        params = {"currencies": "AED,EGP", "access_key": ACCESS_KEY}
        response = requests.get("https://api.exchangerate.host/change", params=params)
        data = response.json()
        if data.get("success") and "quotes" in data:
            usdaed = data["quotes"]["USDAED"]["end_rate"]
            usdegp = data["quotes"]["USDEGP"]["end_rate"]
            return round(usdegp, 4), round(usdegp / usdaed, 4)
    except Exception as e:
        print("CurrencyLayer API error:", e)
    return None, None

# -------------------------------
# Telegram handlers
# -------------------------------
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

# -------------------------------
# Main
# -------------------------------
async def main():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set. Exiting...")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rate", rate))

    print("✅ Bot is running (polling mode)...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
