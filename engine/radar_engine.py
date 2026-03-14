from datetime import datetime

from collectors.fetchers import collect_html, collect_rss
from collectors.sources import FONTES
from detectors.promo_detector import transformar_em_promocoes
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

        self.sent_ids = set()

        for p in self.promocoes:
            if "id" in p:
                self.sent_ids.add(p["id"])

    def save(self):

        save_promocoes(self.promocoes)
        save_metrics(self.metrics)


STATE = RadarState()


def coletar_fontes():

    resultados = []

    fontes_ativas = 0
    fontes_com_erro = 0

    falhas = {}

    for fonte in FONTES:

        try:

            if fonte["type"] == "rss":
                itens = collect_rss(fonte)

            else:
                itens = collect_html(fonte)

            fontes_ativas += 1

            resultados.extend(itens)

        except Exception as e:

            fontes_com_erro += 1

            falhas[fonte["name"]] = str(e)

    STATE.metrics["fontes_monitoradas"] = len(FONTES)
    STATE.metrics["fontes_ativas"] = fontes_ativas
    STATE.metrics["fontes_com_erro"] = fontes_com_erro
    STATE.metrics["falhas_fontes"] = falhas

    return resultados


async def executar_radar(bot):

    try:

        dados = coletar_fontes()

        promos = transformar_em_promocoes(dados)

        novas = 0

        for promo in promos:

            if promo["id"] in STATE.sent_ids:
                continue

            await bot.send_message(
                chat_id=bot._radar_channel_id,
                text=promo["message"],
                disable_web_page_preview=True
            )

            STATE.promocoes.insert(0, promo)

            STATE.sent_ids.add(promo["id"])

            novas += 1

        STATE.metrics["ultimos_alertas_enviados"] = novas

        STATE.metrics["ultima_execucao"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        STATE.metrics["ultimo_erro"] = "nenhum"

        STATE.save()

        return novas

    except Exception as e:

        STATE.metrics["ultimo_erro"] = str(e)

        STATE.save()

        return 0
