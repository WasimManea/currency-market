import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ACCESS_KEY = os.getenv("ACCESS_KEY")
SARF_TODAY_URL = "https://sarf-today.com/app_api/cur_market.json"

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

def get_currencylayer_rates():
    try:
        params = {"currencies": "AED,EGP", "access_key": ACCESS_KEY}
        response = requests.get("https://api.exchangerate.host/change", params=params)
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to CurrencyBot Egypt!\nUse /rate to get USD & AED → EGP live rates."
    )

async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usd_market = get_sarf_today_rate("USD")
    aed_market = get_sarf_today_rate("AED")
    usd_official, aed_official = get_currencylayer_rates()

    message = "💱 Live Exchange Rates\n\n"

    message += "🇺🇸 USD → EGP\n"
    if usd_market:
        message += f"  • Market: {usd_market['ask']:.2f} EGP (▲ {usd_market['change']}%)\n"
    if usd_official:
        message += f"  • Official: {usd_official} EGP\n"
    message += "\n"

    message += "🇦🇪 AED → EGP\n"
    if aed_market:
        message += f"  • Market: {aed_market['ask']:.2f} EGP (▲ {aed_market['change']}%)\n"
    if aed_official:
        message += f"  • Official: {aed_official} EGP\n"

    await update.message.reply_text(message)

async def main():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set. Exiting...")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rate", rate))

    print("✅ Bot is running (polling mode)...")
    await app.run_polling()  # long polling, no public URL required

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
