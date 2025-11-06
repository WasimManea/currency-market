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


def get_usage_count(currency):
    """Return today's usage count for a currency."""
    today = datetime.date.today().isoformat()
    cache = load_cache(CACHE_FILE)
    return cache.get(today, {}).get(currency, 0)


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


# ----------------- API helpers -----------------
def get_sarf_today_rate(currency):
    """Always fetch market rate live (no caching)."""
    print(f"🌐 Fetching market rate for {currency} from Sarf-Today API...")
    try:
        response = requests.get(SARF_TODAY_URL, timeout=10)
        data = response.json()
        for item in data:
            if item["name"] == currency:
                rate = float(item["ask"])
                print(f"✅ Got live {currency} market rate: {rate}")
                return rate
        print(f"⚠️ Currency {currency} not found in Sarf-Today response.")
    except Exception as e:
        print("❌ Sarf-Today API error:", e)
    return None


def get_currencylayer_rates(force_live=False):
    """
    Fetch official rates using exchangerate.host/change.
    If force_live=False and limit exceeded, only use cache.
    """
    today = datetime.date.today().isoformat()
    cache = load_cache(API_CACHE_FILE)

    if today not in cache:
        cache[today] = {}

    # If user exceeded limit, use cache only
    usd_usage = get_usage_count("USD")
    aed_usage = get_usage_count("AED")

    if not force_live and (usd_usage >= DAILY_LIMIT or aed_usage >= DAILY_LIMIT):
        print("📦 Using cached official rates (limit exceeded).")
        return cache[today].get("USD"), cache[today].get("AED")

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
        message += "\n🛠 Admin commands:\n" \
                   "• `/force_refresh` – Clear cache and refresh data.\n" \
                   "• `/cashed` – View current cache file content."
    await update.message.reply_text(message, parse_mode="Markdown")


async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not increment_usage("USD") or not increment_usage("AED"):
            await update.message.reply_text(
                "⚠️ *Daily query limit reached.* Only cached official rates will be shown."
            )

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

        message += "📝 Data sources: Sarf-Today & CurrencyLayer"
        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        print(f"❌ Error in /rate: {e}")
        try:
            await update.message.reply_text("⚠️ An error occurred while fetching rates.")
        except Exception:
            pass


# ----------------- Admin Commands -----------------
async def force_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # 1️⃣ Delete cached file if exists
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            await update.message.reply_text("🧹 Old cache file deleted.")
        else:
            await update.message.reply_text("ℹ️ No cache file found to delete.")

        # 2️⃣ Recreate cache by calling your rate fetching logic
        await update.message.reply_text("🔄 Fetching fresh exchange rates...")

        # Example: if you already have a method to fetch and cache rates
        # Replace this with your actual function name
        if "get_exchange_rates" in globals():
            rates = await get_exchange_rates(force_refresh=True)
        elif "fetch_exchange_rates" in globals():
            rates = await fetch_exchange_rates(force_refresh=True)
        else:
            rates = None

        # 3️⃣ Confirm success
        if rates:
            await update.message.reply_text("✅ Cache cleared and refreshed successfully.")
        else:
            await update.message.reply_text("⚠️ Cache cleared, but failed to refresh rates.")

    except TimedOut:
        print("⚠️ Telegram API timed out while sending a message.")
    except Exception as e:
        print(f"❌ Error in force_refresh: {e}")
        try:
            await update.message.reply_text(f"❌ Error while refreshing: {e}")
        except:
            pass

async def cashed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    if username != ADMIN_USERNAME:
        await update.message.reply_text("🚫 You are not authorized to view the cache.")
        return

    cache_data = load_cache(API_CACHE_FILE)
    if not cache_data:
        await update.message.reply_text("📭 Cache file is empty.")
        return

    formatted = json.dumps(cache_data, indent=2)
    await update.message.reply_text(f"🗂 *Current Cached Data:*\n```\n{formatted}\n```", parse_mode="Markdown")


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
    app.add_handler(CommandHandler("cashed", cashed))

    print("✅ Bot is running (polling mode, with extended timeout)...")
    app.run_polling()


if __name__ == "__main__":
    main()
