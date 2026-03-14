from collectors.fetchers import coletar_todas_fontes
from detectors.promo_detector import transformar_em_promocoes
from storage.promo_storage import carregar_promocoes, salvar_promocoes
from storage.deduplicador import deduplicar


def executar_radar():
    itens = coletar_todas_fontes()

    if not itens:
        return []

    promocoes = transformar_em_promocoes(itens)

    if not promocoes:
        return []

    promocoes = deduplicar(promocoes)

    historico = carregar_promocoes()

    ids_existentes = {p.get("id") for p in historico}

    novas = []

    for promo in promocoes:
        if promo.get("id") not in ids_existentes:
            novas.append(promo)
            historico.append(promo)

    salvar_promocoes(historico)

    return novas


def get_state_snapshot():
    """
    Usado pelo status_builder para mostrar estado atual do radar
    """

    promocoes = carregar_promocoes()

    total = len(promocoes)

    por_tipo = {
        "passagens": 0,
        "transferencias": 0,
        "milheiro": 0,
    }

    for p in promocoes:
        tipo = p.get("type")

        if tipo in por_tipo:
            por_tipo[tipo] += 1

    return {
        "total_promocoes": total,
        "passagens": por_tipo["passagens"],
        "transferencias": por_tipo["transferencias"],
        "milheiro": por_tipo["milheiro"],
    }
