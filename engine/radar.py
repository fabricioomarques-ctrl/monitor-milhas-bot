from collectors.blogs import coletar_blogs
from collectors.programas import coletar_programas
from collectors.bancos import coletar_bancos

from detectors.noise_filter import is_noise
from detectors.bonus_transferencia import detectar_bonus_transferencia
from detectors.milheiro_barato import detectar_milheiro_barato
from detectors.passagens import detectar_passagem_barata

from engine.scoring import ordenar_resultados


def coletar_tudo():
    dados = []
    dados.extend(coletar_blogs())
    dados.extend(coletar_programas())
    dados.extend(coletar_bancos())
    return dados


def deduplicar_por_link(itens):
    vistos = set()
    saida = []

    for item in itens:
        link = item.get("link", "").strip()

        if not link or link in vistos:
            continue

        vistos.add(link)
        saida.append(item)

    return saida


def executar_radar():
    dados_brutos = coletar_tudo()
    oportunidades = []

    for item in dados_brutos:
        texto = item.get("texto", "")
        titulo = item.get("titulo", "")
        combinado = f"{titulo} {texto}"

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

    oportunidades = deduplicar_por_link(oportunidades)
    oportunidades = ordenar_resultados(oportunidades)

    return oportunidades
