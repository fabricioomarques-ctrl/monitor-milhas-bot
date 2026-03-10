import os
import requests
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
        "✈️ Radar PRO de Milhas Ativo!\n\n"
        "Comandos:\n\n"
        "🔥 /promocoes - Promoções gerais\n"
        "💳 /transferencias - Transferência de pontos\n"
        "✈️ /passagens - Promoções de passagens"
    )

    await update.message.reply_text(mensagem)


async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    resposta = "🔥 Promoções encontradas:\n\n"

    for site in sites:

        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(site, headers=headers)

        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.find_all("a")

        for link in links:

            titulo = link.text.strip()
            url = link.get("href")

            if not url:
                continue

            titulo_lower = titulo.lower()

            if any(p in titulo_lower for p in palavras_chave):

                if url.startswith("http"):

                    resposta += f"{titulo}\n{url}\n\n"

    await update.message.reply_text(resposta)


async def transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):

    resposta = "💳 Promoções de transferência:\n\n"

    for site in sites:

        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(site, headers=headers)

        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.find_all("a")

        for link in links:

            titulo = link.text.strip()
            url = link.get("href")

            if not url:
                continue

            titulo_lower = titulo.lower()

            if "transfer" in titulo_lower or "livelo" in titulo_lower:

                if url.startswith("http"):

                    resposta += f"{titulo}\n{url}\n\n"

    await update.message.reply_text(resposta)


async def passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):

    resposta = "✈️ Promoções de passagens:\n\n"

    for site in sites:

        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(site, headers=headers)

        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.find_all("a")

        for link in links:

            titulo = link.text.strip()
            url = link.get("href")

            if not url:
                continue

            titulo_lower = titulo.lower()

            if "passagem" in titulo_lower:

                if url.startswith("http"):

                    resposta += f"{titulo}\n{url}\n\n"

    await update.message.reply_text(resposta)


async def monitorar(context: ContextTypes.DEFAULT_TYPE):

    global ULTIMO_ALERTA

    for site in sites:

        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(site, headers=headers)

        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.find_all("a")

        for link in links:

            titulo = link.text.strip()
            url = link.get("href")

            if not url:
                continue

            if titulo == ULTIMO_ALERTA:
                continue

            if any(bonus in titulo for bonus in bonus_maximo):

                ULTIMO_ALERTA = titulo

                mensagem = f"🚨 ALERTA MÁXIMO DE BÔNUS\n\n{titulo}\n{url}"

                await context.bot.send_message(chat_id=context.job.chat_id, text=mensagem)

                return

            if any(bonus in titulo for bonus in bonus_alto):

                ULTIMO_ALERTA = titulo

                mensagem = f"🔥 BÔNUS ALTO DETECTADO\n\n{titulo}\n{url}"

                await context.bot.send_message(chat_id=context.job.chat_id, text=mensagem)

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
