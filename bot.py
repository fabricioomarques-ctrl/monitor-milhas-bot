import os
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ["TELEGRAM_TOKEN"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✈️ Monitor de Milhas Ativo!\n\n"
        "Comandos:\n"
        "/promocoes - Buscar promoções de milhas"
    )

async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    url = "https://www.melhoresdestinos.com.br/tag/milhas"

    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    posts = soup.select("h2.entry-title a")

    resposta = "🔥 Promoções encontradas:\n\n"

    for post in posts[:5]:
        titulo = post.text
        link = post["href"]
        resposta += f"{titulo}\n{link}\n\n"

    await update.message.reply_text(resposta)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("promocoes", promocoes))

app.run_polling()
