from config import NOISE_WORDS
from utils.texto import normalizar_texto


def is_noise(texto: str) -> bool:
    texto = normalizar_texto(texto)

    for palavra in NOISE_WORDS:
        if normalizar_texto(palavra) in texto:
            return True

    return False
