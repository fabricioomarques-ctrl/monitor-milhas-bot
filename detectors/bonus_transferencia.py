from config import BONUS_MINIMO, KEYWORDS_TRANSFERENCIA
from utils.texto import normalizar_texto, extrair_numeros_percentuais


def detectar_bonus_transferencia(item):
    texto = normalizar_texto(item.get("texto", ""))
    titulo = item.get("titulo", "")
    link = item.get("link", "")
    fonte = item.get("fonte", "")
    origem = item.get("origem", "")

    if not any(normalizar_texto(k) in texto for k in KEYWORDS_TRANSFERENCIA):
        return None

    percentuais = extrair_numeros_percentuais(texto)

    if not percentuais:
        return None

    bonus = max(percentuais)

    if bonus < BONUS_MINIMO:
        return None

    return {
        "tipo": "transferencia_bonificada",
        "origem": origem,
        "fonte": fonte,
        "titulo": titulo,
        "link": link,
        "detalhe": f"Transferência bonificada com {bonus}% de bônus",
        "bonus": bonus,
        "score_base": bonus,
    }
