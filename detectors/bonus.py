import re

from utils.texto import normalizar_texto


BONUS_REGEX = re.compile(
    r"\b(30|40|50|60|70|80|85|90|95|100|110|120|150|200)%\b"
)


def detectar_bonus(texto):

    texto = normalizar_texto(texto)

    match = BONUS_REGEX.search(texto)

    if not match:
        return None

    try:
        return int(match.group(1))
    except Exception:
        return None
