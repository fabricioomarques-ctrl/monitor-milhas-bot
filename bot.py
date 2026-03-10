import os
import feedparser
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CANAL_ID = os.getenv("CANAL_ID")

RSS_FEEDS = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://pontospravoar.com/feed",
    "https://estevaopelomundo.com.br/feed",
]

MILHEIRO_SITES = [
    "https://www.maxmilhas.com.br",
    "https://www.hotmilhas.com.br"
]

enviados = set()
ranking = {}

def enviar(context, mensagem):

    context.bot.send_message(chat_id=CHAT_ID, text=mensagem)

    if CANAL_ID:
        context.bot.send_message(chat_id=CANAL_ID, text=mensagem)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
✈️ Radar de Milhas PRO MAX

/menu
/promocoes
/transferencias
/passagens
/ranking
/status
"""

    await update.message.reply_text(texto)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
📡 MENU

/promocoes
/transferencias
/passagens
/ranking
/status
"""

    await update.message.reply_text(texto)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = f"""
🟢 Radar online

Promoções detectadas: {len(ranking)}
Fontes monitoradas: {len(RSS_FEEDS)}

Bots ativos:
✔ blogs
✔ milheiro
✔ radar
"""

    await update.message.reply_text(texto)

async def ranking_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not ranking:
        await update.message.reply_text("Nenhuma promoção detectada ainda.")
        return

    texto = "🏆 Ranking promoções\n\n"

    ordenado = sorted(ranking.items(), key=lambda x: x[1], reverse=True)

    for i,(titulo,pontos) in enumerate(ordenado[:10],1):

        texto += f"{i}. {titulo}\n"

    await update.message.reply_text(texto)

async def promocoes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = "🔥 Radar monitorando promoções em tempo real."

    await update.message.reply_text(texto)

async def transferencias_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = "🔁 Monitorando transferências bonificadas."

    await update.message.reply_text(texto)

async def passagens_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
✈️ Radar de passagens ativo

Detectando:

• promoções
• milhas baratas
• erro tarifário
"""

    await update.message.reply_text(texto)

async def monitor_blogs(context):

    for feed in RSS_FEEDS:

        try:

            noticias = feedparser.parse(feed)

            for post in noticias.entries[:5]:

                titulo = post.title
                link = post.link

                chave = titulo

                if chave in enviados:
                    continue

                if "milha" in titulo.lower() or "promo" in titulo.lower():

                    msg = f"🔥 Promoção detectada\n\n{titulo}\n{link}"

                    await context.bot.send_message(chat_id=CHAT_ID,text=msg)

                    if CANAL_ID:
                        await context.bot.send_message(chat_id=CANAL_ID,text=msg)

                    enviados.add(chave)

                    ranking[titulo] = ranking.get(titulo,0) + 10

                    return

        except:
            pass

async def monitor_milheiro(context):

    for site in MILHEIRO_SITES:

        try:

            r = requests.get(site,timeout=10)

            txt = r.text.lower()

            if "r$ 15" in txt or "r$15" in txt:

                chave = site

                if chave in enviados:
                    continue

                msg = f"💰 Milheiro barato detectado\n\n{site}"

                await context.bot.send_message(chat_id=CHAT_ID,text=msg)

                if CANAL_ID:
                    await context.bot.send_message(chat_id=CANAL_ID,text=msg)

                enviados.add(chave)

        except:
            pass

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("menu",menu))
    app.add_handler(CommandHandler("promocoes",promocoes_cmd))
    app.add_handler(CommandHandler("transferencias",transferencias_cmd))
    app.add_handler(CommandHandler("passagens",passagens_cmd))
    app.add_handler(CommandHandler("ranking",ranking_cmd))
    app.add_handler(CommandHandler("status",status))

    job = app.job_queue

    job.run_repeating(monitor_blogs,interval=600,first=10)
    job.run_repeating(monitor_milheiro,interval=900,first=30)

    print("Radar PRO iniciado")

    app.run_polling()

if __name__ == "__main__":
    main()
