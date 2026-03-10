import os
import re
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from urllib.parse import urljoin

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CANAL_ID = os.getenv("CANAL_ID")

ARQUIVO = "historico.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

RSS_FEEDS = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://pontospravoar.com/feed",
    "https://estevaopelomundo.com.br/feed"
]

PROGRAMAS = {
    "Livelo": "https://www.livelo.com.br/promocoes",
    "Smiles": "https://www.smiles.com.br/promocoes",
    "LATAM": "https://www.latampass.com/pt_br/promocoes",
    "TudoAzul": "https://tudoazul.voeazul.com.br/web/azul/promocoes"
}

MILHEIRO = [
    "https://www.maxmilhas.com.br",
    "https://www.hotmilhas.com.br"
]

BONUS_REGEX = r"(50|60|70|80|90|100)\s?%"

PALAVRAS_VALIDAS = [
    "milha",
    "milhas",
    "pontos",
    "transfer",
    "bônus",
    "bonus",
    "fidelidade",
    "latam pass",
    "smiles",
    "livelo",
    "tudoazul"
]

PALAVRAS_BLOQUEADAS = [
    "hotel",
    "seguro",
    "ingresso",
    "cruzeiro",
    "cvc",
    "pacote",
    "resort"
]

ranking = {}
historico = {}

def carregar():
    try:
        with open(ARQUIVO) as f:
            return json.load(f)
    except:
        return {}

def salvar():
    with open(ARQUIVO, "w") as f:
        json.dump(historico, f)

historico = carregar()

async def enviar(context, texto):

    await context.bot.send_message(chat_id=CHAT_ID, text=texto)

    if CANAL_ID:
        await context.bot.send_message(chat_id=CANAL_ID, text=texto)

def filtro_valido(texto):

    t = texto.lower()

    if any(b in t for b in PALAVRAS_BLOQUEADAS):
        return False

    if any(v in t for v in PALAVRAS_VALIDAS):
        return True

    return False

def detectar_bonus(texto):

    m = re.search(BONUS_REGEX, texto)

    if m:
        return m.group()

    return ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
✈️ Radar de Milhas PRO

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
Fontes monitoradas: {len(RSS_FEEDS) + len(PROGRAMAS)}
"""

    await update.message.reply_text(texto)

async def ranking_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not ranking:
        await update.message.reply_text("Nenhuma promoção detectada.")
        return

    texto = "🏆 Ranking promoções\n\n"

    ordenado = sorted(ranking.items(), key=lambda x: x[1], reverse=True)

    for i,(k,v) in enumerate(ordenado[:10],1):
        texto += f"{i}. {k}\n"

    await update.message.reply_text(texto)

async def promocoes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("🔥 Radar monitorando promoções.")

async def transferencias_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("🔁 Monitorando transferências bonificadas.")

async def passagens_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("✈️ Monitorando passagens com milhas.")

async def monitor_blogs(context):

    for feed in RSS_FEEDS:

        try:

            data = feedparser.parse(feed)

            for post in data.entries[:5]:

                titulo = post.title
                link = post.link

                if not filtro_valido(titulo):
                    continue

                if link in historico:
                    continue

                bonus = detectar_bonus(titulo)

                msg = f"🔥 Promoção detectada\n\n{titulo}"

                if bonus:
                    msg += f"\nBônus: {bonus}"

                msg += f"\n{link}"

                await enviar(context,msg)

                historico[link] = True
                salvar()

                ranking[titulo] = ranking.get(titulo,0)+10

                return

        except:
            pass

async def monitor_programas(context):

    for nome,url in PROGRAMAS.items():

        try:

            r = requests.get(url,headers=HEADERS,timeout=15)

            soup = BeautifulSoup(r.text,"html.parser")

            links = soup.find_all("a",href=True)

            for a in links:

                link = urljoin(url,a["href"])
                texto = a.text.strip()

                if not filtro_valido(texto):
                    continue

                if link in historico:
                    continue

                bonus = detectar_bonus(texto)

                msg = f"⚡ Promoção detectada\n\nPrograma: {nome}\n{texto}"

                if bonus:
                    msg += f"\nBônus: {bonus}"

                msg += f"\n{link}"

                await enviar(context,msg)

                historico[link]=True
                salvar()

                ranking[nome]=ranking.get(nome,0)+5

                return

        except:
            pass

async def monitor_milheiro(context):

    for site in MILHEIRO:

        try:

            r=requests.get(site,headers=HEADERS,timeout=15)

            txt=r.text.lower()

            if "r$ 15" in txt or "r$15" in txt:

                if site in historico:
                    continue

                msg=f"💰 Milheiro barato detectado\n\n{site}"

                await enviar(context,msg)

                historico[site]=True
                salvar()

                ranking["milheiro barato"]=ranking.get("milheiro barato",0)+7

        except:
            pass

def main():

    app=ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("menu",menu))
    app.add_handler(CommandHandler("status",status))
    app.add_handler(CommandHandler("ranking",ranking_cmd))
    app.add_handler(CommandHandler("promocoes",promocoes_cmd))
    app.add_handler(CommandHandler("transferencias",transferencias_cmd))
    app.add_handler(CommandHandler("passagens",passagens_cmd))

    job=app.job_queue

    job.run_repeating(monitor_blogs,interval=600,first=20)
    job.run_repeating(monitor_programas,interval=900,first=40)
    job.run_repeating(monitor_milheiro,interval=1200,first=60)

    print("Radar de Milhas PRO iniciado")

    app.run_polling()

if __name__=="__main__":
    main()
