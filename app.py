import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Telegram bot token from environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# API URLs
FRANKFURTER_URL = "https://api.frankfurter.app/latest"
SARF_TODAY_URL = "https://sarf-today.com/app_api/cur_market.json"

# Fetch official rate from Frankfurter
def get_frankfurter_rate(from_currency, to_currency):
    try:
        response = requests.get(f"{FRANKFURTER_URL}?from={from_currency}&to={to_currency}")
        data = response.json()
        return data["rates"].get(to_currency)
    except Exception as e:
        print(f"Frankfurter API error: {e}")
        return None

# Fetch market rate from Sarf-Today
def get_sarf_today_rate(currency):
    try:
        response = requests.get(SARF_TODAY_URL)
        data = response.json()
        for item in data:
            if item["name"] == currency:
                return {
                    "ask": float(item["ask"]),
                    "bid": float(item["bid"]),
                    "change": item["change_percentage"],
                }
    except Exception as e:
        print(f"Sarf-Today API error: {e}")
    return None

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to *CurrencyBot Egypt!*\n\n"
        "Use /rate to get live USD and AED to EGP rates.\n\n"
        "Example:\n/rate",
        parse_mode="Markdown"
    )

# /rate command
async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Official ECB rates
    usd_official = get_frankfurter_rate("USD", "EGP")
    aed_official = get_frankfurter_rate("AED", "EGP")

    # Egyptian market rates
    usd_market = get_sarf_today_rate("USD")
    aed_market = get_sarf_today_rate("AED")

    if usd_market and aed_market and usd_official and aed_official:
        message = (
            "💱 *Live Exchange Rates*\n\n"
            "🇺🇸 *USD → EGP*\n"
            f"  • Official: {usd_official:.2f} EGP\n"
            f"  • Market:  {usd_market['ask']:.2f} EGP (▲ {usd_market['change']}%)\n\n"
            "🇦🇪 *AED → EGP*\n"
            f"  • Official: {aed_official:.2f} EGP\n"
            f"  • Market:  {aed_market['ask']:.2f} EGP (▲ {aed_market['change']}%)\n\n"
            "_Official rates: Frankfurter (ECB)_\n"
            "_Market rates: Sarf-Today Egypt_"
        )
    else:
        message = "⚠️ Couldn’t fetch rates right now. Please try again later."

    await update.message.reply_text(message, parse_mode="Markdown")

# Main
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rate", rate))

    print("✅ Bot is running and connected to both APIs...")
    app.run_polling()

if __name__ == "__main__":
    main()
