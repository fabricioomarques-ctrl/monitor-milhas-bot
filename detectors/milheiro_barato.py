import re

from utils.texto import normalizar_texto


PRECO_REGEX = re.compile(
    r"r\$\s*(\d{1,2}(?:[.,]\d{1,2})?)"
)


def detectar_milheiro_barato(
    texto,
    teto=18.0
):

    texto = normalizar_texto(texto)

    match = PRECO_REGEX.search(texto)

    if not match:
        return None

    try:

        valor = float(
            match.group(1).replace(",", ".")
        )

    except Exception:
        return None

    if valor <= teto:
        return valor

    return None
