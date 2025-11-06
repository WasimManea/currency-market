import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Telegram bot token from environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# CurrencyLayer API
CURRENCY_API_URL = "https://api.exchangerate.host/change"
ACCESS_KEY = "4fcbc72dcd2d4b364af824ea0c319a32"

# Sarf-Today API
SARF_TODAY_URL = "https://sarf-today.com/app_api/cur_market.json"

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

# Fetch CurrencyLayer USD and AED → EGP
def get_currencylayer_rates():
    try:
        params = {"currencies": "AED,EGP", "access_key": ACCESS_KEY}
        response = requests.get(CURRENCY_API_URL, params=params)
        data = response.json()

        if data.get("success") and "quotes" in data:
            usdaed = data["quotes"]["USDAED"]["end_rate"]
            usdegp = data["quotes"]["USDEGP"]["end_rate"]
            aed_to_egp = round(usdegp / usdaed, 4)
            usd_to_egp = round(usdegp, 4)
            return usd_to_egp, aed_to_egp
    except Exception as e:
        print("CurrencyLayer API error:", e)
    return None, None

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
    usd_official, aed_official = get_currencylayer_rates()

    message = "💱 *Live Exchange Rates*\n\n"

    # USD
    message += "🇺🇸 *USD → EGP*\n"
    if usd_market:
        message += f"  • Market:  {usd_market['ask']:.2f} EGP (▲ {usd_market['change']}%)\n"
    if usd_official:
        message += f"  • Official: {usd_official} EGP (CurrencyLayer)\n"
    message += "\n"

    # AED
    message += "🇦🇪 *AED → EGP*\n"
    if aed_market:
        message += f"  • Market:  {aed_market['ask']:.2f} EGP (▲ {aed_market['change']}%)\n"
    if aed_official:
        message += f"  • Official: {aed_official} EGP (CurrencyLayer)\n"

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
