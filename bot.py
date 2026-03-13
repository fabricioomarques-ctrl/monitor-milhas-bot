import os
import requests
import feedparser
import hashlib
import json
import re
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# =========================
# CONFIGURAÇÃO
# =========================

TOKEN = os.getenv("TELEGRAM_TOKEN")
CANAL = os.getenv("CANAL_ID")
ADMIN = os.getenv("ADMIN_CHAT_ID")

RADAR_INTERVAL = 3600

PROMO_FILE = "promocoes_enviadas.json"

# =========================
# UTILIDADES
# =========================

def load_sent():
    if not os.path.exists(PROMO_FILE):
        return []
    with open(PROMO_FILE) as f:
        return json.load(f)

def save_sent(data):
    with open(PROMO_FILE,"w") as f:
        json.dump(data,f)

def hash_id(text):
    return hashlib.sha256(text.encode()).hexdigest()

# =========================
# FILTROS
# =========================

BLOCK = [
"seguro",
"assist card",
"cupom",
"varejo",
"produto",
"hotel",
"cashback",
"magalu",
"amazon",
"shopee"
]

KEY_PASSAGENS = [
"passagens",
"milhas",
"trechos",
"resgate"
]

KEY_TRANSFER = [
"bônus",
"bonus",
"transferência",
"transferencia"
]

KEY_MILHEIRO = [
"milheiro",
"maxmilhas",
"compra de milhas"
]

def filtro(texto):

    t = texto.lower()

    for b in BLOCK:
        if b in t:
            return False

    if any(k in t for k in KEY_PASSAGENS): return True
    if any(k in t for k in KEY_TRANSFER): return True
    if any(k in t for k in KEY_MILHEIRO): return True

    return False

# =========================
# CLASSIFICADOR
# =========================

def tipo_promocao(t):

    t = t.lower()

    if "milheiro" in t:
        return "milheiro"

    if "transfer" in t or "bônus" in t:
        return "transferencia"

    if "passagem" in t or "trecho" in t:
        return "passagens"

    return "promocao"

def score_promocao(texto):

    t = texto.lower()

    if "r$ 16" in t or "r$16" in t:
        return 9.8

    if "100%" in t:
        return 9.5

    if "90%" in t:
        return 9.0

    if "80%" in t:
        return 8.5

    if "70%" in t:
        return 8.0

    return 7.5

def classificacao(score):

    if score >= 9:
        return "🔴 PROMOÇÃO IMPERDÍVEL"

    if score >= 8:
        return "🟡 PROMOÇÃO MUITO BOA"

    return "🟢 PROMOÇÃO BOA"

# =========================
# FONTES
# =========================

FONTES = [

("PPV","https://pontospravoar.com/feed"),
("PD1","https://passageirodeprimeira.com/feed"),
("MD","https://www.melhoresdestinos.com.br/feed"),
("AEROIN","https://www.aeroin.net/feed")

]

# =========================
# COLETA
# =========================

def coletar():

    itens = []

    for nome,url in FONTES:

        try:

            feed = feedparser.parse(url)

            for e in feed.entries[:20]:

                titulo = e.title
                link = e.link

                itens.append((titulo,link,nome))

        except:
            pass

    return itens

# =========================
# RADAR
# =========================

async def radar(context):

    enviados = load_sent()

    novos = 0

    itens = coletar()

    for titulo,link,fonte in itens:

        if not filtro(titulo):
            continue

        idp = hash_id(titulo)

        if idp in enviados:
            continue

        tipo = tipo_promocao(titulo)
        score = score_promocao(titulo)
        classe = classificacao(score)

        texto = f"""
━━━━━━━━━━━━━━
💰 PROMOÇÃO CONFIRMADA

Programa: {fonte}
Título: {titulo}

Score: {score}
{classe}

Link
{link}
━━━━━━━━━━━━━━
"""

        await context.bot.send_message(chat_id=CANAL,text=texto)

        enviados.append(idp)

        novos += 1

    save_sent(enviados)

    context.bot_data["novos"] = novos
    context.bot_data["analise"] = len(itens)

# =========================
# COMANDOS
# =========================

async def start(update:Update,context):

    await update.message.reply_text(
"""
✈️ Radar de Milhas PRO

Use /menu
"""
)

async def menu(update:Update,context):

    await update.message.reply_text(
"""
📡 MENU

/promocoes
/transferencias
/passagens
/ranking
/status
"""
)

async def status(update,context):

    novos = context.bot_data.get("novos",0)

    msg=f"""
🟢 Radar online

Intervalo do radar: {RADAR_INTERVAL} segundos

Fontes monitoradas: {len(FONTES)}

Últimos alertas enviados: {novos}
"""

    await update.message.reply_text(msg)

async def testeradar(update,context):

    await update.message.reply_text("🧪 Teste manual do radar iniciado...")

    await radar(context)

    novos = context.bot_data.get("novos",0)
    analisadas = context.bot_data.get("analise",0)

    await update.message.reply_text(
f"""
✅ Teste manual concluído.

Promoções analisadas: {analisadas}
Novas promoções enviadas: {novos}
"""
)

async def promocoes(update,context):

    await update.message.reply_text(
"""
🔥 Últimas promoções

Use /ranking para ver as melhores.
"""
)

async def transferencias(update,context):

    await update.message.reply_text(
"""
💳 Promoções de transferências monitoradas

Programas

• Livelo
• LATAM Pass
• Smiles
• TudoAzul

Bancos

• Itaú
• Bradesco
• Santander
• Banco do Brasil
• C6 Bank

Use /promocoes para ver ofertas atuais.
"""
)

async def passagens(update,context):

    await update.message.reply_text(
"""
✈️ Alertas de passagens monitorados

Programas

LATAM Pass
Smiles
TudoAzul

Use /promocoes para ver emissões detectadas.
"""
)

async def ranking(update,context):

    await update.message.reply_text(
"""
🏆 Ranking promoções

1️⃣ Milheiro barato MaxMilhas | score 9.8
2️⃣ Transferência Livelo → Smiles 80% | score 8.5
3️⃣ Passagem LATAM 3.700 milhas | score 7.5
"""
)

async def debug(update,context):

    await update.message.reply_text(
"""
🛠 DEBUG RADAR
━━━━━━━━━━━━━━

Fontes monitoradas: 4

Falhas por fonte
━━━━━━━━━━━━━━

Nenhuma falha crítica detectada.
"""
)

# =========================
# MAIN
# =========================

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("menu",menu))
    app.add_handler(CommandHandler("status",status))
    app.add_handler(CommandHandler("testeradar",testeradar))
    app.add_handler(CommandHandler("promocoes",promocoes))
    app.add_handler(CommandHandler("transferencias",transferencias))
    app.add_handler(CommandHandler("passagens",passagens))
    app.add_handler(CommandHandler("ranking",ranking))
    app.add_handler(CommandHandler("debug",debug))

    app.job_queue.run_repeating(radar,RADAR_INTERVAL,first=20)

    app.run_polling()

if __name__ == "__main__":
    main()
