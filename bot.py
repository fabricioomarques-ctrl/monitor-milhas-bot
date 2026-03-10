import os
import requests
import feedparser
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# RSS monitorados
RSS_FEEDS = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://www.melhorescartoes.com.br/feed"
]

ULTIMO_POST = ""

# =============================
# COMANDOS
# =============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensagem = (
        "✈️ Radar de Milhas PRO+ ativo\n\n"
        "Comandos disponíveis:\n"
        "/menu\n"
        "/promocoes\n"
        "/transferencias\n"
        "/passagens"
    )

    await update.message.reply_text(mensagem)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensagem = (
        "📡 MENU RADAR\n\n"
        "✈️ /promocoes\n"
        "🔄 /transferencias\n"
        "🛫 /passagens"
    )

    await update.message.reply_text(mensagem)


# =============================
# PROMOÇÕES GERAIS
# =============================

async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    url = "https://www.melhoresdestinos.com.br/"

    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.text, "html.parser")

    links = soup.find_all("a")

    resposta = "🔥 Promoções encontradas:\n\n"

    count = 0

    for link in links:

        titulo = link.text.strip()
        href = link.get("href")

        if not href:
            continue

        if "milhas" in titulo.lower() or "passagem" in titulo.lower():

            if href.startswith("http"):

                resposta += f"{titulo}\n{href}\n\n"

                count += 1

        if count == 5:
            break

    if count == 0:
        resposta += "Nenhuma promoção encontrada."

    await update.message.reply_text(resposta)


# =============================
# TRANSFERÊNCIAS
# =============================

async def transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):

    resposta = (
        "🔄 Monitorando transferências:\n\n"
        "• Livelo\n"
        "• LATAM Pass\n"
        "• Smiles\n"
        "• TudoAzul\n\n"
        "Use /promocoes para ver ofertas atuais."
    )

    await update.message.reply_text(resposta)


# =============================
# PASSAGENS
# =============================

async def passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):

    resposta = (
        "🛫 Buscando promoções de passagens...\n\n"
        "Sites monitorados:\n"
        "Melhores Destinos\n"
        "Passageiro de Primeira\n"
        "Melhores Cartões"
    )

    await update.message.reply_text(resposta)


# =============================
# MONITOR RSS AUTOMÁTICO
# =============================

async def monitorar(context: ContextTypes.DEFAULT_TYPE):

    global ULTIMO_POST

    for feed in RSS_FEEDS:

        noticias = feedparser.parse(feed)

        for entry in noticias.entries[:3]:

            titulo = entry.title
            link = entry.link

            if titulo == ULTIMO_POST:
                continue

            texto = titulo.lower()

            if (
                "livelo" in texto
                or "milhas" in texto
                or "passagem" in texto
                or "latam" in texto
                or "smiles" in texto
                or "azul" in texto
            ):

                mensagem = f"🚨 Nova promoção detectada!\n\n{titulo}\n{link}"

                if "100%" in texto or "90%" in texto or "80%" in texto:

                    mensagem = (
                        "🔥 ALERTA DE BÔNUS ALTO!\n\n"
                        f"{titulo}\n{link}"
                    )

                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=mensagem
                )

                ULTIMO_POST = titulo
                return


# =============================
# MAIN
# =============================

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("promocoes", promocoes))
    app.add_handler(CommandHandler("transferencias", transferencias))
    app.add_handler(CommandHandler("passagens", passagens))

    job = app.job_queue

    job.run_repeating(
        monitorar,
        interval=600,
        first=20
    )

    print("Radar de Milhas PRO+ iniciado")

    app.run_polling()


if __name__ == "__main__":
    main()
