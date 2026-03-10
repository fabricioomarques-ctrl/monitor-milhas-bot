import os
import json
import feedparser
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS_FEEDS = [
"https://www.melhoresdestinos.com.br/feed",
"https://passageirodeprimeira.com/feed",
"https://pontospravoar.com/feed",
"https://estevaopelomundo.com.br/feed"
]

PROGRAMAS = ["livelo","smiles","latam","tudoazul","azul"]
BANCOS = ["itau","itaú","bradesco","santander","banco do brasil","c6","inter"]
BONUS = ["100%","90%","85%","80%"]
MILHEIRO = ["milheiro","r$14","r$15","r$16","r$17"]
ERRO = ["erro tarifario","tarifa erro","passagem absurda"]

ARQUIVO = "promocoes_enviadas.json"

def carregar_historico():
    try:
        with open(ARQUIVO,"r") as f:
            return json.load(f)
    except:
        return []

def salvar_historico(data):
    with open(ARQUIVO,"w") as f:
        json.dump(data,f)

historico = carregar_historico()
ranking = {}

# ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (
"✈️ Radar de Milhas PRO+++\n\n"
"/menu\n"
"/promocoes\n"
"/transferencias\n"
"/passagens\n"
"/ranking\n"
"/status"
)

    await update.message.reply_text(texto)

# ------------------

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (
"📡 MENU RADAR\n\n"
"/promocoes\n"
"/transferencias\n"
"/passagens\n"
"/ranking\n"
"/status"
)

    await update.message.reply_text(texto)

# ------------------

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (
"🟢 RADAR ONLINE\n\n"
"Monitorando:\n"
"Blogs de milhas\n"
"Programas de pontos\n"
"Bancos\n\n"
"Promoções detectadas hoje: "
+ str(len(ranking))
)

    await update.message.reply_text(texto)

# ------------------

async def ranking_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not ranking:
        await update.message.reply_text("Nenhuma promoção detectada ainda hoje.")
        return

    texto = "🏆 Ranking de promoções do dia\n\n"

    ordenado = sorted(ranking.items(), key=lambda x: x[1], reverse=True)

    pos = 1

    for titulo,score in ordenado[:5]:

        texto += f"{pos}️⃣ {titulo}\n"

        pos += 1

    await update.message.reply_text(texto)

# ------------------

async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("🔎 Radar verificando promoções...")

# ------------------

async def transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (
"💳 Monitorando transferências bonificadas\n\n"
"Livelo\n"
"Smiles\n"
"LATAM Pass\n"
"TudoAzul\n\n"
"Bancos\n"
"Itaú\n"
"Bradesco\n"
"Santander\n"
"Banco do Brasil\n"
"C6\n"
"Inter"
)

    await update.message.reply_text(texto)

# ------------------

async def passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (
"✈️ Monitor de passagens ativo\n\n"
"Detectando:\n"
"Erro tarifário\n"
"Promoções relâmpago\n"
"Milheiro barato"
)

    await update.message.reply_text(texto)

# ------------------

def pontuar(texto):

    score = 1

    if any(b in texto for b in BONUS):
        score += 5

    if any(m in texto for m in MILHEIRO):
        score += 3

    if any(e in texto for e in ERRO):
        score += 4

    return score

# ------------------

async def monitor(context: ContextTypes.DEFAULT_TYPE):

    global historico

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

                mensagem = f"💳 Transferência detectada\n\n{titulo}\n{link}"

            if any(m in texto for m in MILHEIRO):

                mensagem = f"💰 Milheiro barato\n\n{titulo}\n{link}"

            if any(e in texto for e in ERRO):

                mensagem = f"✈️ POSSÍVEL ERRO TARIFÁRIO\n\n{titulo}\n{link}"

            if mensagem:

                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=mensagem
                )

                historico.append(titulo)
                salvar_historico(historico)

                ranking[titulo] = pontuar(texto)

                return

# ------------------

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("ranking", ranking_cmd))
    app.add_handler(CommandHandler("promocoes", promocoes))
    app.add_handler(CommandHandler("transferencias", transferencias))
    app.add_handler(CommandHandler("passagens", passagens))

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
