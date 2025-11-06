import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ContextTypes

# Telegram bot token from environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Public URL provided by Railway (e.g., https://your-app-name.up.railway.app)
RAILWAY_URL = os.getenv("RAILWAY_PUBLIC_URL")

# CurrencyLayer change API
CURRENCY_API_URL = "https://api.exchangerate.host/change"
ACCESS_KEY = os.getenv("CURRENCY_API_KEY")  # better to store in env

def get_aed_egp_rate():
    try:
        params = {"currencies": "AED,EGP", "access_key": ACCESS_KEY}
        response = requests.get(CURRENCY_API_URL, params=params)
        data = response.json()

        if data.get("success") and "quotes" in data:
            usdaed = data["quotes"]["USDAED"]["end_rate"]
            usdegp = data["quotes"]["USDEGP"]["end_rate"]
            return round(usdegp / usdaed, 4)
        else:
            print("Currency API error:", data)
            return None
    except Exception as e:
        print("Currency API request failed:", e)
        return None

def get_usd_egp_rate():
    try:
        params = {"currencies": "EGP", "access_key": ACCESS_KEY}
        response = requests.get(CURRENCY_API_URL, params=params)
        data = response.json()
        if data.get("success") and "quotes" in data:
            return round(data["quotes"]["USDEGP"]["end_rate"], 4)
        return None
    except Exception as e:
        print("Currency API request failed:", e)
        return None

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to *CurrencyBot Egypt!*\n\n"
        "Use /rate to get USD and AED → EGP live rates.\n\n"
        "Example:\n/rate",
        parse_mode="Markdown"
    )

# /rate command
async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usd_egp = get_usd_egp_rate()
    aed_egp = get_aed_egp_rate()

    if usd_egp and aed_egp:
        message = (
            "💱 *Live Exchange Rates (CurrencyLayer)*\n\n"
            f"🇺🇸 1 USD = {usd_egp} EGP\n"
            f"🇦🇪 1 AED = {aed_egp} EGP\n\n"
            "_Rates updated daily._"
        )
    else:
        message = "⚠️ Couldn't fetch rates right now. Please try again later."

    await update.message.reply_text(message, parse_mode="Markdown")

# Main
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rate", rate))

    # Webhook setup for Railway
    if RAILWAY_URL:
        webhook_url = f"{RAILWAY_URL}/{BOT_TOKEN}"
        print(f"✅ Setting webhook to {webhook_url}")
        app.bot.set_webhook(webhook_url)
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", "8080")),
            webhook_path=f"/{BOT_TOKEN}"
        )
    else:
        print("❌ No Railway URL found, running with polling")
        app.run_polling()

if __name__ == "__main__":
    main()
