import os
import feedparser
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS_FEEDS = [

"https://www.melhoresdestinos.com.br/feed",
"https://passageirodeprimeira.com/feed",
"https://www.melhorescartoes.com.br/feed",
"https://passagensimperdiveis.com.br/feed"

]

ULTIMA_PROMO = ""

# PALAVRAS CHAVE

BONUS_ALERTA = ["100%", "90%", "85%", "80%"]

PROGRAMAS = [

"livelo",
"smiles",
"latam",
"azul",
"tudoazul"

]

ERRO_TARIFARIO = [

"erro tarifario",
"tarifa erro",
"passagem absurda"

]

MILHEIRO = [

"milheiro",
"R$14",
"R$15",
"R$16"

]

# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (

"✈️ Radar de Milhas PRO++\n\n"

"/menu\n"
"/promocoes\n"
"/transferencias\n"
"/passagens\n"
"/status\n"

)

    await update.message.reply_text(texto)

# ==========================

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (

"📡 MENU RADAR\n\n"

"/promocoes\n"
"/transferencias\n"
"/passagens\n"
"/status"

)

    await update.message.reply_text(texto)

# ==========================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (

"🟢 RADAR ONLINE\n\n"

"Monitorando:\n"

"• Blogs de milhas\n"
"• Livelo\n"
"• Smiles\n"
"• LATAM Pass\n"
"• Azul\n"

)

    await update.message.reply_text(texto)

# ==========================

async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = "🔎 Buscando promoções recentes..."

    await update.message.reply_text(texto)

# ==========================

async def monitor(context: ContextTypes.DEFAULT_TYPE):

    global ULTIMA_PROMO

    for feed in RSS_FEEDS:

        noticias = feedparser.parse(feed)

        for post in noticias.entries[:5]:

            titulo = post.title
            link = post.link

            if titulo == ULTIMA_PROMO:
                continue

            texto = titulo.lower()

            if any(p in texto for p in PROGRAMAS):

                mensagem = f"🚨 Promoção detectada\n\n{titulo}\n{link}"

                if any(b in texto for b in BONUS_ALERTA):

                    mensagem = f"🔥 BÔNUS ALTO DETECTADO\n\n{titulo}\n{link}"

                if any(m in texto for m in MILHEIRO):

                    mensagem = f"💰 MILHEIRO BARATO\n\n{titulo}\n{link}"

                if any(e in texto for e in ERRO_TARIFARIO):

                    mensagem = f"✈️ ERRO TARIFÁRIO\n\n{titulo}\n{link}"

                await context.bot.send_message(

chat_id=CHAT_ID,
text=mensagem

)

                ULTIMA_PROMO = titulo

                return

# ==========================

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("promocoes", promocoes))

    job = app.job_queue

    job.run_repeating(

monitor,
interval=600,
first=30

)

    print("Radar PRO++ iniciado")

    app.run_polling()

if __name__ == "__main__":
    main()
