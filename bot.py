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
from telegram.ext import JobQueue

ULTIMA_PROMO = ""

async def monitorar_promocoes(context: ContextTypes.DEFAULT_TYPE):

    global ULTIMA_PROMO

    url = "https://www.melhoresdestinos.com.br/"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    posts = soup.find_all("a")

    for post in posts:
        titulo = post.text.strip()
        link = post.get("href")

        if not link:
            continue

        if "milhas" in titulo.lower() or "livelo" in titulo.lower():

            if link.startswith("http"):

                if titulo != ULTIMA_PROMO:

                    ULTIMA_PROMO = titulo

                    mensagem = f"🚨 Nova promoção detectada!\n\n{titulo}\n{link}"

                    await context.bot.send_message(
                        chat_id=context.job.chat_id,
                        text=mensagem
                    )

                break
                chat_id = 5006505664

job_queue = app.job_queue

job_queue.run_repeating(
    monitorar_promocoes,
    interval=1800,
    first=10,
    chat_id=chat_id
)
app.run_polling()
