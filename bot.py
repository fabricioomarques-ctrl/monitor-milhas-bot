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

    "bradesco",
    "itau",
    "c6",
    "nubank",

    "passagem",
    "milhas",
    "promoção",
    "resgate",
    "feirão",
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensagem = (
        "✈️ Radar de Milhas Ativo!\n\n"
        "Comandos:\n"
        "/promocoes - Buscar promoções agora\n"
        "/transferencias - Promoções de transferência\n"
        "/passagens - Promoções de passagens"
    )

    await update.message.reply_text(mensagem)


async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    resposta = "🔥 Promoções encontradas:\n\n"

    for site in sites:

        headers = {"User-Agent": "Mozilla/5.0"}

        response = requests.get(site, headers=headers)

        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.find_all("a")

        count = 0

        for link in links:

            titulo = link.text.strip()
            url = link.get("href")

            if not url:
                continue

            titulo_lower = titulo.lower()

            for palavra in palavras_chave:

                if palavra in titulo_lower:

                    if url.startswith("http"):

                        resposta += f"{titulo}\n{url}\n\n"

                        count += 1
                        break

            if count == 5:
                break

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

            titulo_lower = titulo.lower()

            for palavra in palavras_chave:

                if palavra in titulo_lower:

                    if url.startswith("http"):

                        if titulo != ULTIMO_ALERTA:

                            ULTIMO_ALERTA = titulo

                            mensagem = f"🚨 Nova promoção detectada!\n\n{titulo}\n{url}"

                            await context.bot.send_message(
                                chat_id=context.job.chat_id,
                                text=mensagem
                            )

                            return


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("promocoes", promocoes))

job_queue = app.job_queue

job_queue.run_repeating(
    monitorar,
    interval=600,
    first=10,
    chat_id=chat_id
)

app.run_polling()
