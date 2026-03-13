from collections import defaultdict

from config import TRUSTED_BLOG_SOURCES
from engine.scoring import chave_confirmacao


def confirmar_multi_fonte(oportunidades: list[dict]) -> list[dict]:
    agrupados = defaultdict(list)

    for item in oportunidades:
        chave = chave_confirmacao(item)
        agrupados[chave].append(item)

    confirmados = []

    for _, itens in agrupados.items():
        origens = {i.get("origem", "") for i in itens}
        fontes = {i.get("fonte", "") for i in itens}

        confirmado = False

        if "programa" in origens or "banco" in origens:
            confirmado = True

        if not confirmado and any(f in TRUSTED_BLOG_SOURCES for f in fontes):
            confirmado = True

        if not confirmado and len(origens) >= 2:
            confirmado = True

        if not confirmado:
            continue

        melhor = itens[0]
        melhor["confirmado_fontes"] = len(fontes)
        melhor["fontes_detectadas"] = sorted(list(fontes))
        confirmados.append(melhor)

    return confirmados
