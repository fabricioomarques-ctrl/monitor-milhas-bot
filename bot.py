import os
import re
import json
import asyncio
import hashlib
from datetime import datetime, timedelta
import requests
import feedparser
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CANAL_ID = os.getenv("CANAL_ID")

PROMOCOES_FILE = "promocoes_enviadas.json"
METRICS_FILE = "dashboard_metrics.json"

RADAR_INTERVAL_SECONDS = 3600
JANELA_REPETICAO_HORAS = 24

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ===============================
# FONTES
# ===============================

FONTES_RSS = [
"https://passageirodeprimeira.com/feed",
"https://pontospravoar.com/feed",
"https://www.melhoresdestinos.com.br/feed",
"https://aeroin.net/feed",
"https://www.melhorescartoes.com.br/feed",
"https://onemileatatime.com/feed/",
"https://viewfromthewing.com/feed/",
"https://frequentmiler.com/feed/",
"https://loyaltylobby.com/feed/",
"https://upgradedpoints.com/feed/",
"https://thepointsguy.com/feed/",
"https://awardwallet.com/blog/feed/",
"https://godsavethepoints.com/feed/",
"https://thriftytraveler.com/feed/",
"https://www.secretflying.com/feed/",
"https://www.fly4free.com/feed/",
]

FONTES_OFICIAIS = [
{"program": "Smiles","url":"https://www.smiles.com.br/promocoes"},
{"program": "Smiles","url":"https://www.smiles.com.br/clube-smiles"},
{"program": "LATAM Pass","url":"https://latampass.latam.com"},
{"program": "TudoAzul","url":"https://www.voeazul.com.br"},
{"program": "Livelo","url":"https://www.livelo.com.br"},
{"program": "Esfera","url":"https://www.esfera.com.vc"},
{"program": "ALL Accor","url":"https://all.accor.com"},
]

SITEMAPS = [
"https://www.smiles.com.br/sitemap.xml",
"https://www.livelo.com.br/sitemap.xml",
"https://www.esfera.com.vc/sitemap.xml",
"https://latampass.latam.com/sitemap.xml",
]

# ===============================
# UTIL
# ===============================

def limpar_texto(texto):
    if not texto:
        return ""
    texto = BeautifulSoup(texto, "html.parser").get_text(" ", strip=True)
    texto = re.sub(r"https?://\S+","",texto)
    texto = re.sub(r"\s+"," ",texto)
    return texto.strip()

def hash_id(texto):
    return hashlib.md5(texto.encode()).hexdigest()

def carregar_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path,"r",encoding="utf8") as f:
        return json.load(f)

def salvar_json(path,data):
    with open(path,"w",encoding="utf8") as f:
        json.dump(data,f,indent=2,ensure_ascii=False)

# ===============================
# DETECTORES
# ===============================

def detectar_bonus(texto):
    achados=re.findall(r"(\d{2,3})\s*%",texto)
    if achados:
        return max([int(x) for x in achados])
    return 0

def detectar_milheiro(texto):
    m=re.search(r"milheiro[^0-9]*r\$?\s*(\d+[,.]?\d*)",texto.lower())
    if m:
        return float(m.group(1).replace(",","."))
    return None

def detectar_programa(texto):

    programas={
"smiles":"Smiles",
"latam":"LATAM Pass",
"azul":"TudoAzul",
"livelo":"Livelo",
"esfera":"Esfera",
"accor":"ALL Accor",
}

    t=texto.lower()

    for k,v in programas.items():
        if k in t:
            return v

    return None

def detectar_tipo(texto):

    t=texto.lower()

    if "transfer" in t or "bônus" in t or "bonus" in t:
        return "transferencias"

    if "milheiro" in t or "comprar milhas" in t:
        return "milheiro"

    if "passagem" in t or "resgate" in t:
        return "passagens"

    return None

# ===============================
# COLETA
# ===============================

def coletar_rss():

    itens=[]

    for url in FONTES_RSS:
        try:
            feed=feedparser.parse(url)
            for entry in feed.entries[:15]:
                itens.append({
"title":entry.title,
"link":entry.link,
"summary":entry.summary if "summary" in entry else ""
})
        except:
            pass

    return itens

