from collectors.fetchers import coletar_todas_fontes
from detectors.promo_detector import transformar_em_promocoes
from storage.promo_storage import salvar_promocoes, carregar_promocoes
from storage.deduplicador import deduplicar


def executar_radar():

    # coleta de dados
    itens = coletar_todas_fontes()

    if not itens:
        return []

    # transforma em promoções detectadas
    promocoes = transformar_em_promocoes(itens)

    if not promocoes:
        return []

    # remove duplicadas
    promocoes = deduplicar(promocoes)

    # carrega histórico
    historico = carregar_promocoes()

    novas = []

    for p in promocoes:

        if p["id"] not in historico:
            novas.append(p)

    # salva histórico atualizado
    salvar_promocoes(promocoes)

    return novas


def get_status():

    promocoes = carregar_promocoes()

    return {
        "total": len(promocoes)
    }
