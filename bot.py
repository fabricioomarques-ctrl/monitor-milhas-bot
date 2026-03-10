import os
import re
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN=os.getenv("TELEGRAM_TOKEN")
CHAT_ID=os.getenv("CHAT_ID")
CANAL_ID=os.getenv("CANAL_ID")

ARQUIVO="historico.json"

HEADERS={"User-Agent":"Mozilla/5.0"}

# BLOGS
RSS_FEEDS=[
"https://www.melhoresdestinos.com.br/feed",
"https://passageirodeprimeira.com/feed",
"https://pontospravoar.com/feed"
]

# PROGRAMAS
PROGRAMAS={
"Livelo":"https://www.livelo.com.br/promocoes",
"Smiles":"https://www.smiles.com.br/promocoes",
"LATAM":"https://www.latampass.com/pt_br/promocoes",
"TudoAzul":"https://tudoazul.voeazul.com.br/web/azul/promocoes"
}

# MILHEIRO
MILHEIRO=[
"https://www.maxmilhas.com.br",
"https://www.hotmilhas.com.br"
]

PALAVRAS_VALIDAS=[
"milhas","milha","transfer","bônus","bonus",
"smiles","livelo","latam","tudoazul"
]

PALAVRAS_BLOQUEADAS=[
"hotel","resort","pacote","seguro",
"cruzeiro","ingresso","shopping"
]

BONUS_REGEX=r"(30|40|50|60|70|80|90|100)%"

ranking={}
historico={}
eventos={}

# carregar histórico
try:
    with open(ARQUIVO) as f:
        historico=json.load(f)
except:
    historico={}

def salvar():
    with open(ARQUIVO,"w") as f:
        json.dump(historico,f)

def filtro(txt):

    t=txt.lower()

    if any(b in t for b in PALAVRAS_BLOQUEADAS):
        return False

    if any(v in t for v in PALAVRAS_VALIDAS):
        return True

    return False

def classificar(txt):

    m=re.search(BONUS_REGEX,txt)

    if not m:
        return "🟢 Promoção boa"

    bonus=int(m.group().replace("%",""))

    if bonus>=100:
        return "🔴 PROMOÇÃO IMPERDÍVEL"

    if bonus>=80:
        return "🟡 Promoção muito boa"

    return "🟢 Promoção boa"

async def enviar(context,msg):

    await context.bot.send_message(chat_id=CHAT_ID,text=msg)

    if CANAL_ID:
        await context.bot.send_message(chat_id=CANAL_ID,text=msg)

def registrar_evento(chave,fonte):

    if chave not in eventos:
        eventos[chave]=set()

    eventos[chave].add(fonte)

    return len(eventos[chave])

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    texto="""
✈️ Radar de Milhas PRO MAX

/menu
/ranking
/status
"""

    await update.message.reply_text(texto)

async def menu(update:Update,context:ContextTypes.DEFAULT_TYPE):

    texto="""
📡 MENU

/ranking
/status
"""

    await update.message.reply_text(texto)

async def status(update:Update,context:ContextTypes.DEFAULT_TYPE):

    texto=f"""
🟢 Radar online

Promoções detectadas: {len(ranking)}

Detectores ativos
✔ blogs
✔ programas
✔ milheiro
✔ confirmação múltipla
"""

    await update.message.reply_text(texto)

async def ranking_cmd(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if not ranking:
        await update.message.reply_text("Nenhuma promoção detectada")
        return

    texto="🏆 Ranking promoções\n\n"

    ordenado=sorted(ranking.items(),key=lambda x:x[1],reverse=True)

    for i,(k,v) in enumerate(ordenado[:10],1):
        texto+=f"{i}. {k}\n"

    await update.message.reply_text(texto)

async def blogs(context):

    for feed in RSS_FEEDS:

        try:

            data=feedparser.parse(feed)

            for post in data.entries[:5]:

                titulo=post.title
                link=post.link

                if not filtro(titulo):
                    continue

                if link in historico:
                    continue

                chave=titulo.lower()

                fontes=registrar_evento(chave,"blog")

                if fontes<2:
                    continue

                nivel=classificar(titulo)

                msg=f"""
🔥 PROMOÇÃO CONFIRMADA

{titulo}

{nivel}

{link}
"""

                await enviar(context,msg)

                historico[link]=True
                salvar()

                ranking[titulo]=ranking.get(titulo,0)+10

                return

        except:
            pass

async def programas(context):

    for nome,url in PROGRAMAS.items():

        try:

            r=requests.get(url,headers=HEADERS,timeout=15)

            soup=BeautifulSoup(r.text,"html.parser")

            links=soup.find_all("a",href=True)

            for a in links:

                txt=a.text.strip()
                link=urljoin(url,a["href"])

                if not filtro(txt):
                    continue

                if link in historico:
                    continue

                chave=txt.lower()

                fontes=registrar_evento(chave,"programa")

                if fontes<2:
                    continue

                nivel=classificar(txt)

                msg=f"""
⚡ PROMOÇÃO CONFIRMADA

Programa: {nome}

{txt}

{nivel}

{link}
"""

                await enviar(context,msg)

                historico[link]=True
                salvar()

                ranking[nome]=ranking.get(nome,0)+5

                return

        except:
            pass

async def milheiro(context):

    for site in MILHEIRO:

        try:

            r=requests.get(site,headers=HEADERS,timeout=15)

            txt=r.text.lower()

            if "r$ 15" in txt or "r$15" in txt:

                if site in historico:
                    continue

                msg=f"""
💰 MILHEIRO BARATO

🔴 PROMOÇÃO IMPERDÍVEL

{site}
"""

                await enviar(context,msg)

                historico[site]=True
                salvar()

                ranking["milheiro"]=ranking.get("milheiro",0)+7

        except:
            pass

def main():

    app=ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("menu",menu))
    app.add_handler(CommandHandler("status",status))
    app.add_handler(CommandHandler("ranking",ranking_cmd))

    job=app.job_queue

    # modo estável (10 min)
    job.run_repeating(blogs,interval=600,first=20)
    job.run_repeating(programas,interval=600,first=30)
    job.run_repeating(milheiro,interval=600,first=40)

    print("Radar PRO MAX iniciado")

    app.run_polling()

if __name__=="__main__":
    main()
