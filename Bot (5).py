from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import random

BOT_TOKEN = "8358410115:AAF6mtD7Mw1YEn6LNWdEJr6toCubTOz3NLg"  # Aapka token

async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Example: /add 415")
        return

    amount = context.args[0]

    # Escrower = command run karne wala
    escrower = f"@{update.message.from_user.username}" if update.message.from_user.username else "Unknown"

    # Buyer = jis message pe reply kiya (nahi to Unknown)
    buyer = "Unknown"
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        buyer = f"@{user.username}" if user.username else "Unknown"

    seller = escrower  # Seller = Escrower
    trade_id = f"#TID{random.randint(100000, 999999)}"

    msg = (
        f"RECEIVED AMOUNT : {amount}\n"
        f"TRADE ID : {trade_id}\n\n"
        f"BUYER : {buyer}\n"
        f"SELLER : {seller}\n"
        f"ESCROWED BY : {escrower}"
    )
    await update.message.reply_text(msg)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", add_deal))
    app.run_polling()

if __name__ == "__main__":
    main()
