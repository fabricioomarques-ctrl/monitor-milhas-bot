import json
import os

ARQUIVO_ALERTAS = "promocoes_enviadas.json"
MAX_ITENS = 5000


def carregar_alertas_enviados() -> set:
    if not os.path.exists(ARQUIVO_ALERTAS):
        return set()

    try:
        with open(ARQUIVO_ALERTAS, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return set(data)

        return set()

    except Exception:
        return set()


def salvar_alertas_enviados(alertas: set) -> None:
    lista = list(alertas)

    if len(lista) > MAX_ITENS:
        lista = lista[-MAX_ITENS:]

    with open(ARQUIVO_ALERTAS, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)
