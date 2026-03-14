import asyncio
from datetime import datetime

from collectors.fetchers import collect_html, collect_rss
from collectors.sources import FONTES
from detectors.promo_detector import (
    dedupe_by_signature,
    format_promo_card,
    promo_resumo_ranking,
    transformar_em_promocoes,
)
from storage.promo_storage import (
    load_metrics,
    load_promocoes,
    save_metrics,
    save_promocoes,
)


class RadarState:
    def __init__(self):
        self.promocoes = load_promocoes()
        self.metrics = load_metrics()
        self.sent_ids = {p["id"] for p in self.promocoes if isinstance(p, dict) and "id" in p}

        self.metrics.setdefault("ultimos_alertas_enviados", 0)
        self.metrics.setdefault("ultima_execucao", None)
        self.metrics.setdefault("ultimo_erro", "nenhum")
        self.metrics.setdefault("fontes_monitoradas", len(FONTES))
        self.metrics.setdefault("fontes_ativas", 0)
        self.metrics.setdefault("fontes_com_erro", 0)
        self.metrics.setdefault("falhas_fontes", {})

        # já nasce com o total real
        self.metrics["fontes_monitoradas"] = len(FONTES)

    def persist(self):
        save_promocoes(self.promocoes)
        save_metrics(self.metrics)


STATE = RadarState()


def _collect_all_sources_sync():
    results = []
    fontes_ativas = 0
    fontes_com_erro = 0
    falhas = {}

    for source in FONTES:
        try:
            if source["type"] == "rss":
                data = collect_rss(source)
            else:
                data = collect_html(source)

            fontes_ativas += 1

            if data:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for item in data:
                    item["created_at"] = now
                results.extend(data)

        except Exception as e:
            optional = source.get("optional", False)
            if not optional:
                fontes_com_erro += 1
                falhas[source["name"]] = str(e)[:180]

    STATE.metrics["fontes_monitoradas"] = len(FONTES)
    STATE.metrics["fontes_ativas"] = fontes_ativas
    STATE.metrics["fontes_com_erro"] = fontes_com_erro
    STATE.metrics["falhas_fontes"] = falhas

    return results


def _transform_sync(raw_items):
    return transformar_em_promocoes(raw_items)


def _add_if_new(promo: dict) -> bool:
    if promo["id"] in STATE.sent_ids:
        return False

    if not isinstance(STATE.promocoes, list):
        STATE.promocoes = []

    STATE.promocoes.insert(0, promo)
    STATE.sent_ids.add(promo["id"])
    STATE.promocoes = STATE.promocoes[:400]
    return True


async def run_radar(bot):
    try:
        # roda coleta bloqueante fora do loop principal
        raw_items = await asyncio.to_thread(_collect_all_sources_sync)

        # roda classificação pesada fora do loop principal
        promotions = await asyncio.to_thread(_transform_sync, raw_items)

        novas_reais = 0

        for promo in promotions:
            if _add_if_new(promo):
                await bot.send_message(
                    chat_id=bot._radar_channel_id,
                    text=format_promo_card(promo),
                    disable_web_page_preview=True,
                )
                novas_reais += 1

        STATE.metrics["ultimos_alertas_enviados"] = novas_reais
        STATE.metrics["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.metrics["ultimo_erro"] = "nenhum"
        STATE.persist()

        return {
            "analisadas": len(promotions),
            "novas_enviadas": novas_reais,
            "erro": "nenhum",
        }

    except Exception as e:
        STATE.metrics["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.metrics["ultimo_erro"] = str(e)[:250]
        STATE.persist()

        return {
            "analisadas": 0,
            "novas_enviadas": 0,
            "erro": str(e)[:250],
        }


def get_state_snapshot():
    return {
        "promocoes": STATE.promocoes,
        "metrics": STATE.metrics,
    }


def get_latest_promocoes(limit=5):
    promos = [p for p in STATE.promocoes if p["type"] in ("promocoes", "milheiro", "passagens")]
    return dedupe_by_signature(promos, limit)


def get_latest_transferencias(limit=5):
    promos = [p for p in STATE.promocoes if p["type"] == "transferencias"]
    return dedupe_by_signature(promos, limit)


def get_latest_passagens(limit=5):
    promos = [p for p in STATE.promocoes if p["type"] == "passagens"]
    return dedupe_by_signature(promos, limit)


def get_ranking(limit=5):
    promos = sorted(STATE.promocoes, key=lambda p: p["score"], reverse=True)
    return dedupe_by_signature(promos, limit)


def build_promocoes_text(limit=5):
    promos = get_latest_promocoes(limit)
    if not promos:
        return "🔥 Últimas promoções\n\nNenhuma promoção registrada ainda."

    lines = ["🔥 Últimas promoções", ""]
    for promo in promos:
        lines.append(format_promo_card(promo))
        lines.append("")
    return "\n".join(lines).strip()


def build_transferencias_text(limit=5):
    promos = get_latest_transferencias(limit)
    if not promos:
        return (
            "💳 Promoções de transferências de pontos monitoradas\n\n"
            "• Livelo\n"
            "• LATAM Pass\n"
            "• Smiles\n"
            "• TudoAzul\n\n"
            "Bancos monitorados:\n"
            "• Itaú\n"
            "• Bradesco\n"
            "• Santander\n"
            "• Banco do Brasil\n"
            "• C6 Bank\n\n"
            "Use /promocoes para ver ofertas atuais."
        )

    lines = ["💳 Promoções de transferências de pontos monitoradas", ""]
    for promo in promos:
        lines.append("━━━━━━━━━━━━━━")
        lines.append(f"Programa: {promo['program']}")
        lines.append(f"Título: {promo['title']}")
        lines.append(f"Score: {promo['score']}")
        lines.append(promo["classification"])
        lines.append("Link:")
        lines.append(promo["link"])
    lines.append("━━━━━━━━━━━━━━")
    return "\n".join(lines)


def build_passagens_text(limit=5):
    promos = get_latest_passagens(limit)
    if not promos:
        return "✈️ Últimos alertas de passagens\n\nNenhuma promoção registrada ainda."

    lines = ["✈️ Últimos alertas de passagens", ""]
    for promo in promos:
        lines.append("━━━━━━━━━━━━━━")
        lines.append(f"Programa: {promo['program']}")
        lines.append(f"Título: {promo['title']}")
        lines.append(f"Score: {promo['score']}")
        lines.append(promo["classification"])
        lines.append("Link:")
        lines.append(promo["link"])
    lines.append("━━━━━━━━━━━━━━")
    return "\n".join(lines)


def build_ranking_text(limit=5):
    promos = get_ranking(limit)
    if not promos:
        return "🏆 Ranking promoções\n\nNenhuma promoção registrada ainda."

    medals = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣"}
    lines = ["🏆 Ranking promoções", ""]
    for idx, promo in enumerate(promos, start=1):
        prefix = medals.get(idx, f"{idx}.")
        lines.append(f"{prefix} {promo_resumo_ranking(promo)}")
    return "\n".join(lines)
