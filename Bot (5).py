import asyncio
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from web3 import Web3

# ================== BOT CONFIG ==================
BOT_TOKEN = "6098583669:AAE64kFMI_JE6BpgUKyBszq13LdvTgfnsjY"
MASTER_GROUP_ID = -1001234567890  # Apna master private group ID (bot admin hona chahiye)

# ================== BSC CONFIG ==================
BSC_RPC = "https://bsc-dataseed.binance.org/"
ESCROW_PRIVATE_KEY = "YOUR_ESCROW_WALLET_PRIVATE_KEY"
ESCROW_ADDRESS = "0xYourEscrowWallet"
USDT_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"  # BSC USDT Contract

w3 = Web3(Web3.HTTPProvider(BSC_RPC))
usdt_contract = w3.eth.contract(
    address=Web3.to_checksum_address(USDT_CONTRACT),
    abi=[{
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }]
)

# ================== DEAL STORAGE ==================
deals = {}  # chat_id -> {"buyer":addr,"seller":addr,"amount":float,"paid":bool,"start_balance":int}


async def start_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Create invite link valid for 2 users
    link = await context.bot.create_chat_invite_link(
        chat_id=MASTER_GROUP_ID,
        name=f"Deal_{user.id}",
        member_limit=2
    )

    # Record starting USDT balance
    start_balance = usdt_contract.functions.balanceOf(ESCROW_ADDRESS).call()

    deals[link.invite_link] = {
        "buyer": None,
        "seller": None,
        "amount": None,
        "paid": False,
        "start_balance": start_balance
    }

    await update.message.reply_text(
        f"✅ Private Deal Room Created!\n\n"
        f"🔹 Buyer & Seller join here: {link.invite_link}\n"
        f"💰 Send USDT (BEP20) to Escrow: `{ESCROW_ADDRESS}`\n\n"
        f"Buyer set: `/buyer <USDT_address>`\n"
        f"Seller set: `/seller <USDT_address>`\n"
        f"Release fund: `/release <amount>`\n\n"
        f"Bot will auto-check payment..."
    )


async def set_buyer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.chat.invite_link or "manual"
    if link not in deals:
        return await update.message.reply_text("❌ No active deal here.")
    deals[link]["buyer"] = context.args[0]
    await update.message.reply_text(f"✅ Buyer USDT Address set: {context.args[0]}")


async def set_seller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.chat.invite_link or "manual"
    if link not in deals:
        return await update.message.reply_text("❌ No active deal here.")
    deals[link]["seller"] = context.args[0]
    await update.message.reply_text(f"✅ Seller USDT Address set: {context.args[0]}")


async def release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.chat.invite_link or "manual"
    if link not in deals:
        return await update.message.reply_text("❌ No active deal here.")

    deal = deals[link]
    if not deal["seller"]:
        return await update.message.reply_text("❌ Seller address not set.")
    if not deal["paid"]:
        return await update.message.reply_text("❌ Payment not detected yet.")

    seller = deal["seller"]
    amount = float(context.args[0])
    amount_wei = int(amount * 10**18)

    nonce = w3.eth.get_transaction_count(ESCROW_ADDRESS)
    txn = usdt_contract.functions.transfer(
        Web3.to_checksum_address(seller), amount_wei
    ).build_transaction({
        'chainId': 56,
        'gas': 100000,
        'gasPrice': w3.to_wei('5', 'gwei'),
        'nonce': nonce
    })

    signed_txn = w3.eth.account.sign_transaction(txn, private_key=ESCROW_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

    await update.message.reply_text(
        f"✅ {amount} USDT Released to Seller!\n"
        f"🔹 Tx Hash: {tx_hash.hex()}"
    )


# Background task to check USDT payments
async def payment_checker(app: Application):
    while True:
        for link, deal in list(deals.items()):
            if not deal["paid"]:
                current_balance = usdt_contract.functions.balanceOf(ESCROW_ADDRESS).call()
                if current_balance > deal["start_balance"]:
                    deal["paid"] = True
                    # Notify in master group
                    try:
                        await app.bot.send_message(
                            chat_id=MASTER_GROUP_ID,
                            text=f"✅ Payment detected for deal {link}!\nBuyer can /release now."
                        )
                    except:
                        pass
        await asyncio.sleep(30)  # check every 30 sec


async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("startdeal", start_deal))
    app.add_handler(CommandHandler("buyer", set_buyer))
    app.add_handler(CommandHandler("seller", set_seller))
    app.add_handler(CommandHandler("release", release))

    # Start background payment checker
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(payment_checker(app)), 30)

    print("🤖 Bot Started with Auto Payment Check...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
