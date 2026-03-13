from collectors.rss import coletar_rss
from collectors.programas import coletar_programas
from collectors.milheiro import coletar_milheiro
from collectors.social import coletar_social

from detectors.bonus import detectar_bonus
from detectors.transferencia import detectar_transferencia
from detectors.milheiro_barato import detectar_milheiro_barato


def coletar_tudo():

    dados = []

    dados.extend(coletar_rss())
    dados.extend(coletar_programas())
    dados.extend(coletar_milheiro())
    dados.extend(coletar_social())

    return dados


def classificar_item(item):

    texto = item.get("texto", "")

    bonus = detectar_bonus(texto)

    milheiro = detectar_milheiro_barato(texto)

    transferencia = detectar_transferencia(texto)

    if bonus is not None and bonus >= 80:

        return {
            "tipo": "bonus_alto",
            "titulo": item["titulo"],
            "link": item["link"],
            "fonte": item["fonte"],
            "detalhe": f"{bonus}% de bônus detectado",
        }

    if transferencia and bonus is not None and bonus >= 70:

        return {
            "tipo": "transferencia_bonificada",
            "titulo": item["titulo"],
            "link": item["link"],
            "fonte": item["fonte"],
            "detalhe": f"Transferência bonificada com {bonus}% de bônus",
        }

    if milheiro is not None:

        return {
            "tipo": "milheiro_barato",
            "titulo": item["titulo"],
            "link": item["link"],
            "fonte": item["fonte"],
            "detalhe": f"Milheiro detectado por R$ {milheiro:.2f}",
        }

    return None


def executar_radar():

    dados = coletar_tudo()

    resultados = []

    for item in dados:

        r = classificar_item(item)

        if r:
            resultados.append(r)

    return resultados
