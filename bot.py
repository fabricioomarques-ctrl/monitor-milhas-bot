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

    url = "https://www.melhoresdestinos.com.br/"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    posts = soup.find_all("a")

    resposta = "🔥 Promoções encontradas:\n\n"

    count = 0

    for post in posts:
        titulo = post.text.strip()
        link = post.get("href")

        if "milhas" in titulo.lower() or "passagem" in titulo.lower():

            if link.startswith("http"):
                resposta += f"{titulo}\n{link}\n\n"
                count += 1

        if count == 5:
            break

    if count == 0:
        resposta += "Nenhuma promoção encontrada agora."

    await update.message.reply_text(resposta)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("promocoes", promocoes))

app.run_polling()
