import os
import feedparser
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# RSS feeds
RSS_PROMOCOES = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://www.melhorescartoes.com.br/feed"
]

RSS_TRANSFERENCIAS = [
    "https://www.melhorescartoes.com.br/tag/transferencia-bonificada/feed",
    "https://passageirodeprimeira.com/tag/transferencia-bonificada/feed"
]

RSS_PASSAGENS = [
    "https://www.melhoresdestinos.com.br/categoria/promocao-passagem/feed"
]

# evitar duplicados
enviados = set()

# menu
menu = ReplyKeyboardMarkup(
    [
        ["🔥 Promoções", "💳 Transferências"],
        ["✈️ Passagens"]
    ],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "✈️ Radar PRO de Milhas Ativo!\n\n"
        "Comandos:\n"
        "🔥 /promocoes\n"
        "💳 /transferencias\n"
        "✈️ /passagens"
    )
    await update.message.reply_text(texto, reply_markup=menu)

async def buscar_rss(feeds):

    resultados = []

    for url in feeds:
        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:
            titulo = entry.title
            link = entry.link

            if link not in enviados:
                enviados.add(link)
                resultados.append(f"{titulo}\n{link}")

    return resultados

async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dados = await buscar_rss(RSS_PROMOCOES)

    if not dados:
        await update.message.reply_text("Nenhuma promoção nova.")
        return

    texto = "🔥 Promoções encontradas:\n\n"
    texto += "\n\n".join(dados[:5])

    await update.message.reply_text(texto)

async def transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dados = await buscar_rss(RSS_TRANSFERENCIAS)

    if not dados:
        await update.message.reply_text("Nenhuma transferência nova.")
        return

    texto = "💳 Transferências bonificadas:\n\n"
    texto += "\n\n".join(dados[:5])

    await update.message.reply_text(texto)

async def passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dados = await buscar_rss(RSS_PASSAGENS)

    if not dados:
        await update.message.reply_text("Nenhuma promoção de passagem.")
        return

    texto = "✈️ Promoções de passagens:\n\n"
    texto += "\n\n".join(dados[:5])

    await update.message.reply_text(texto)

async def monitorar(context: ContextTypes.DEFAULT_TYPE):

    bot = context.bot

    dados = await buscar_rss(RSS_PROMOCOES + RSS_TRANSFERENCIAS + RSS_PASSAGENS)

    for item in dados:

        alerta = item

        if "100%" in item or "90%" in item or "80%" in item:
            alerta = "🚨 BÔNUS ALTO DETECTADO!\n\n" + item

        await bot.send_message(chat_id=CHAT_ID, text=alerta)

async def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("promocoes", promocoes))
    app.add_handler(CommandHandler("transferencias", transferencias))
    app.add_handler(CommandHandler("passagens", passagens))

    job = app.job_queue
    job.run_repeating(monitorar, interval=600, first=10)

    print("Radar PRO iniciado")

    app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
