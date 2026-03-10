import os
import asyncio
import feedparser
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS_FEEDS = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://www.melhorescartoes.com.br/feed"
]

# ---------- COMANDOS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = """
✈️ Radar PRO de Milhas Ativo!

Comandos:

🔥 /promocoes
💳 /transferencias
✈️ /passagens
"""
    await update.message.reply_text(texto)


async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = "🔥 Promoções encontradas:\n\n"

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)

        for entry in feed.entries[:3]:
            texto += f"{entry.title}\n{entry.link}\n\n"

    await update.message.reply_text(texto)


async def transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = "💳 Promoções de transferência:\n\n"

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:

            titulo = entry.title.lower()

            if "transfer" in titulo or "bonus" in titulo or "bônus" in titulo:
                texto += f"{entry.title}\n{entry.link}\n\n"

    if texto == "💳 Promoções de transferência:\n\n":
        texto += "Nenhuma promoção encontrada."

    await update.message.reply_text(texto)


async def passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = "✈️ Promoções de passagens:\n\n"

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:

            titulo = entry.title.lower()

            if "passagem" in titulo or "voo" in titulo:
                texto += f"{entry.title}\n{entry.link}\n\n"

    if texto == "✈️ Promoções de passagens:\n\n":
        texto += "Nenhuma promoção encontrada."

    await update.message.reply_text(texto)


# ---------- MONITOR AUTOMÁTICO ----------

async def radar(context):

    while True:

        texto = ""

        for url in RSS_FEEDS:

            feed = feedparser.parse(url)

            for entry in feed.entries[:2]:

                titulo = entry.title.lower()

                if "100%" in titulo:
                    texto += f"🚨 BÔNUS 100% DETECTADO\n{entry.title}\n{entry.link}\n\n"

                elif "90%" in titulo or "80%" in titulo:
                    texto += f"🔥 BÔNUS ALTO\n{entry.title}\n{entry.link}\n\n"

        if texto:
            await context.bot.send_message(chat_id=CHAT_ID, text=texto)

        await asyncio.sleep(600)


# ---------- INICIAR BOT ----------

async def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("promocoes", promocoes))
    app.add_handler(CommandHandler("transferencias", transferencias))
    app.add_handler(CommandHandler("passagens", passagens))

    asyncio.create_task(radar(app))

    await app.run_polling()


asyncio.run(main())
