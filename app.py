import os
import requests
import logging
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler
import gspread
from google.oauth2.service_account import Credentials

# --- ENV VARS ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")  # optional
GOOGLE_CRED_JSON = os.environ.get("GOOGLE_CRED_JSON")  # optional (stringified service account JSON)

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI for webhook ---
app = FastAPI()
TELEGRAM_PATH = "/webhook"

# --- Google Sheets Setup (optional) ---
gc = None
sheet = None
if GOOGLE_CRED_JSON and GOOGLE_SHEET_ID:
    creds = Credentials.from_service_account_info(eval(GOOGLE_CRED_JSON), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1

# --- Helper to fetch rates ---
def get_rates():
    url = "https://sarf-today.com/app_api/cur_market.json"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

def find_currency(rates, code):
    for c in rates:
        if c["name"].upper() == code.upper():
            return c
    return None

def convert_to_egp(amount, from_currency):
    rates = get_rates()
    cur = find_currency(rates, from_currency)
    if not cur:
        return None
    egp_value = amount * float(cur["ask"])
    return egp_value, cur["ask"]

# --- Telegram commands ---
async def start(update: Update, context):
    msg = (
        "Welcome to 💱 Currency Bot!\n"
        "Use:\n"
        "• /usd <amount> → Convert USD → EGP\n"
        "• /aed <amount> → Convert AED → EGP\n"
        "• /convert <amount> <currency_code> → Convert any currency → EGP"
    )
    await update.message.reply_text(msg)

async def usd(update: Update, context):
    await convert_command(update, context, "USD")

async def aed(update: Update, context):
    await convert_command(update, context, "AED")

async def convert_command(update: Update, context, currency=None):
    try:
        args = context.args
        if not args:
            await update.message.reply_text("Please enter an amount. Example: /usd 10")
            return

        if currency:
            amount = float(args[0])
            cur = currency
        else:
            if len(args) < 2:
                await update.message.reply_text("Usage: /convert <amount> <currency_code>")
                return
            amount = float(args[0])
            cur = args[1].upper()

        egp_value, rate = convert_to_egp(amount, cur)
        if egp_value is None:
            await update.message.reply_text(f"Currency {cur} not found.")
            return

        msg = f"{amount} {cur} = {egp_value:.2f} EGP 💰\n(1 {cur} = {rate} EGP)"
        await update.message.reply_text(msg)

        # Log to Google Sheet
        if sheet:
            sheet.append_row([cur, amount, egp_value, rate, update.message.from_user.username or "", update.message.date.isoformat()])

    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error fetching rate. Please try again later.")

# --- Telegram setup ---
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("usd", usd))
application.add_handler(CommandHandler("aed", aed))
application.add_handler(CommandHandler("convert", convert_command))

# --- FastAPI webhook endpoint ---
@app.post(TELEGRAM_PATH)
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

# --- Root check ---
@app.get("/")
def home():
    return {"message": "Currency bot running."}

# --- Run on Railway ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
