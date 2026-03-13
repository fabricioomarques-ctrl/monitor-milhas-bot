from utils.texto import normalizar_texto


KEYWORDS_TRANSFERENCIA = [

    "transferencia bonificada",
    "bonus de transferencia",
    "bônus de transferência",

    "transferir pontos",
    "transfira seus pontos",

    "bonificada",
]


def detectar_transferencia(texto):

    texto = normalizar_texto(texto)

    for palavra in KEYWORDS_TRANSFERENCIA:

        if palavra in texto:
            return True

    return False
