import re
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "6098583669:AAE64kFMI_JE6BpgUKyBszq13LdvTgfnsjY"

# TonAPI + CoinGecko endpoints
TON_RATE_API = "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd"
TON_API_BASE = "https://tonapi.io/v2"

# -------- Fetch NFT Data --------
def fetch_nft_data(collection_address: str):
    # TON → USD
    ton_price = requests.get(TON_RATE_API).json()['the-open-network']['usd']

    # Collection stats
    stats_url = f"{TON_API_BASE}/nft/collections/{collection_address}/stats"
    stats = requests.get(stats_url).json()

    if "floor_price" not in stats:
        return None

    floor_ton = stats.get("floor_price", 0)/1e9
    avg_ton = stats.get("average_price", 0)/1e9
    last_sale_ton = stats.get("last_sale_price", 0)/1e9

    # Recent 5 sales
    history_url = f"{TON_API_BASE}/nft/collections/{collection_address}/sales?limit=5"
    history_data = requests.get(history_url).json().get("sales", [])

    history = []
    for s in history_data:
        token = s.get("nft", {}).get("address", "Unknown")
        price_ton = s.get("price", 0)/1e9
        date = s.get("timestamp", "")[:10]
        history.append((token[-6:], price_ton, date))

    return {
        "floor": floor_ton,
        "avg": avg_ton,
        "last": last_sale_ton,
        "history": history,
        "ton_usd": ton_price
    }

# -------- Format Reply --------
def format_nft_reply(collection, nft_data):
    msg = f"""
🖼 Collection: {collection}

💰 Floor: {nft_data['floor']:.2f} TON ≈ ${nft_data['floor']*nft_data['ton_usd']:.2f}
📊 AVG: {nft_data['avg']:.2f} TON ≈ ${nft_data['avg']*nft_data['ton_usd']:.2f}
🕒 Last sale: {nft_data['last']:.2f} TON ≈ ${nft_data['last']*nft_data['ton_usd']:.2f}

📜 Recent sales (5):
"""
    for h in nft_data['history']:
        msg += f"{h[0]} → {h[1]:.2f} TON — {h[2]}\n"

    return msg

# -------- Command: /nft --------
async def nft_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /nft <collection_address>")
        return

    collection = context.args[0]
    nft_data = fetch_nft_data(collection)
    if not nft_data:
        await update.message.reply_text("❌ Collection not found or API error.")
        return

    msg = format_nft_reply(collection, nft_data)
    await update.message.reply_text(msg)

# -------- Auto Detect NFT Links --------
async def nft_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    match = re.search(r't\.me/nft/([A-Za-z0-9\-]+)', text)
    if not match:
        return

    collection_slug = match.group(1).split("-")[0]  # "EternalRose-5170" -> "EternalRose"
    collection_address = collection_slug  # Map slug to collection address in real scenario

    nft_data = fetch_nft_data(collection_address)
    if nft_data:
        msg = format_nft_reply(collection_slug, nft_data)
        await update.message.reply_text(msg)

# -------- Start Bot --------
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("nft", nft_price))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, nft_link_handler))

print("🚀 TON NFT Price Bot Running...")
app.run_polling()
