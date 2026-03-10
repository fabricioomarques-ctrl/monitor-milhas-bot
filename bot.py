import os
import feedparser
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# RSS monitorados

RSS_FEEDS = [

"https://www.melhoresdestinos.com.br/feed",
"https://passageirodeprimeira.com/feed",
"https://www.melhorescartoes.com.br/feed",
"https://passagensimperdiveis.com.br/feed"

]

# histórico anti duplicação
historico = set()

# palavras monitoradas

PROGRAMAS = [
"livelo",
"smiles",
"latam",
"azul",
"tudoazul"
]

BANCOS = [
"itau",
"itaú",
"bradesco",
"santander",
"banco do brasil"
]

BONUS = [
"100%",
"90%",
"85%",
"80%"
]

MILHEIRO = [
"milheiro",
"r$14",
"r$15",
"r$16"
]

ERRO = [
"erro tarifario",
"tarifa erro",
"passagem absurda"
]

# ============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (

"✈️ Radar de Milhas PRO+++\n\n"

"/menu\n"
"/promocoes\n"
"/transferencias\n"
"/passagens\n"
"/status\n"

)

    await update.message.reply_text(texto)

# ============================

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (

"📡 MENU RADAR\n\n"

"/promocoes\n"
"/transferencias\n"
"/passagens\n"
"/status"

)

    await update.message.reply_text(texto)

# ============================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (

"🟢 RADAR ATIVO\n\n"

"Monitorando:\n"

"Programas\n"
"Livelo\n"
"Smiles\n"
"LATAM Pass\n"
"TudoAzul\n\n"

"Bancos\n"
"Itaú\n"
"Bradesco\n"
"Santander\n"
"Banco do Brasil\n\n"

"Blogs de milhas"

)

    await update.message.reply_text(texto)

# ============================

async def transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (

"💳 Transferências monitoradas\n\n"

"Livelo → Smiles\n"
"Livelo → LATAM\n"
"Livelo → Azul\n\n"

"Bancos\n"
"Itaú\n"
"Bradesco\n"
"Santander\n"
"Banco do Brasil"

)

    await update.message.reply_text(texto)

# ============================

async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("🔎 Buscando promoções...")

# ============================

async def monitor(context: ContextTypes.DEFAULT_TYPE):

    for feed in RSS_FEEDS:

        noticias = feedparser.parse(feed)

        for post in noticias.entries[:5]:

            titulo = post.title
            link = post.link

            if titulo in historico:
                continue

            texto = titulo.lower()

            mensagem = None

            if any(p in texto for p in PROGRAMAS):

                mensagem = f"🚨 Promoção detectada\n\n{titulo}\n{link}"

            if any(b in texto for b in BONUS):

                mensagem = f"🔥 BÔNUS ALTO DETECTADO\n\n{titulo}\n{link}"

            if any(banco in texto for banco in BANCOS):

                mensagem = f"💳 Transferência de banco detectada\n\n{titulo}\n{link}"

            if any(m in texto for m in MILHEIRO):

                mensagem = f"💰 Milheiro barato\n\n{titulo}\n{link}"

            if any(e in texto for e in ERRO):

                mensagem = f"✈️ Possível erro tarifário\n\n{titulo}\n{link}"

            if mensagem:

                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=mensagem
                )

                historico.add(titulo)

                return

# ============================

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("promocoes", promocoes))
    app.add_handler(CommandHandler("transferencias", transferencias))

    job = app.job_queue

    job.run_repeating(
        monitor,
        interval=600,
        first=20
    )

    print("Radar PRO+++ iniciado")

    app.run_polling()

if __name__ == "__main__":
    main()
