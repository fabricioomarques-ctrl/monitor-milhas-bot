import os
import feedparser
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# RSS de sites de milhas
RSS_FEEDS = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://www.melhorescartoes.com.br/feed"
]

# ---------- COMANDOS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = """
✈️ Radar PRO de Milhas Ativo!

Comandos:

🔥 /promocoes – Promoções gerais  
💳 /transferencias – Transferência de pontos  
✈️ /passagens – Promoções de passagens
"""
    await update.message.reply_text(mensagem)


async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await enviar_promocoes(update)


async def transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await enviar_transferencias(update)


async def passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await enviar_passagens(update)


# ---------- BUSCA RSS ----------

async def enviar_promocoes(update):
    texto = "🔥 Promoções encontradas:\n\n"

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)

        for entry in feed.entries[:3]:
            texto += f"{entry.title}\n{entry.link}\n\n"

    await update.message.reply_text(texto)


async def enviar_transferencias(update):
    texto = "💳 Promoções de transferência:\n\n"

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:
            titulo = entry.title.lower()

            if "transfer" in titulo or "bônus" in titulo or "bonus" in titulo:
                texto += f"{entry.title}\n{entry.link}\n\n"

    if texto == "💳 Promoções de transferência:\n\n":
        texto += "Nenhuma promoção encontrada agora."

    await update.message.reply_text(texto)


async def enviar_passagens(update):
    texto = "✈️ Promoções de passagens:\n\n"

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:
            titulo = entry.title.lower()

            if "passagem" in titulo or "voo" in titulo or "milhas" in titulo:
                texto += f"{entry.title}\n{entry.link}\n\n"

    if texto == "✈️ Promoções de passagens:\n\n":
        texto += "Nenhuma promoção encontrada agora."

    await update.message.reply_text(texto)


# ---------- MONITOR AUTOMÁTICO ----------

async def monitorar(context: ContextTypes.DEFAULT_TYPE):

    texto = ""

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)

        for entry in feed.entries[:2]:

            titulo = entry.title.lower()

            if "100%" in titulo:
                texto += f"🚨 ALERTA MÁXIMO DE BÔNUS\n{entry.title}\n{entry.link}\n\n"

            elif "80%" in titulo or "90%" in titulo:
                texto += f"🔥 BÔNUS ALTO\n{entry.title}\n{entry.link}\n\n"

    if texto:
        await context.bot.send_message(chat_id=CHAT_ID, text=texto)


# ---------- INICIAR BOT ----------

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("promocoes", promocoes))
app.add_handler(CommandHandler("transferencias", transferencias))
app.add_handler(CommandHandler("passagens", passagens))

# JobQueue corrigido
job_queue = app.job_queue

job_queue.run_repeating(
    monitorar,
    interval=600,
    first=10
)

app.run_polling()
