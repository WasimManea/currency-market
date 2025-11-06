import os
import json
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ==========================
# Config
# ==========================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  # set in Railway env
RAILWAY_STATIC_URL = "currency-market-production.up.railway.app"
CACHE_FILE = "rate_cache.json"

EXCHANGERATE_API = "https://api.exchangerate.host/change?currencies=AED,EGP&access_key=4fcbc72dcd2d4b364af824ea0c319a32"
SARF_TODAY_API = "https://sarf-today.com/app_api/cur_market.json"
MAX_CALLS_PER_DAY = 3

# ==========================
# Helper Functions
# ==========================
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def get_exchangerate_data():
    """Fetch rate from ExchangeRate API and cache it."""
    cache = load_cache()
    today = datetime.utcnow().date().isoformat()

    # Check if cached for today
    if cache.get("date") == today and cache.get("calls", 0) < MAX_CALLS_PER_DAY:
        return cache.get("rates", {}), cache.get("source_date", today)

    try:
        resp = requests.get(EXCHANGERATE_API, timeout=10)
        data = resp.json()
        if data.get("success"):
            rates = {
                "USD_EGP": data["quotes"]["USDEGP"]["end_rate"],
                "AED_EGP": data["quotes"]["USDAED"]["end_rate"],
            }
            cache = {
                "date": today,
                "calls": cache.get("calls", 0) + 1,
                "rates": rates,
                "source_date": today,
            }
            save_cache(cache)
            return rates, today
    except Exception as e:
        print("ExchangeRate API failed:", e)

    # fallback to cached rates or empty
    return cache.get("rates", {}), cache.get("source_date", today)

def get_sarf_today_data():
    """Fetch rates from Sarf-Today"""
    try:
        resp = requests.get(SARF_TODAY_API, timeout=10)
        data = resp.json()
        rates = {}
        for item in data:
            if item["name"] == "USD":
                rates["USD_EGP"] = float(item["bid"])
            elif item["name"] == "AED":
                rates["AED_EGP"] = float(item["bid"])
        return rates
    except Exception as e:
        print("Sarf-Today API failed:", e)
        return {}

def get_combined_rates():
    """Combine ExchangeRate + Sarf-Today data for bot response"""
    rates, rate_date = get_exchangerate_data()
    sarf_rates = get_sarf_today_data()

    # Merge: ExchangeRate first, fallback to Sarf-Today
    combined = {}
    combined["USD_EGP"] = rates.get("USD_EGP") or sarf_rates.get("USD_EGP")
    combined["AED_EGP"] = rates.get("AED_EGP") or sarf_rates.get("AED_EGP")
    return combined, rate_date

# ==========================
# Handlers
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💱 Welcome! Use /rate to get the latest USD & AED to EGP exchange rates."
    )

async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates, rate_date = get_combined_rates()
    if not rates:
        await update.message.reply_text("❌ Unable to fetch rates at the moment.")
        return

    message = (
        f"💱 **Live Exchange Rates**\n\n"
        f"🇺🇸 USD → EGP\n"
        f"  • Official: {rates['USD_EGP']:.4f} EGP (CurrencyLayer, {rate_date})\n\n"
        f"🇦🇪 AED → EGP\n"
        f"  • Official: {rates['AED_EGP']:.4f} EGP (CurrencyLayer, {rate_date})\n\n"
        f"Data sources: Sarf-Today & CurrencyLayer"
    )
    await update.message.reply_text(message, parse_mode="Markdown")

# ==========================
# Main
# ==========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rate", rate))

    # Webhook setup
    PORT = int(os.environ.get("PORT", 8443))
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"https://{RAILWAY_STATIC_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
