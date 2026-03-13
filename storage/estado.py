import json
import os

ARQUIVO_ESTADO = "promocoes_enviadas.json"
MAX_ITENS_ESTADO = 5000


def carregar_promocoes_enviadas():
    if not os.path.exists(ARQUIVO_ESTADO):
        return set()

    try:
        with open(ARQUIVO_ESTADO, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return set(data)

        return set()
    except Exception:
        return set()


def salvar_promocoes_enviadas(enviados):
    lista = list(enviados)

    if len(lista) > MAX_ITENS_ESTADO:
        lista = lista[-MAX_ITENS_ESTADO:]

    with open(ARQUIVO_ESTADO, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)
