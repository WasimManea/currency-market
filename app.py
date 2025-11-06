import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Get BOT_TOKEN from environment
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables")

# Get PORT from server (Railway sets this automatically)
PORT = int(os.environ.get("PORT", 8443))

# Fixed app URL
APP_URL = "https://currency-market-production.up.railway.app"

# Handler for /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! 👋")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add /start command handler
    app.add_handler(CommandHandler("start", start))

    # Run webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{APP_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
