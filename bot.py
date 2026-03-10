import os
import requests
import feedparser
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ["TELEGRAM_TOKEN"]
chat_id = 5006505664

ULTIMO_ALERTA = ""

sites = [
    "https://www.melhoresdestinos.com.br/",
    "https://passageirodeprimeira.com/",
    "https://www.melhorescartoes.com.br/"
]

rss_feeds = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://www.melhorescartoes.com.br/feed"
]

palavras_chave = [
    "livelo",
    "transfer",
    "transferência",
    "bônus",
    "latam pass",
    "tudoazul",
    "smiles",
    "latam",
    "azul",
    "gol",
    "passagem",
    "milhas",
    "promoção"
]

bonus_maximo = ["100%", "110%", "120%"]
bonus_alto = ["80%", "90%"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensagem = (
        "✈️ Radar PRO+ de Milhas Ativo!\n\n"
        "Comandos:\n\n"
        "🔥 /promocoes - Promoções gerais\n"
        "💳 /transferencias - Transferência de pontos\n"
        "✈️ /passagens - Promoções de passagens"
    )

    await update.message.reply_text(mensagem)


async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    resposta = "🔥 Promoções encontradas:\n\n"

    for feed_url in rss_feeds:

        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:5]:

            titulo = entry.title
            link = entry.link

            if any(p in titulo.lower() for p in palavras_chave):

                resposta += f"{titulo}\n{link}\n\n"

    await update.message.reply_text(resposta)


async def transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):

    resposta = "💳 Promoções de transferência:\n\n"

    for feed_url in rss_feeds:

        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:5]:

            titulo = entry.title.lower()

            if "transfer" in titulo or "livelo" in titulo:

                resposta += f"{entry.title}\n{entry.link}\n\n"

    await update.message.reply_text(resposta)


async def passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):

    resposta = "✈️ Promoções de passagens:\n\n"

    for feed_url in rss_feeds:

        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:5]:

            titulo = entry.title.lower()

            if "passagem" in titulo:

                resposta += f"{entry.title}\n{entry.link}\n\n"

    await update.message.reply_text(resposta)


async def monitorar(context: ContextTypes.DEFAULT_TYPE):

    global ULTIMO_ALERTA

    for feed_url in rss_feeds:

        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:5]:

            titulo = entry.title
            link = entry.link

            if titulo == ULTIMO_ALERTA:
                continue

            if any(b in titulo for b in bonus_maximo):

                ULTIMO_ALERTA = titulo

                await context.bot.send_message(
                    chat_id=context.job.chat_id,
                    text=f"🚨 ALERTA MÁXIMO DE BÔNUS\n\n{titulo}\n{link}"
                )

                return

            if any(b in titulo for b in bonus_alto):

                ULTIMO_ALERTA = titulo

                await context.bot.send_message(
                    chat_id=context.job.chat_id,
                    text=f"🔥 BÔNUS ALTO DETECTADO\n\n{titulo}\n{link}"
                )

                return


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("promocoes", promocoes))
app.add_handler(CommandHandler("transferencias", transferencias))
app.add_handler(CommandHandler("passagens", passagens))

job_queue = app.job_queue

job_queue.run_repeating(
    monitorar,
    interval=600,
    first=10,
    chat_id=chat_id
)

app.run_polling()
