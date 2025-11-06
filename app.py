import os
import json
from datetime import date
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Bot token and CurrencyLayer key
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # set in Railway env vars
ACCESS_KEY = os.getenv("CURRENCY_ACCESS_KEY")  # set in Railway env vars

# Railway static URL
RAILWAY_URL = "currency-market-production.up.railway.app"

# API URLs
CURRENCY_API_URL = "https://api.exchangerate.host/change"
SARF_TODAY_URL = "https://sarf-today.com/app_api/cur_market.json"

# Cache setup
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, "currency_cache.json")
MAX_CALLS_PER_DAY = 3

# Fetch Sarf-Today market rate
def get_sarf_today_rate(currency):
    try:
        resp = requests.get(SARF_TODAY_URL, timeout=10)
        data = resp.json()
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

# Load/save cache
def load_cache():
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"date": str(date.today()), "calls": 0, "usd_egp": None, "aed_egp": None}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

# Fetch CurrencyLayer rates with caching
def get_currencylayer_rates():
    cache = load_cache()
    today_str = str(date.today())

    if cache.get("date") != today_str:
        cache["date"] = today_str
        cache["calls"] = 0

    if cache["calls"] < MAX_CALLS_PER_DAY:
        try:
            params = {"currencies": "AED,EGP", "access_key": ACCESS_KEY}
            response = requests.get(CURRENCY_API_URL, params=params, timeout=10)
            data = response.json()
            if data.get("success") and "quotes" in data:
                usdaed = data["quotes"]["USDAED"]["end_rate"]
                usdegp = data["quotes"]["USDEGP"]["end_rate"]
                aed_to_egp = round(usdegp / usdaed, 4)
                usd_to_egp = round(usdegp, 4)
                cache.update({
                    "usd_egp": usd_to_egp,
                    "aed_egp": aed_to_egp,
                    "calls": cache.get("calls", 0) + 1,
                    "rate_date": data.get("end_date", today_str)
                })
                save_cache(cache)
                return usd_to_egp, aed_to_egp, cache["rate_date"]
        except Exception as e:
            print("CurrencyLayer API error:", e)
            if cache.get("usd_egp") and cache.get("aed_egp"):
                return cache["usd_egp"], cache["aed_egp"], cache.get("rate_date", today_str)
            return None, None, None
    else:
        if cache.get("usd_egp") and cache.get("aed_egp"):
            return cache["usd_egp"], cache["aed_egp"], cache.get("rate_date", today_str)
    return None, None, None

# Trend arrow
def trend_arrow(change_pct):
    if change_pct is None:
        return ""
    return "▲" if float(change_pct) > 0 else "▼"

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

    message = "💱 *Live Exchange Rates – Egypt*\n\n"
    message += f"📅 Rate Date: {rate_date or str(date.today())}\n\n"

    # USD
    message += "🇺🇸 *USD → EGP*\n"
    if usd_market:
        arrow = trend_arrow(usd_market['change'])
        message += f"  • Market: {usd_market['ask']:.2f} EGP ({arrow} {usd_market['change']}%)\n"
    if usd_official:
        message += f"  • Official: {usd_official:.4f} EGP (CurrencyLayer)\n"
    message += "\n"

    # AED
    message += "🇦🇪 *AED → EGP*\n"
    if aed_market:
        arrow = trend_arrow(aed_market['change'])
        message += f"  • Market: {aed_market['ask']:.2f} EGP ({arrow} {aed_market['change']}%)\n"
    if aed_official:
        message += f"  • Official: {aed_official:.4f} EGP (CurrencyLayer)\n"
    message += "\n"

    message += "\n📝 Data sources: Sarf-Today (Market) & CurrencyLayer (Official, cached max 3/day)"
    await update.message.reply_text(message, parse_mode="Markdown")

# Main
def main():
    port = int(os.environ.get("PORT", 8081))
    webhook_url = f"https://{RAILWAY_URL}/{BOT_TOKEN}"  # your Railway URL + bot token

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rate", rate))

    print("✅ Bot running with webhook...")
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=webhook_url
    )

if __name__ == "__main__":
    main()
