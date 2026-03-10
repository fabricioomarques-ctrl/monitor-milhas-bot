import os
import json
import feedparser
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ARQUIVO = "promocoes_enviadas.json"

# -----------------------------
# SITES RSS (BLOGS)
# -----------------------------

RSS_FEEDS = [

"https://www.melhoresdestinos.com.br/feed",
"https://passageirodeprimeira.com/feed",
"https://pontospravoar.com/feed",
"https://estevaopelomundo.com.br/feed"

]

# -----------------------------
# SITES OFICIAIS PROGRAMAS
# -----------------------------

PROGRAMAS_SITES = {

"Livelo": "https://www.livelo.com.br/ofertas",
"Smiles": "https://www.smiles.com.br/promocoes",
"LATAM Pass": "https://www.latampass.com/pt_br/promocoes",
"TudoAzul": "https://tudoazul.voeazul.com.br/web/azul/promocoes"

}

PROGRAMAS = ["livelo","smiles","latam","azul"]
BANCOS = ["itau","itaú","bradesco","santander","inter","c6"]
BONUS = ["100%","90%","85%","80%"]
MILHEIRO = ["milheiro","r$14","r$15","r$16","r$17"]
ERRO = ["erro tarifario","tarifa erro"]

ranking = {}

# -----------------------------
# HISTÓRICO
# -----------------------------

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

# -----------------------------
# COMANDOS TELEGRAM
# -----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
✈️ Radar de Milhas PRO+++

/menu
/promocoes
/transferencias
/passagens
/ranking
/status
"""

    await update.message.reply_text(texto)

# -----------------------------

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
📡 MENU RADAR

/promocoes
/transferencias
/passagens
/ranking
/status
"""

    await update.message.reply_text(texto)

# -----------------------------

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = f"""
🟢 RADAR ONLINE

Monitorando:

Blogs de milhas
Programas de pontos
Bancos

Promoções detectadas hoje: {len(ranking)}
"""

    await update.message.reply_text(texto)

# -----------------------------

async def ranking_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not ranking:

        await update.message.reply_text("Nenhuma promoção detectada hoje.")
        return

    texto = "🏆 Ranking de promoções do dia\n\n"

    ordenado = sorted(ranking.items(), key=lambda x: x[1], reverse=True)

    pos = 1

    for titulo,score in ordenado[:5]:

        texto += f"{pos}️⃣ {titulo}\n"

        pos += 1

    await update.message.reply_text(texto)

# -----------------------------

async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("🔎 Radar verificando promoções...")

# -----------------------------

async def transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
💳 Monitor de transferências ativo

Livelo
Smiles
LATAM Pass
TudoAzul

Bancos

Itaú
Bradesco
Santander
C6
Inter
"""

    await update.message.reply_text(texto)

# -----------------------------

async def passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
✈️ Monitor de passagens ativo

Detectando:

Erro tarifário
Promoções relâmpago
Milheiro barato
"""

    await update.message.reply_text(texto)

# -----------------------------
# SISTEMA DE PONTUAÇÃO
# -----------------------------

def pontuar(texto):

    score = 1

    if any(b in texto for b in BONUS):
        score += 5

    if any(m in texto for m in MILHEIRO):
        score += 3

    if any(e in texto for e in ERRO):
        score += 4

    return score

# -----------------------------
# MONITOR BLOGS
# -----------------------------

async def monitor_blogs(context):

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

# -----------------------------
# MONITOR PROGRAMAS OFICIAIS
# -----------------------------

async def monitor_programas(context):

    for nome, url in PROGRAMAS_SITES.items():

        try:

            r = requests.get(url, timeout=10)

            soup = BeautifulSoup(r.text, "html.parser")

            texto = soup.get_text().lower()

            if "100%" in texto or "90%" in texto or "bônus" in texto:

                msg = f"""
🚨 POSSÍVEL PROMOÇÃO DETECTADA

Programa: {nome}

Confira:
{url}
"""

                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=msg
                )

        except:

            pass

# -----------------------------
# MAIN
# -----------------------------

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
        monitor_blogs,
        interval=600,
        first=20
    )

    job.run_repeating(
        monitor_programas,
        interval=900,
        first=30
    )

    print("Radar PRO+++ iniciado")

    app.run_polling()

if __name__ == "__main__":
    main()
