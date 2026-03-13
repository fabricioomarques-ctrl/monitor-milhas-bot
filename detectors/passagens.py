from config import KEYWORDS_PASSAGEM, PASSAGEM_MILHAS_MAX
from utils.texto import normalizar_texto, extrair_valores_milhas


def detectar_passagem_barata(item):
    texto = normalizar_texto(item.get("texto", ""))

    if not any(normalizar_texto(k) in texto for k in KEYWORDS_PASSAGEM):
        return None

    valores = extrair_valores_milhas(texto)

    if not valores:
        return None

    menor = min(valores)

    if menor > PASSAGEM_MILHAS_MAX:
        return None

    return {
        "tipo": "passagem_barata",
        "origem": item.get("origem", ""),
        "fonte": item.get("fonte", ""),
        "titulo": item.get("titulo", ""),
        "link": item.get("link", ""),
        "detalhe": f"Passagem detectada por {menor} milhas",
        "milhas": menor,
    }
