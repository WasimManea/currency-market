import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
RAILWAY_STATIC_URL = "currency-market-production.up.railway.app"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is working!")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    PORT = int(os.environ.get("PORT"))
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"https://{RAILWAY_STATIC_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
