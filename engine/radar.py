from collectors.blogs import coletar_blogs
from collectors.programas import coletar_programas
from collectors.bancos import coletar_bancos

from detectors.bonus_transferencia import detectar_bonus_transferencia
from detectors.milheiro_barato import detectar_milheiro_barato


def executar_radar():

    resultados = []

    resultados += coletar_blogs()
    resultados += coletar_programas()
    resultados += coletar_bancos()

    bonus = detectar_bonus_transferencia(resultados)
    milheiros = detectar_milheiro_barato(resultados)

    resultados += bonus
    resultados += milheiros

    return resultados
