import os
import feedparser
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

PROMO_FEEDS = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://www.melhorescartoes.com.br/feed"
]

TRANSFER_FEEDS = [
    "https://www.melhorescartoes.com.br/tag/transferencia-bonificada/feed",
    "https://passageirodeprimeira.com/tag/transferencia-bonificada/feed"
]

PASSAGEM_FEEDS = [
    "https://www.melhoresdestinos.com.br/categoria/promocao-passagem/feed"
]

enviados = set()

menu = ReplyKeyboardMarkup(
    [
        ["🔥 Promoções", "💳 Transferências"],
        ["✈️ Passagens"]
    ],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (
        "✈️ Radar PRO+ de Milhas\n\n"
        "Comandos disponíveis:\n"
        "/promocoes\n"
        "/transferencias\n"
        "/passagens"
    )

    await update.message.reply_text(texto, reply_markup=menu)

async def buscar(feeds):

    resultados = []

    for url in feeds:

        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:

            titulo = entry.title
            link = entry.link

            if link not in enviados:
                enviados.add(link)
                resultados.append((titulo, link))

    return resultados

async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dados = await buscar(PROMO_FEEDS)

    texto = "🔥 Promoções encontradas:\n\n"

    for titulo, link in dados[:5]:
        texto += f"{titulo}\n{link}\n\n"

    await update.message.reply_text(texto)

async def transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dados = await buscar(TRANSFER_FEEDS)

    texto = "💳 Transferências bonificadas:\n\n"

    for titulo, link in dados[:5]:
        texto += f"{titulo}\n{link}\n\n"

    await update.message.reply_text(texto)

async def passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dados = await buscar(PASSAGEM_FEEDS)

    texto = "✈️ Promoções de passagens:\n\n"

    for titulo, link in dados[:5]:
        texto += f"{titulo}\n{link}\n\n"

    await update.message.reply_text(texto)

async def monitorar(context: ContextTypes.DEFAULT_TYPE):

    bot = context.bot

    dados = await buscar(PROMO_FEEDS + TRANSFER_FEEDS + PASSAGEM_FEEDS)

    for titulo, link in dados:

        alerta = f"{titulo}\n{link}"

        if "100%" in titulo:
            alerta = f"🚨 BÔNUS 100% DETECTADO\n\n{alerta}"

        elif "90%" in titulo or "80%" in titulo:
            alerta = f"🔥 BÔNUS ALTO\n\n{alerta}"

        await bot.send_message(chat_id=CHAT_ID, text=alerta)

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("promocoes", promocoes))
    app.add_handler(CommandHandler("transferencias", transferencias))
    app.add_handler(CommandHandler("passagens", passagens))

    job = app.job_queue
    job.run_repeating(monitorar, interval=600, first=10)

    print("Radar PRO+ iniciado")

    app.run_polling()

if __name__ == "__main__":
    main()
