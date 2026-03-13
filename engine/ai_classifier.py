from utils.texto import normalizar_texto


def enriquecer_contexto(item: dict) -> dict:
    """
    Classificador heurístico avançado.
    Não depende só de regex: tenta inferir prioridade/contexto.
    """
    texto = normalizar_texto(f"{item.get('titulo', '')} {item.get('detalhe', '')} {item.get('texto', '')}")

    sinais_urgencia = [
        "somente hoje",
        "por tempo limitado",
        "ultimas horas",
        "últimas horas",
        "relampago",
        "relâmpago",
        "ultima chance",
        "última chance",
    ]

    sinais_oficiais = [
        "oficial",
        "programa",
        "clube",
    ]

    urgencia = any(s in texto for s in sinais_urgencia)
    oficial = any(s in texto for s in sinais_oficiais)

    item["ai_urgencia"] = urgencia
    item["ai_oficial"] = oficial

    return item
