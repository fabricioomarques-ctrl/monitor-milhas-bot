import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config import ADMIN_IDS, CANAL_ID, MAX_RANKING, RADAR_INTERVAL_SECONDS, TELEGRAM_TOKEN
from dashboard.status_builder import build_debug_text, build_status_text
from engine.radar_engine import (
    STATE,
    executar_varredura,
    get_promocoes_por_tipo,
    get_ranking,
)

SCAN_LOCK = asyncio.Lock()


def is_admin(update: Update) -> bool:
    if not ADMIN_IDS:
        return True
    if not update.effective_chat:
        return False
    return update.effective_chat.id in ADMIN_IDS


def format_card(promo: dict) -> str:
    texto = "💰 PROMOÇÃO CONFIRMADA\n\n"
    texto += f"Programa: {promo.get('program', 'Programa não identificado')}\n"
    texto += f"Título: {promo.get('title', '')}\n"
    texto += f"Fontes confirmadas: {promo.get('fontes_confirmadas', 1)}\n"
    texto += f"Score: {promo.get('score', 0)}\n"
    texto += f"{promo.get('classification', '🟢 PROMOÇÃO BOA')}\n\n"
    texto += "Link:\n"
    texto += str(promo.get("link", ""))
    return texto


def format_lista(titulo: str, promocoes: list) -> str:
    if not promocoes:
        return f"{titulo}\n\nNenhuma promoção registrada ainda."

    partes = [titulo, ""]
    for promo in promocoes:
        partes.append("━━━━━━━━━━━━━━")
        partes.append(f"Programa: {promo.get('program', 'Programa não identificado')}")
        partes.append(f"Título: {promo.get('title', '')}")
        partes.append(f"Score: {promo.get('score', 0)}")
        partes.append(f"{promo.get('classification', '🟢 PROMOÇÃO BOA')}")
        partes.append("Link:")
        partes.append(str(promo.get("link", "")))
    partes.append("━━━━━━━━━━━━━━")
    return "\n".join(partes)


async def _run_scan() -> dict:
    async with SCAN_LOCK:
        result = await asyncio.to_thread(executar_varredura)

        novas = result.get("novas", [])
        detectadas = result.get("detectadas", 0)

        for promo in novas:
            await _APP.bot.send_message(
                chat_id=CANAL_ID,
                text=format_card(promo),
                disable_web_page_preview=True,
            )

        STATE.metricas["ultimos_alertas_enviados"] = len(novas)
        STATE.metricas["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.metricas["ultimo_erro"] = "nenhum"
        STATE.persistir()

        return {
            "detectadas": detectadas,
            "novas": len(novas),
        }


async def _scheduled_scan():
    try:
        await _run_scan()
    except Exception as e:
        STATE.metricas["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.metricas["ultimo_erro"] = str(e)
        STATE.persistir()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✈️ Radar de Milhas PRO\n\n"
        "/menu\n"
        "/promocoes\n"
        "/transferencias\n"
        "/passagens\n"
        "/ranking\n"
        "/status",
        disable_web_page_preview=True,
    )


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📡 MENU\n\n"
        "/promocoes\n"
        "/transferencias\n"
        "/passagens\n"
        "/ranking\n"
        "/status\n"
        "/testeradar\n"
        "/debug",
        disable_web_page_preview=True,
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        build_status_text(RADAR_INTERVAL_SECONDS),
        disable_web_page_preview=True,
    )


async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Comando disponível apenas para o administrador.")
        return

    await update.message.reply_text(build_debug_text(), disable_web_page_preview=True)


async def cmd_promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_ranking(limit=5)
    await update.message.reply_text(
        format_lista("🔥 Últimas promoções", promos),
        disable_web_page_preview=True,
    )


async def cmd_transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_promocoes_por_tipo("transferencias", limit=5)
    if not promos:
        texto = (
            "💳 Promoções de transferências de pontos monitoradas\n\n"
            "Nenhuma transferência promocional ativa detectada no momento."
        )
    else:
        texto = format_lista("💳 Promoções de transferências de pontos monitoradas", promos)

    await update.message.reply_text(texto, disable_web_page_preview=True)


async def cmd_passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_promocoes_por_tipo("passagens", limit=5)
    await update.message.reply_text(
        format_lista("✈️ Últimos alertas de passagens", promos),
        disable_web_page_preview=True,
    )


async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_ranking(limit=MAX_RANKING if MAX_RANKING < 6 else 5)

    if not promos:
        await update.message.reply_text(
            "🏆 Ranking promoções\n\nNenhuma promoção registrada ainda.",
            disable_web_page_preview=True,
        )
        return

    linhas = ["🏆 Ranking promoções", ""]
    medalhas = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣"}

    for i, promo in enumerate(promos, start=1):
        prefixo = medalhas.get(i, f"{i}.")
        linhas.append(
            f"{prefixo} {promo.get('program', 'Programa não identificado')} | "
            f"{promo.get('title', '')} | score {promo.get('score', 0)}"
        )

    await update.message.reply_text("\n".join(linhas), disable_web_page_preview=True)


async def cmd_testeradar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Comando disponível apenas para o administrador.")
        return

    if SCAN_LOCK.locked():
        await update.message.reply_text(
            "⏳ Já existe uma varredura em andamento. Aguarde terminar.",
            disable_web_page_preview=True,
        )
        return

    await update.message.reply_text("🧪 Teste manual do radar iniciado...", disable_web_page_preview=True)

    try:
        result = await _run_scan()
        await update.message.reply_text(
            "✅ Teste manual concluído.\n\n"
            f"Fontes monitoradas: {STATE.metricas.get('fontes_monitoradas', 0)}\n"
            f"Fontes ativas: {STATE.metricas.get('fontes_ativas', 0)}\n"
            f"Fontes com erro: {STATE.metricas.get('fontes_com_erro', 0)}\n"
            f"Promoções analisadas: {result.get('detectadas', 0)}\n"
            f"Novas promoções enviadas: {result.get('novas', 0)}\n"
            f"Último erro: {STATE.metricas.get('ultimo_erro', 'nenhum')}",
            disable_web_page_preview=True,
        )
    except Exception as e:
        STATE.metricas["ultimo_erro"] = str(e)
        STATE.persistir()
        await update.message.reply_text(
            f"❌ Erro ao executar o radar: {e}",
            disable_web_page_preview=True,
        )


async def post_init(application):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _scheduled_scan,
        "interval",
        seconds=RADAR_INTERVAL_SECONDS,
        next_run_time=datetime.now(),
        id="radar_scan",
        replace_existing=True,
    )
    scheduler.start()
    application.bot_data["scheduler"] = scheduler


async def post_shutdown(application):
    scheduler = application.bot_data.get("scheduler")
    if scheduler:
        scheduler.shutdown(wait=False)


_APP = None


def main():
    global _APP

    _APP = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    _APP.add_handler(CommandHandler("start", cmd_start))
    _APP.add_handler(CommandHandler("menu", cmd_menu))
    _APP.add_handler(CommandHandler("status", cmd_status))
    _APP.add_handler(CommandHandler("debug", cmd_debug))
    _APP.add_handler(CommandHandler("promocoes", cmd_promocoes))
    _APP.add_handler(CommandHandler("transferencias", cmd_transferencias))
    _APP.add_handler(CommandHandler("passagens", cmd_passagens))
    _APP.add_handler(CommandHandler("ranking", cmd_ranking))
    _APP.add_handler(CommandHandler("testeradar", cmd_testeradar))

    _APP.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
