from collectors.blogs import coletar_blogs
from collectors.programas import coletar_programas
from collectors.bancos import coletar_bancos
from collectors.milheiro import coletar_milheiro
from collectors.social import coletar_social

from detectors.noise_filter import is_noise
from detectors.transferencias import detectar_transferencia
from detectors.passagens import detectar_passagem
from detectors.milheiro_barato import detectar_milheiro_barato

from engine.confirmador import confirmar_multi_fonte
from engine.scoring import ordenar_resultados


def coletar_tudo() -> list[dict]:
    dados = []
    dados.extend(coletar_blogs())
    dados.extend(coletar_programas())
    dados.extend(coletar_bancos())
    dados.extend(coletar_milheiro())
    dados.extend(coletar_social())
    return dados


def detectar_oportunidades(dados_brutos: list[dict]) -> list[dict]:
    oportunidades = []

    for item in dados_brutos:
        combinado = f"{item.get('titulo', '')} {item.get('texto', '')}"

        if is_noise(combinado):
            continue

        transferencia = detectar_transferencia(item)
        if transferencia:
            oportunidades.append(transferencia)

        passagem = detectar_passagem(item)
        if passagem:
            oportunidades.append(passagem)

        milheiro = detectar_milheiro_barato(item)
        if milheiro:
            oportunidades.append(milheiro)

    return oportunidades


def executar_radar() -> list[dict]:
    dados_brutos = coletar_tudo()
    oportunidades = detectar_oportunidades(dados_brutos)
    oportunidades = confirmar_multi_fonte(oportunidades)
    oportunidades = ordenar_resultados(oportunidades)

    return oportunidades
