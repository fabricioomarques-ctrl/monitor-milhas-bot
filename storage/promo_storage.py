import json
import os


ARQUIVO_PROMOCOES = "promocoes_enviadas.json"


def _garantir_arquivo():
    if not os.path.exists(ARQUIVO_PROMOCOES):
        with open(ARQUIVO_PROMOCOES, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def carregar_promocoes():
    _garantir_arquivo()

    try:
        with open(ARQUIVO_PROMOCOES, "r", encoding="utf-8") as f:
            dados = json.load(f)

        if isinstance(dados, list):
            return dados

        return []

    except Exception:
        return []


def salvar_promocoes(promocoes):
    _garantir_arquivo()

    if not isinstance(promocoes, list):
        promocoes = []

    try:
        with open(ARQUIVO_PROMOCOES, "w", encoding="utf-8") as f:
            json.dump(promocoes, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
