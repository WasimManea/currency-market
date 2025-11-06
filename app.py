import os
import json
import requests
from datetime import datetime, date
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Telegram bot token
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# CurrencyLayer API
CURRENCY_API_URL = "https://api.exchangerate.host/change"
ACCESS_KEY = "4fcbc72dcd2d4b364af824ea0c319a32"

# Sarf-Today API
SARF_TODAY_URL = "https://sarf-today.com/app_api/cur_market.json"

# Cache file for CurrencyLayer rates
CACHE_FILE = "currency_cache.json"
MAX_CALLS_PER_DAY = 3

# Fetch Sarf-Today rates
def get_sarf_today_rate(currency):
    try:
        response = requests.get(SARF_TODAY_URL)
        data = response.json()
        for item in data:
            if item["name"] == currency:
                return {
                    "ask": float(item["ask"]),
                    "bid": float(item["bid"]),
                    "change": item["change_percentage"]
                }
    except Exception as e:
        print("Sarf-Today API error:", e)
    return None

# Load cache
def load_cache():
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"date": str(date.today()), "calls": 0, "usd_egp": None, "aed_egp": None}

# Save cache
def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

# Fetch CurrencyLayer rates with max 3 calls/day
def get_currencylayer_rates():
    cache = load_cache()
    today_str = str(date.today())

    # Reset daily calls if it's a new day
    if cache["date"] != today_str:
        cache["date"] = today_str
        cache["calls"] = 0

    # If we haven't exceeded max calls, call API
    if cache["calls"] < MAX_CALLS_PER_DAY:
        try:
            params = {"currencies": "AED,EGP", "access_key": ACCESS_KEY}
            response = requests.get(CURRENCY_API_URL, params=params)
            data = response.json()

            if data.get("success") and "quotes" in data:
                usdaed = data["quotes"]["USDAED"]["end_rate"]
                usdegp = data["quotes"]["USDEGP"]["end_rate"]
                aed_to_egp = round(usdegp / usdaed, 4)
                usd_to_egp = round(usdegp, 4)

                # Update cache
                cache["usd_egp"] = usd_to_egp
                cache["aed_egp"] = aed_to_egp
                cache["calls"] += 1
                cache["rate_date"] = data.get("end_date", today_str)
                save_cache(cache)

                return usd_to_egp, aed_to_egp, cache["rate_date"]

        except Exception as e:
            print("CurrencyLayer API error:", e)
            # On error, fallback to cached rates if available
            if cache["usd_egp"] and cache["aed_egp"]:
                return cache["usd_egp"], cache["aed_egp"], cache.get("rate_date", today_str)
            return None, None, None
    else:
        # Use cached rates after max calls reached
        if cache["usd_egp"] and cache["aed_egp"]:
            return cache["usd_egp"], cache["aed_egp"], cache.get("rate_date", today_str)
    return None, None, None

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to *CurrencyBot Egypt!*\n\n"
        "Use /rate to get live USD and AED → EGP rates from Sarf-Today and CurrencyLayer.\n"
        "Example: /rate",
        parse_mode="Markdown"
    )

# /rate command
async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usd_market = get_sarf_today_rate("USD")
    aed_market = get_sarf_today_rate("AED")
    usd_official, aed_official, rate_date = get_currencylayer_rates()

    message = "💱 *Live Exchange Rates*\n\n"

    # USD
    message += "🇺🇸 *USD → EGP*\n"
    if usd_market:
        message += f"  • Market:  {usd_market['ask']:.2f} EGP (▲ {usd_market['change']}%)\n"
    if usd_official:
        message += f"  • Official: {usd_official} EGP (CurrencyLayer, {rate_date})\n"
    message += "\n"

    # AED
    message += "🇦🇪 *AED → EGP*\n"
    if aed_market:
        message += f"  • Market:  {aed_market['ask']:.2f} EGP (▲ {aed_market['change']}%)\n"
    if aed_official:
        message += f"  • Official: {aed_official} EGP (CurrencyLayer, {rate_date})\n"

    message += "\n_Data sources: Sarf-Today (Egypt Market) & CurrencyLayer_"

    await update.message.reply_text(message, parse_mode="Markdown")

# Main
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rate", rate))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
