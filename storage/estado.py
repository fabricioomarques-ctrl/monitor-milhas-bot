import json
import os

ARQUIVO_ESTADO = "promocoes_enviadas.json"


def carregar_promocoes_enviadas():

    if not os.path.exists(ARQUIVO_ESTADO):
        return set()

    try:

        with open(
            ARQUIVO_ESTADO,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return set(data)

        return set()

    except Exception:
        return set()


def salvar_promocoes_enviadas(enviados):

    with open(
        ARQUIVO_ESTADO,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            list(enviados),
            f,
            ensure_ascii=False,
            indent=2
        )
