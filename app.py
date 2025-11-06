import os
import requests
import datetime
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ACCESS_KEY = os.getenv("ACCESS_KEY")
CACHE_FILE = "usage_cache.json"
API_CACHE_FILE = "api_cache.json"
DAILY_LIMIT = 20
SARF_TODAY_URL = "https://sarf-today.com/app_api/cur_market.json"
ADMIN_USERNAME = "Wasim_muhammed"


# ----------------- Cache helpers -----------------
def ensure_cache_files():
    """Ensure both cache files exist and print status."""
    for file in [CACHE_FILE, API_CACHE_FILE]:
        if not os.path.exists(file):
            with open(file, "w") as f:
                json.dump({}, f)
            print(f"🆕 Created new cache file: {file}")
        else:
            print(f"✅ Cache file found: {file}")


def load_cache(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load cache from {file}: {e}")
        return {}


def save_cache(cache, file):
    try:
        with open(file, "w") as f:
            json.dump(cache, f, indent=2)
        print(f"💾 Cache updated → {file}")
    except Exception as e:
        print(f"❌ Failed to save cache {file}: {e}")


def increment_usage(currency):
    today = datetime.date.today().isoformat()
    cache = load_cache(CACHE_FILE)
    if today not in cache:
        cache[today] = {}
    if currency not in cache[today]:
        cache[today][currency] = 0

    if cache[today][currency] >= DAILY_LIMIT:
        print(f"⚠️ Daily limit reached for {currency}")
        return False

    cache[today][currency] += 1
    save_cache(cache, CACHE_FILE)
    print(f"🔢 Usage count for {currency}: {cache[today][currency]}/{DAILY_LIMIT}")
    return True


# ----------------- API helpers with caching -----------------
def get_sarf_today_rate(currency):
    today = datetime.date.today().isoformat()
    cache = load_cache(API_CACHE_FILE)

    if today not in cache:
        cache[today] = {}

    if currency in cache[today]:
        print(f"📦 Using cached market rate for {currency}: {cache[today][currency]}")
        return cache[today][currency]

    print(f"🌐 Fetching market rate for {currency} from Sarf-Today API...")
    try:
        response = requests.get(SARF_TODAY_URL, timeout=10)
        data = response.json()
        for item in data:
            if item["name"] == currency:
                rate = float(item["ask"])
                cache[today][currency] = rate
                save_cache(cache, API_CACHE_FILE)
                print(f"✅ Got {currency} rate: {rate}")
                return rate
    except Exception as e:
        print("❌ Sarf-Today API error:", e)
    return None


def get_currencylayer_rates():
    """
    Fetch official rates using exchangerate.host/change.
    We compute:
      - USD → EGP
      - AED → EGP = USD_EGP / USD_AED
    """
    today = datetime.date.today().isoformat()
    cache = load_cache(API_CACHE_FILE)

    if today not in cache:
        cache[today] = {}

    if "USD" in cache[today] and "AED" in cache[today]:
        print("📦 Using cached official rates")
        return cache[today]["USD"], cache[today]["AED"]

    print("🌐 Fetching official rates from exchangerate.host/change ...")
    try:
        params = {"currencies": "EGP,AED", "access_key": ACCESS_KEY}
        response = requests.get("https://api.exchangerate.host/change", params=params, timeout=10)
        data = response.json()
        if not data.get("success"):
            print(f"⚠️ API returned error: {data}")
            return None, None

        quotes = data.get("quotes", {})
        usd_egp = quotes.get("USDEGP", {}).get("end_rate")
        usd_aed = quotes.get("USDAED", {}).get("end_rate")

        if not usd_egp or not usd_aed:
            print("⚠️ Missing rate data in API response")
            return None, None

        usd_rate = round(float(usd_egp), 4)
        aed_rate = round(float(usd_egp) / float(usd_aed), 4)

        cache[today]["USD"] = usd_rate
        cache[today]["AED"] = aed_rate
        save_cache(cache, API_CACHE_FILE)
        print(f"✅ Updated official rates: USD={usd_rate}, AED={aed_rate}")
        return usd_rate, aed_rate
    except Exception as e:
        print("❌ Currency API error:", e)
    return None, None


# ----------------- Telegram handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    message = (
        "👋 Welcome to *CurrencyBot Egypt!*\n\n"
        "Use `/rate` to get 🇺🇸 USD & 🇦🇪 AED → 🇪🇬 EGP live rates.\n"
        f"Daily limit: {DAILY_LIMIT} requests per currency.\n"
    )
    if username == ADMIN_USERNAME:
        message += "\n🛠 Admin command: `/force_refresh` – clear cache and refresh data."
    await update.message.reply_text(message, parse_mode="Markdown")


async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not increment_usage("USD") or not increment_usage("AED"):
            await update.message.reply_text(
                "⚠️ *Daily query limit reached.* Please try again tomorrow."
            )
            return

        usd_market = get_sarf_today_rate("USD")
        aed_market = get_sarf_today_rate("AED")
        usd_official, aed_official = get_currencylayer_rates()

        message = "💱 *Live Exchange Rates*\n\n"

        # USD
        message += "🇺🇸 *USD → EGP*\n"
        if usd_market:
            message += f"  • Market: {usd_market:.2f} EGP\n"
        if usd_official:
            message += f"  • Official: {usd_official:.4f} EGP\n"
        message += "\n"

        # AED
        message += "🇦🇪 *AED → EGP*\n"
        if aed_market:
            message += f"  • Market: {aed_market:.2f} EGP\n"
        if aed_official:
            message += f"  • Official: {aed_official:.4f} EGP\n"
        message += "\n"

        message += "📝 Data sources: Sarf-Today (Market) & exchangerate.host/change (Official)"

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        print(f"❌ Error in /rate: {e}")
        try:
            await update.message.reply_text("⚠️ An error occurred while fetching rates.")
        except Exception:
            pass


# ----------------- Admin Command -----------------
async def force_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    if username != ADMIN_USERNAME:
        await update.message.reply_text("🚫 You are not authorized to run this command.")
        return

    for file in [CACHE_FILE, API_CACHE_FILE]:
        try:
            with open(file, "w") as f:
                json.dump({}, f)
            print(f"🧹 Cleared {file}")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to clear {file}: {e}")
            return

    get_sarf_today_rate("USD")
    get_sarf_today_rate("AED")
    get_currencylayer_rates()

    await update.message.reply_text("✅ Cache cleared and data refreshed successfully.")


# ----------------- Main -----------------
def main():
    ensure_cache_files()

    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set. Exiting...")
        return

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(20)
        .read_timeout(20)
        .write_timeout(20)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rate", rate))
    app.add_handler(CommandHandler("force_refresh", force_refresh))

    print("✅ Bot is running (polling mode, with extended timeout)...")
    app.run_polling()


if __name__ == "__main__":
    main()
