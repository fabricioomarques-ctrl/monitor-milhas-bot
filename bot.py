import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! 👋\n"
        "Sou seu monitor inteligente de milhas ✈️\n\n"
        "Comandos disponíveis:\n"
        "/promocoes - Ver promoções atuais\n"
        "/sites - Sites monitorados\n"
        "/ajuda - Ajuda"
    )

async def promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = (
        "🔥 Monitor de Promoções\n\n"
        "Atualmente monitorando:\n"
        "• Livelo\n"
        "• LATAM Pass\n"
        "• Smiles\n"
        "• TudoAzul\n\n"
        "E também sites de promoções."
    )
    await update.message.reply_text(mensagem)

async def sites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = (
        "🌐 Sites monitorados:\n\n"
        "- Melhores Destinos\n"
        "- Passagens Imperdíveis\n"
        "- Pontos pra Voar\n"
    )
    await update.message.reply_text(mensagem)

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot de monitoramento de milhas.\n\n"
        "Use /promocoes para ver oportunidades."
    )

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("promocoes", promocoes))
app.add_handler(CommandHandler("sites", sites))
app.add_handler(CommandHandler("ajuda", ajuda))

app.run_polling()
