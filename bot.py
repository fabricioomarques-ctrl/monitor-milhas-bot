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
# RSS BLOGS
# -----------------------------

RSS_FEEDS = [

"https://www.melhoresdestinos.com.br/feed",
"https://passageirodeprimeira.com/feed",
"https://pontospravoar.com/feed",
"https://estevaopelomundo.com.br/feed"

]

# -----------------------------
# PROGRAMAS
# -----------------------------

PROGRAMAS_SITES = {

"Livelo":"https://www.livelo.com.br/ofertas",
"Smiles":"https://www.smiles.com.br/promocoes",
"LATAM":"https://www.latampass.com/pt_br/promocoes",
"TudoAzul":"https://tudoazul.voeazul.com.br/web/azul/promocoes"

}

# -----------------------------
# FONTES ANTECIPADAS
# -----------------------------

FONTES_ANTECIPADAS = [

"https://www.livelo.com.br/parceiros",
"https://www.smiles.com.br/parceiros",
"https://www.latampass.com/pt_br/parceiros",
"https://tudoazul.voeazul.com.br/parceiros"

]

# -----------------------------
# MILHEIRO
# -----------------------------

MILHEIRO_SITES = [

"https://www.maxmilhas.com.br",
"https://www.hotmilhas.com.br"

]

BONUS = ["100%","95%","90%","85%","80%"]

PALAVRAS_PROMO = ["bonus","bônus","promo","promoção","transfer"]

IGNORAR = ["shopping","produto","loja"]

# -----------------------------
# HISTÓRICO
# -----------------------------

def carregar():

    try:
        with open(ARQUIVO,"r") as f:
            return json.load(f)

    except:
        return []

def salvar(data):

    with open(ARQUIVO,"w") as f:
        json.dump(data,f)

historico = carregar()

ranking = {}

def ja_enviado(item):

    return item in historico

def registrar(item):

    historico.append(item)

    salvar(historico)

# -----------------------------
# COMANDOS
# -----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
✈️ Radar de Milhas PRO+++ Ultra

/menu
/ranking
/status
"""

    await update.message.reply_text(texto)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
📡 MENU

/ranking
/status
"""

    await update.message.reply_text(texto)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = f"""
🟢 RADAR ONLINE

Promoções detectadas hoje: {len(ranking)}

Detectores ativos:

✔ blogs
✔ programas
✔ milheiro
✔ radar antecipado
"""

    await update.message.reply_text(texto)

async def ranking_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not ranking:

        await update.message.reply_text("Nenhuma promoção detectada ainda.")
        return

    texto = "🏆 Ranking promoções\n\n"

    ordenado = sorted(ranking.items(), key=lambda x: x[1], reverse=True)

    pos = 1

    for titulo,score in ordenado[:5]:

        texto += f"{pos}️⃣ {titulo}\n"

        pos += 1

    await update.message.reply_text(texto)

# -----------------------------
# RADAR BLOGS
# -----------------------------

async def monitor_blogs(context):

    for feed in RSS_FEEDS:

        noticias = feedparser.parse(feed)

        for post in noticias.entries[:5]:

            titulo = post.title
            link = post.link

            chave = titulo + link

            if ja_enviado(chave):
                continue

            texto = titulo.lower()

            if any(b in texto for b in BONUS):

                msg = f"🔥 BÔNUS DETECTADO\n\n{titulo}\n{link}"

                await context.bot.send_message(chat_id=CHAT_ID,text=msg)

                registrar(chave)

                ranking[titulo] = 10

                return

# -----------------------------
# RADAR PROGRAMAS
# -----------------------------

async def monitor_programas(context):

    for nome,url in PROGRAMAS_SITES.items():

        try:

            r = requests.get(url,timeout=10)

            soup = BeautifulSoup(r.text,"html.parser")

            links = soup.find_all("a",href=True)

            for l in links:

                href = l["href"]

                texto = href.lower()

                if any(p in texto for p in PALAVRAS_PROMO):

                    if any(i in texto for i in IGNORAR):
                        continue

                    chave = nome + href

                    if ja_enviado(chave):
                        continue

                    msg = f"""
🚨 POSSÍVEL PROMOÇÃO

Programa: {nome}

Link detectado:
{href}
"""

                    await context.bot.send_message(chat_id=CHAT_ID,text=msg)

                    registrar(chave)

                    ranking[nome] = 7

                    return

        except:

            pass

# -----------------------------
# RADAR MILHEIRO
# -----------------------------

async def monitor_milheiro(context):

    for site in MILHEIRO_SITES:

        try:

            r = requests.get(site,timeout=10)

            texto = r.text.lower()

            if "r$ 15" in texto or "r$ 16" in texto or "r$ 17" in texto:

                chave = site + "milheiro"

                if ja_enviado(chave):
                    continue

                msg = f"""
💰 MILHEIRO BARATO

Possível oportunidade detectada

{site}
"""

                await context.bot.send_message(chat_id=CHAT_ID,text=msg)

                registrar(chave)

                ranking["milheiro barato"] = 6

        except:

            pass

# -----------------------------
# RADAR ANTECIPADO
# -----------------------------

async def radar_antecipado(context):

    for url in FONTES_ANTECIPADAS:

        try:

            r = requests.get(url,timeout=10)

            texto = r.text.lower()

            if any(p in texto for p in PALAVRAS_PROMO):

                chave = url + "antecipado"

                if ja_enviado(chave):
                    continue

                msg = f"""
📡 POSSÍVEL PROMOÇÃO ANTECIPADA

Fonte detectada:
{url}
"""

                await context.bot.send_message(chat_id=CHAT_ID,text=msg)

                registrar(chave)

                ranking["promo antecipada"] = 8

        except:

            pass

# -----------------------------
# MAIN
# -----------------------------

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("menu",menu))
    app.add_handler(CommandHandler("status",status))
    app.add_handler(CommandHandler("ranking",ranking_cmd))

    job = app.job_queue

    job.run_repeating(monitor_blogs,interval=600,first=20)

    job.run_repeating(monitor_programas,interval=900,first=40)

    job.run_repeating(monitor_milheiro,interval=1200,first=60)

    job.run_repeating(radar_antecipado,interval=1500,first=80)

    print("Radar PRO+++ Ultra iniciado")

    app.run_polling()

if __name__ == "__main__":
    main()
