from engine.radar_engine import get_state_snapshot


def build_status_text(interval_seconds: int) -> str:
    snapshot = get_state_snapshot()
    metrics = snapshot["metrics"]
    total_promos = len(snapshot["promocoes"])

    return (
        "🟢 Radar online\n\n"
        f"⏱ Intervalo do radar: {interval_seconds} segundos\n"
        f"📥 Promoções detectadas: {total_promos}\n"
        f"🛰 Fontes monitoradas: {metrics.get('fontes_monitoradas', 0)}\n"
        f"✅ Fontes ativas: {metrics.get('fontes_ativas', 0)}\n"
        f"❌ Fontes com erro: {metrics.get('fontes_com_erro', 0)}\n\n"
        "Detectores ativos:\n"
        "✓ blogs\n"
        "✓ programas\n"
        "✓ milheiro\n"
        "✓ redes sociais\n"
        "✓ confirmação múltipla\n"
        "✓ score automático\n"
        "✓ envio no canal\n\n"
        f"📤 Últimos alertas enviados: {metrics.get('ultimos_alertas_enviados', 0)}\n"
        f"🕒 Última execução: {metrics.get('ultima_execucao') or 'ainda não executado'}\n"
        f"⚠️ Último erro: {metrics.get('ultimo_erro', 'nenhum')}"
    )


def build_debug_text() -> str:
    snapshot = get_state_snapshot()
    metrics = snapshot["metrics"]
    falhas = metrics.get("falhas_fontes", {})

    lines = [
        "🛠 DEBUG RADAR",
        "━━━━━━━━━━━━━━",
        "",
        f"Fontes monitoradas: {metrics.get('fontes_monitoradas', 0)}",
        f"Fontes ativas: {metrics.get('fontes_ativas', 0)}",
        f"Fontes com erro: {metrics.get('fontes_com_erro', 0)}",
        f"Última execução: {metrics.get('ultima_execucao') or 'ainda não executado'}",
        f"Último erro geral: {metrics.get('ultimo_erro', 'nenhum')}",
        "",
        "Falhas por fonte",
        "━━━━━━━━━━━━━━",
        "",
    ]

    if not falhas:
        lines.append("Nenhuma falha crítica detectada.")
    else:
        for nome, erro in falhas.items():
            lines.append(f"• {nome}: {erro}")
            lines.append("")

    return "\n".join(lines).strip()
