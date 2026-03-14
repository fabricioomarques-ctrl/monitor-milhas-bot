import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config import TELEGRAM_TOKEN, CANAL_ID
from engine.radar_engine import executar_radar, STATE
from dashboard.status_builder import build_status_text, build_debug_text


RADAR_INTERVAL = 3600


def is_admin(update: Update):
    return True


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (
        "✈️ Radar de Milhas PRO\n\n"
        "/menu\n"
        "/promocoes\n"
        "/transferencias\n"
        "/passagens\n"
        "/ranking\n"
        "/status"
    )

    await update.message.reply_text(texto, disable_web_page_preview=True)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = (
        "📡 MENU\n\n"
        "/promocoes\n"
        "/transferencias\n"
        "/passagens\n"
        "/ranking\n"
        "/status\n"
        "/testeradar\n"
        "/debug"
    )

    await update.message.reply_text(texto, disable_web_page_preview=True)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = build_status_text(RADAR_INTERVAL)

    await update.message.reply_text(texto, disable_web_page_preview=True)


async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = build_debug_text()

    await update.message.reply_text(texto, disable_web_page_preview=True)


async def cmd_promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    promos = STATE.promocoes[:5]

    if not promos:

        await update.message.reply_text(
            "🔥 Últimas promoções\n\nNenhuma promoção registrada ainda.",
            disable_web_page_preview=True,
        )

        return

    texto = "🔥 Últimas promoções\n\n"

    for p in promos:

        texto += f"{p['title']}\nScore {p['score']}\n\n"

    await update.message.reply_text(texto, disable_web_page_preview=True)


async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):

    promos = sorted(STATE.promocoes, key=lambda x: x["score"], reverse=True)[:5]

    if not promos:

        await update.message.reply_text(
            "🏆 Ranking promoções\n\nNenhuma promoção registrada ainda.",
            disable_web_page_preview=True,
        )

        return

    texto = "🏆 Ranking promoções\n\n"

    for i, p in enumerate(promos, start=1):

        texto += f"{i}. {p['title']} | score {p['score']}\n"

    await update.message.reply_text(texto, disable_web_page_preview=True)


async def cmd_passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):

    promos = [p for p in STATE.promocoes if p["type"] == "passagens"][:5]

    if not promos:

        await update.message.reply_text(
            "✈️ Últimos alertas de passagens\n\nNenhuma promoção registrada ainda.",
            disable_web_page_preview=True,
        )

        return

    texto = "✈️ Últimos alertas de passagens\n\n"

    for p in promos:

        texto += f"{p['title']}\nScore {p['score']}\n\n"

    await update.message.reply_text(texto, disable_web_page_preview=True)


async def cmd_transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):

    promos = [p for p in STATE.promocoes if p["type"] == "transferencias"][:5]

    if not promos:

        await update.message.reply_text(
            "💳 Promoções de transferências de pontos monitoradas\n\n"
            "• Livelo\n"
            "• LATAM Pass\n"
            "• Smiles\n"
            "• TudoAzul\n\n"
            "Use /promocoes para ver ofertas atuais.",
            disable_web_page_preview=True,
        )

        return

    texto = "💳 Promoções de transferências\n\n"

    for p in promos:

        texto += f"{p['title']}\nScore {p['score']}\n\n"

    await update.message.reply_text(texto, disable_web_page_preview=True)


async def cmd_testeradar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("🧪 Teste manual do radar iniciado...")

    novas = await executar_radar(context.bot)

    await update.message.reply_text(
        f"✅ Radar executado\n\nNovas promoções enviadas: {novas}"
    )


async def scheduled_scan(bot):

    await executar_radar(bot)


async def post_init(application):

    application.bot._radar_channel_id = CANAL_ID

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        scheduled_scan,
        "interval",
        seconds=RADAR_INTERVAL,
        args=[application.bot],
        next_run_time=datetime.now(),  # executa imediatamente
    )

    scheduler.start()

    application.bot_data["scheduler"] = scheduler


async def post_shutdown(application):

    scheduler = application.bot_data.get("scheduler")

    if scheduler:
        scheduler.shutdown(wait=False)


def main():

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("promocoes", cmd_promocoes))
    app.add_handler(CommandHandler("transferencias", cmd_transferencias))
    app.add_handler(CommandHandler("passagens", cmd_passagens))
    app.add_handler(CommandHandler("ranking", cmd_ranking))
    app.add_handler(CommandHandler("testeradar", cmd_testeradar))
    app.add_handler(CommandHandler("debug", cmd_debug))

    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
