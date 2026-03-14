from collectors.fetchers import coletar_todas_fontes
from detectors.promo_detector import transformar_em_promocoes
from storage.deduplicador import deduplicar
from storage.promo_storage import (
    carregar_metricas,
    carregar_promocoes,
    salvar_metricas,
    salvar_promocoes,
)


class RadarState:
    def __init__(self):
        self.promocoes = carregar_promocoes()
        self.metricas = carregar_metricas()

        self.metricas.setdefault("fontes_monitoradas", 0)
        self.metricas.setdefault("fontes_ativas", 0)
        self.metricas.setdefault("fontes_com_erro", 0)
        self.metricas.setdefault("ultimos_alertas_enviados", 0)
        self.metricas.setdefault("ultima_execucao", None)
        self.metricas.setdefault("ultimo_erro", "nenhum")
        self.metricas.setdefault("falhas_fontes", {})

    def persistir(self):
        salvar_promocoes(self.promocoes)
        salvar_metricas(self.metricas)


STATE = RadarState()


def executar_varredura():
    itens, falhas = coletar_todas_fontes()

    fontes_monitoradas = 4
    fontes_com_erro = len(falhas)
    fontes_ativas = max(fontes_monitoradas - fontes_com_erro, 0)

    STATE.metricas["fontes_monitoradas"] = fontes_monitoradas
    STATE.metricas["fontes_ativas"] = fontes_ativas
    STATE.metricas["fontes_com_erro"] = fontes_com_erro
    STATE.metricas["falhas_fontes"] = falhas

    promocoes_detectadas = transformar_em_promocoes(itens)
    promocoes_detectadas = deduplicar(promocoes_detectadas)

    historico = carregar_promocoes()
    ids_existentes = {p.get("id") for p in historico}

    novas = []
    for promo in promocoes_detectadas:
        if promo.get("id") not in ids_existentes:
            novas.append(promo)
            historico.append(promo)

    historico = deduplicar(historico)
    STATE.promocoes = historico[-400:] if len(historico) > 400 else historico

    return {
        "novas": novas,
        "detectadas": len(promocoes_detectadas),
    }


def get_state_snapshot():
    STATE.promocoes = carregar_promocoes()
    STATE.metricas = carregar_metricas()

    return {
        "promocoes": STATE.promocoes,
        "metricas": STATE.metricas,
    }


def get_promocoes_por_tipo(tipo: str, limit: int = 5) -> list:
    snapshot = get_state_snapshot()
    promos = [p for p in snapshot["promocoes"] if p.get("type") == tipo]
    promos = sorted(promos, key=lambda p: p.get("score", 0), reverse=True)
    return promos[:limit]


def get_ranking(limit: int = 5) -> list:
    snapshot = get_state_snapshot()
    promos = sorted(snapshot["promocoes"], key=lambda p: p.get("score", 0), reverse=True)
    return promos[:limit]
