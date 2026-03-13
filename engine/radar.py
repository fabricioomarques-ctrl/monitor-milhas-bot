from collections import defaultdict

from config import TRUSTED_BLOG_SOURCES

from collectors.blogs import coletar_blogs
from collectors.programas import coletar_programas
from collectors.bancos import coletar_bancos
from collectors.milheiro import coletar_milheiro
from collectors.social import coletar_social

from detectors.noise_filter import is_noise
from detectors.bonus_transferencia import detectar_bonus_transferencia
from detectors.milheiro_barato import detectar_milheiro_barato
from detectors.passagens import detectar_passagem_barata

from engine.scoring import ordenar_resultados, chave_confirmacao


def coletar_tudo():
    dados = []
    dados.extend(coletar_blogs())
    dados.extend(coletar_programas())
    dados.extend(coletar_bancos())
    dados.extend(coletar_milheiro())
    dados.extend(coletar_social())
    return dados


def detectar_oportunidades(dados_brutos):
    oportunidades = []

    for item in dados_brutos:
        combinado = f"{item.get('titulo', '')} {item.get('texto', '')}"

        if is_noise(combinado):
            continue

        bonus = detectar_bonus_transferencia(item)
        if bonus:
            oportunidades.append(bonus)

        milheiro = detectar_milheiro_barato(item)
        if milheiro:
            oportunidades.append(milheiro)

        passagem = detectar_passagem_barata(item)
        if passagem:
            oportunidades.append(passagem)

    return oportunidades


def confirmar_multi_fonte(oportunidades):
    """
    Regra fiel ao espírito do projeto:
    - fonte oficial (programa/banco) confirma
    - blog confiável também pode confirmar sozinho
    - ou 2 origens distintas confirmam
    """
    agrupados = defaultdict(list)

    for item in oportunidades:
        chave = chave_confirmacao(item)
        agrupados[chave].append(item)

    confirmados = []

    for _, itens in agrupados.items():
        origens = {i.get("origem", "") for i in itens}
        fontes = {i.get("fonte", "") for i in itens}

        confirmado = False

        # 1) fonte oficial confirma
        if "programa" in origens or "banco" in origens:
            confirmado = True

        # 2) blog confiável também confirma
        if not confirmado and any(f in TRUSTED_BLOG_SOURCES for f in fontes):
            confirmado = True

        # 3) duas origens distintas também confirmam
        if not confirmado and len(origens) >= 2:
            confirmado = True

        if not confirmado:
            continue

        melhor = itens[0]
        melhor["confirmado_fontes"] = len(fontes)
        melhor["fontes_detectadas"] = sorted(list(fontes))
        confirmados.append(melhor)

    return confirmados


def executar_radar():
    dados_brutos = coletar_tudo()
    oportunidades = detectar_oportunidades(dados_brutos)
    oportunidades = confirmar_multi_fonte(oportunidades)
    oportunidades = ordenar_resultados(oportunidades)

    return oportunidades
