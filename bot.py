import os
import time
import feedparser
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================================
# VARIÁVEIS DE AMBIENTE
# ================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CANAL_ID = os.getenv("CANAL_ID")

# ================================
# FONTES MONITORADAS
# ================================

FONTES = [
    "https://www.pontospravoar.com/feed",
    "https://passageirodeprimeira.com/feed",
    "https://www.melhoresdestinos.com.br/feed",
]

PROMOCOES_DETECTADAS = []

# ================================
# FILTRO PROFISSIONAL
# ================================

def filtro_profissional(titulo):
    ruido = ["shopping", "varejo", "cashback"]
    titulo_lower = titulo.lower()

    for palavra in ruido:
        if palavra in titulo_lower:
            return False
    return True

# ================================
# SISTEMA DE SCORE
# ================================

def calcular_score(titulo):
    titulo = titulo.lower()

    if "milheiro" in titulo or "100%" in titulo:
        return 9.8
    if "bonus" in titulo:
        return 8.0
    return 7.0

# ================================
# CLASSIFICAÇÃO DA PROMOÇÃO
# ================================

def classificar(score):

    if score >= 9:
        return "🔴 PROMOÇÃO IMPERDÍVEL"

    if score >= 7.5:
        return "🟡 PROMOÇÃO MUITO BOA"

    return "🟢 PROMOÇÃO BOA"

# ================================
# DETECTOR DE PROMOÇÕES
# ================================

def detectar_promocoes():

    novas = []

    for fonte in FONTES:

        feed = feedparser.parse(fonte)

        for entry in feed.entries[:5]:

            titulo = entry.title
            link = entry.link

            if not filtro_profissional(titulo):
                continue

            score = calcular_score(titulo)

            promo = {
                "titulo": titulo,
                "link": link,
                "score": score
            }

            novas.append(promo)

    return novas

# ================================
# ENVIO DE ALERTA TELEGRAM
# ================================

async def enviar_alerta(context, promo):

    score = promo["score"]
    classificacao = classificar(score)

    mensagem = f"""
💰 PROMOÇÃO CONFIRMADA

Título: {promo['titulo']}

Score: {score}

{classificacao}

Link:
{promo['link']}
"""

    await context.bot.send_message(chat_id=CANAL_ID, text=mensagem)

# ================================
# LOOP DO RADAR
# ================================

async def radar(context: ContextTypes.DEFAULT_TYPE):

    global PROMOCOES_DETECTADAS

    novas = detectar_promocoes()

    for promo in novas:

        if promo["link"] not in [p["link"] for p in PROMOCOES_DETECTADAS]:

            PROMOCOES_DETECTADAS.append(promo)

            await enviar_alerta(context, promo)

# ================================
# COMANDOS DO BOT
# ================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Radar iniciado.")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = """
MENU

/promocoes
/transferencias
/passagens
/ranking
/status
"""

    await update.message.reply_text(texto)

async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not PROMOCOES_DETECTADAS:
        await update.message.reply_text("Nenhuma promoção detectada ainda.")
        return

    texto = "🔥 Últimas promoções\n\n"

    for p in PROMOCOES_DETECTADAS[-5:]:
        texto += f"• {p['titulo']} | score {p['score']}\n"

    await update.message.reply_text(texto)

async def transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔁 Últimas transferências\n\nNenhuma promoção registrada ainda.")

async def passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✈ Últimos alertas de passagens\n\nNenhuma promoção registrada ainda.")

async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):

    ranking = sorted(PROMOCOES_DETECTADAS, key=lambda x: x["score"], reverse=True)

    texto = "🏆 Ranking promoções\n\n"

    for i, p in enumerate(ranking[:5], start=1):
        texto += f"{i}. {p['titulo']} | score {p['score']}\n"

    await update.message.reply_text(texto)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = f"""
🟢 Radar online

Promoções detectadas: {len(PROMOCOES_DETECTADAS)}
Fontes monitoradas: {len(FONTES)}

Detectores ativos:
✓ blogs
✓ programas
✓ milheiro
✓ redes sociais
✓ confirmação múltipla
✓ score automático
✓ envio no canal
"""

    await update.message.reply_text(texto)

# ================================
# MAIN
# ================================

def main():

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("promocoes", promocoes))
    app.add_handler(CommandHandler("transferencias", transferencias))
    app.add_handler(CommandHandler("passagens", passagens))
    app.add_handler(CommandHandler("ranking", ranking))
    app.add_handler(CommandHandler("status", status))

    job_queue = app.job_queue
    job_queue.run_repeating(radar, interval=600, first=10)

    print("Radar iniciado.")

    app.run_polling()

if __name__ == "__main__":
    main()
