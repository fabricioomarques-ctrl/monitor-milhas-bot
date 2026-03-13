from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config import ADMIN_IDS, CANAL_ID, RADAR_INTERVAL_SECONDS, TELEGRAM_TOKEN
from dashboard.status_builder import build_debug_text, build_status_text
from engine.radar_engine import (
    build_passagens_text,
    build_promocoes_text,
    build_ranking_text,
    build_transferencias_text,
    run_radar,
)


def is_admin(update: Update) -> bool:
    if not update.effective_chat:
        return False
    return update.effective_chat.id in ADMIN_IDS


async def deny_admin(update: Update):
    await update.message.reply_text("⛔ Comando disponível apenas para o administrador.")


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
    await update.message.reply_text(
        build_status_text(RADAR_INTERVAL_SECONDS),
        disable_web_page_preview=True,
    )


async def cmd_promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        build_promocoes_text(),
        disable_web_page_preview=True,
    )


async def cmd_transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        build_transferencias_text(),
        disable_web_page_preview=True,
    )


async def cmd_passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        build_passagens_text(),
        disable_web_page_preview=True,
    )


async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        build_ranking_text(),
        disable_web_page_preview=True,
    )


async def cmd_testeradar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny_admin(update)
        return

    await update.message.reply_text("🧪 Teste manual do radar iniciado...", disable_web_page_preview=True)
    result = await run_radar(context.bot)

    texto = (
        "✅ Teste manual concluído.\n\n"
        f"Fontes monitoradas: 15\n"
        f"Promoções analisadas: {result['analisadas']}\n"
        f"Novas promoções enviadas: {result['novas_enviadas']}\n"
        f"Último erro: {result['erro']}"
    )
    await update.message.reply_text(texto, disable_web_page_preview=True)


async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny_admin(update)
        return

    await update.message.reply_text(
        build_debug_text(),
        disable_web_page_preview=True,
    )


async def scheduled_scan(bot):
    await run_radar(bot)


async def post_init(application):
    application.bot._radar_channel_id = CANAL_ID

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_scan,
        "interval",
        seconds=RADAR_INTERVAL_SECONDS,
        args=[application.bot],
        id="radar_scan",
        replace_existing=True,
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
