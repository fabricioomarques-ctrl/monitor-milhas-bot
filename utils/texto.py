import re
import unicodedata


def normalizar_texto(texto):

    texto = str(texto or "").strip().lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    ).encode(
        "ascii",
        "ignore"
    ).decode(
        "ascii"
    )

    texto = re.sub(r"\s+", " ", texto)

    return texto


def limpar_espacos(texto):

    return re.sub(
        r"\s+",
        " ",
        str(texto or "")
    ).strip()
