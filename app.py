import os
import json
import asyncio
from datetime import datetime
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================== CONFIG ==================
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
RAILWAY_PUBLIC_DOMAIN = os.environ["RAILWAY_STATIC_URL"]
PORT = int(os.environ["PORT"])
CACHE_FILE = "cached_rate.json"

SARF_API = "https://sarf-today.com/app_api/cur_market.json"
EXCHANGE_API = "https://api.exchangerate.host/change?currencies=AED,EGP&access_key=YOUR_ACCESS_KEY"

MAX_DAILY_CALLS = 3
# ============================================

async def fetch_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=10) as resp:
            return await resp.json()

async def get_cached_rate():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

async def save_cached_rate(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

async def get_exchange_rate():
    cache = await get_cached_rate()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Check if we already called API max times today
    if cache.get("date") == today and cache.get("calls", 0) >= MAX_DAILY_CALLS:
        return cache.get("rate"), cache.get("source_date")
    
    try:
        data = await fetch_json(EXCHANGE_API)
        if data.get("success"):
            rate_usd = data["quotes"]["USDEGP"]["end_rate"]
            rate_aed = data["quotes"]["USDAED"]["end_rate"]
            
            cache.update({
                "date": today,
                "calls": cache.get("calls", 0) + 1,
                "rate": {"USD": rate_usd, "AED": rate_aed},
                "source_date": today
            })
            await save_cached_rate(cache)
            return cache["rate"], today
    except:
        pass
    
    # fallback to Sarf-Today
    sarf_data =_
