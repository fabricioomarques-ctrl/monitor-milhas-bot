import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✈️ Monitor de Milhas ativo!")

async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Monitorando promoções de milhas...")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("promocoes", promocoes))

app.run_polling()
