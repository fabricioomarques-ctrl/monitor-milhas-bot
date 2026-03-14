from engine.radar_engine import get_state_snapshot


def build_status_text(interval_seconds: int) -> str:
    snapshot = get_state_snapshot()
    promocoes = snapshot["promocoes"]
    metricas = snapshot["metricas"]

    return (
        "🟢 Radar online\n\n"
        f"⏱ Intervalo do radar: {interval_seconds} segundos\n"
        f"📥 Promoções detectadas: {len(promocoes)}\n"
        f"🛰 Fontes monitoradas: {metricas.get('fontes_monitoradas', 0)}\n"
        f"✅ Fontes ativas: {metricas.get('fontes_ativas', 0)}\n"
        f"❌ Fontes com erro: {metricas.get('fontes_com_erro', 0)}\n\n"
        "Detectores ativos:\n"
        "✓ blogs\n"
        "✓ programas\n"
        "✓ milheiro\n"
        "✓ score automático\n"
        "✓ envio no canal\n\n"
        f"📤 Últimos alertas enviados: {metricas.get('ultimos_alertas_enviados', 0)}\n"
        f"🕒 Última execução: {metricas.get('ultima_execucao') or 'ainda não executado'}\n"
        f"⚠️ Último erro: {metricas.get('ultimo_erro', 'nenhum')}"
    )


def build_debug_text() -> str:
    snapshot = get_state_snapshot()
    metricas = snapshot["metricas"]
    falhas = metricas.get("falhas_fontes", {})

    texto = (
        "🛠 DEBUG RADAR\n"
        "━━━━━━━━━━━━━━\n\n"
        f"Fontes monitoradas: {metricas.get('fontes_monitoradas', 0)}\n"
        f"Fontes ativas: {metricas.get('fontes_ativas', 0)}\n"
        f"Fontes com erro: {metricas.get('fontes_com_erro', 0)}\n"
        f"Última execução: {metricas.get('ultima_execucao') or 'ainda não executado'}\n"
        f"Último erro geral: {metricas.get('ultimo_erro', 'nenhum')}\n\n"
        "Falhas por fonte\n"
        "━━━━━━━━━━━━━━\n\n"
    )

    if not falhas:
        texto += "Nenhuma falha crítica detectada."
    else:
        for fonte, erro in falhas.items():
            texto += f"• {fonte}: {erro}\n"

    return texto.strip()
