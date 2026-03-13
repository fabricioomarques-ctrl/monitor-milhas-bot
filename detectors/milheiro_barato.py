import re

from utils.texto import normalizar_texto


PRECO_REGEX = re.compile(
    r"r\$\s*(\d{1,2}(?:[.,]\d{1,2})?)"
)

CONTEXTOS_MILHEIRO = [
    "milheiro",
    "milheiros",
    "milha",
    "milhas",
    "1000 milhas",
    "1.000 milhas",
    "compra de milhas",
    "venda de milhas",
    "lote de milhas",
    "preco do milheiro",
    "preço do milheiro",
]


def detectar_milheiro_barato(texto, teto=18.0):
    texto = normalizar_texto(texto)

    # primeiro exige contexto real de milhas
    tem_contexto = any(contexto in texto for contexto in CONTEXTOS_MILHEIRO)

    if not tem_contexto:
        return None

    match = PRECO_REGEX.search(texto)

    if not match:
        return None

    try:
        valor = float(match.group(1).replace(",", "."))
    except Exception:
        return None

    if valor <= teto:
        return valor

    return None