def coletar_paginas():

    itens=[]

    for f in FONTES_OFICIAIS:

        try:
            r=requests.get(f["url"],headers=HEADERS,timeout=15)
            soup=BeautifulSoup(r.text,"html.parser")

            texto=soup.get_text(" ",strip=True)

            itens.append({
"title":texto[:200],
"summary":texto,
"link":f["url"]
})
        except:
            pass

    return itens

# ===============================
# TRANSFORMAÇÃO
# ===============================

def transformar(itens):

    promocoes=[]

    for item in itens:

        texto=f"{item['title']} {item['summary']}"
        texto=limpar_texto(texto)

        tipo=detectar_tipo(texto)
        if not tipo:
            continue

        programa=detectar_programa(texto)
        if not programa:
            continue

        bonus=detectar_bonus(texto)
        milheiro=detectar_milheiro(texto)

        score=7

        if bonus>=100:
            score=9.7
        elif bonus>=80:
            score=9

        if milheiro:
            if milheiro<=10:
                score=10
            elif milheiro<=11:
                score=9.5

        promo={
"id":hash_id(texto),
"title":texto[:140],
"link":item["link"],
"type":tipo,
"program":programa,
"score":score,
"bonus":bonus,
"milheiro":milheiro,
"created_at":datetime.now().isoformat()
}

        promocoes.append(promo)

    return promocoes

# ===============================
# RANKING
# ===============================

def ranking(promos):

    vistos=set()
    resultado=[]

    for p in sorted(promos,key=lambda x:x["score"],reverse=True):

        key=f"{p['program']}-{p['type']}-{p['bonus']}-{p['milheiro']}"

        if key in vistos:
            continue

        vistos.add(key)
        resultado.append(p)

    return resultado[:5]

# ===============================
# RADAR
# ===============================

async def rodar_radar(bot):

    rss=coletar_rss()
    paginas=coletar_paginas()

    itens=rss+paginas

    promocoes=transformar(itens)

    historico=carregar_json(PROMOCOES_FILE,[])

    ids={p["id"] for p in historico}

    novas=[]

    for p in promocoes:
        if p["id"] not in ids:
            novas.append(p)
            historico.append(p)

    salvar_json(PROMOCOES_FILE,historico)

    for p in novas:

        msg=f"""
🚨 ALERTA

Programa: {p['program']}
Tipo: {p['type']}

{p['title']}

Score: {p['score']}

{p['link']}
"""

        await bot.send_message(chat_id=CANAL_ID,text=msg)

# ===============================
# COMANDOS
# ===============================

async def status(update:Update,context:ContextTypes.DEFAULT_TYPE):

    promos=carregar_json(PROMOCOES_FILE,[])

    msg=f"""
🟢 Radar online

Promoções registradas: {len(promos)}

Intervalo: {RADAR_INTERVAL_SECONDS}s
"""

    await update.message.reply_text(msg)

async def ranking_cmd(update:Update,context:ContextTypes.DEFAULT_TYPE):

    promos=carregar_json(PROMOCOES_FILE,[])

    r=ranking(promos)

    txt="🏆 Ranking oportunidades\n\n"

    for i,p in enumerate(r,1):

        txt+=f"""{i}. {p['program']}
{p['title']}
Score: {p['score']}

"""

    await update.message.reply_text(txt)

async def transferencias(update:Update,context:ContextTypes.DEFAULT_TYPE):

    promos=carregar_json(PROMOCOES_FILE,[])

    filtradas=[p for p in promos if p["type"]=="transferencias"]

    txt="💳 Transferências\n\n"

    for p in filtradas[:5]:

        txt+=f"""
{p['program']}
{p['title']}
Bônus: {p['bonus']}%

"""

    await update.message.reply_text(txt)

# ===============================
# BOT
# ===============================

async def post_init(app):

    scheduler=AsyncIOScheduler()

    scheduler.add_job(
rodar_radar,
"interval",
seconds=RADAR_INTERVAL_SECONDS,
args=[app.bot]
)

    scheduler.start()

def main():

    app=ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("status",status))
    app.add_handler(CommandHandler("ranking",ranking_cmd))
    app.add_handler(CommandHandler("transferencias",transferencias))

    app.run_polling()

if __name__=="__main__":
    main()
