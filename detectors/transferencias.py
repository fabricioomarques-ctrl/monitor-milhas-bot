from config import BONUS_MINIMO, KEYWORDS_TRANSFERENCIA
from utils.texto import normalizar_texto, extrair_percentuais


def detectar_transferencia(item: dict) -> dict | None:
    texto = normalizar_texto(item.get("texto", ""))

    if not any(normalizar_texto(k) in texto for k in KEYWORDS_TRANSFERENCIA):
        return None

    percentuais = extrair_percentuais(texto)

    if not percentuais:
        return None

    bonus = max(percentuais)

    if bonus < BONUS_MINIMO:
        return None

    return {
        "tipo": "transferencia_bonificada",
        "origem": item.get("origem", ""),
        "fonte": item.get("fonte", ""),
        "titulo": item.get("titulo", ""),
        "link": item.get("link", ""),
        "detalhe": f"Transferência bonificada com {bonus}% de bônus",
        "bonus": bonus,
    }
