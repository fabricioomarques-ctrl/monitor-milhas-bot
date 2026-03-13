from config import CONTEXTO_MILHEIRO, MILHEIRO_MAXIMO
from utils.texto import normalizar_texto, extrair_precos_reais


def detectar_milheiro_barato(item: dict) -> dict | None:
    texto_original = item.get("texto", "")
    texto = normalizar_texto(texto_original)

    if not any(normalizar_texto(c) in texto for c in CONTEXTO_MILHEIRO):
        return None

    precos = extrair_precos_reais(texto_original)

    if not precos:
        return None

    menor_preco = min(precos)

    if menor_preco > MILHEIRO_MAXIMO:
        return None

    return {
        "tipo": "milheiro_barato",
        "origem": item.get("origem", ""),
        "fonte": item.get("fonte", ""),
        "titulo": item.get("titulo", ""),
        "link": item.get("link", ""),
        "detalhe": f"Milheiro detectado por R$ {menor_preco:.2f}",
        "preco": menor_preco,
    }
