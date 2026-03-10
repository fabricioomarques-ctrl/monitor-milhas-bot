import os
import feedparser
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")

RSS_FEEDS = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://www.melhorescartoes.com.br/feed"
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✈️ Radar de Milhas ativo!")

async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = "🔥 Promoções encontradas:\n\n"

    for url in RSS_FEEDS:

        feed = feedparser.parse(url)

        for entry in feed.entries[:3]:

            texto += f"{entry.title}\n{entry.link}\n\n"

    await update.message.reply_text(texto)

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("promocoes", promocoes))

    print("Bot iniciado...")

    app.run_polling()

if __name__ == "__main__":
    main()
