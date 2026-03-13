import json
import os
import time

from config import JANELA_REPETICAO_HORAS

ARQUIVO_ALERTAS = "promocoes_enviadas.json"
MAX_ITENS = 10000
JANELA_REPETICAO_SEGUNDOS = JANELA_REPETICAO_HORAS * 3600


def _normalizar_base(data):
    if isinstance(data, dict):
        saida = {}
        for chave, valor in data.items():
            try:
                saida[str(chave)] = float(valor)
            except Exception:
                continue
        return saida

    if isinstance(data, list):
        agora = time.time()
        return {str(item): agora for item in data}

    return {}


def carregar_alertas_enviados() -> dict:
    if not os.path.exists(ARQUIVO_ALERTAS):
        return {}

    try:
        with open(ARQUIVO_ALERTAS, "r", encoding="utf-8") as f:
            data = json.load(f)

        return limpar_expirados(_normalizar_base(data))
    except Exception:
        return {}


def salvar_alertas_enviados(alertas: dict) -> None:
    base = limpar_expirados(dict(alertas))

    if len(base) > MAX_ITENS:
        itens_ordenados = sorted(base.items(), key=lambda x: x[1], reverse=True)
        base = dict(itens_ordenados[:MAX_ITENS])

    with open(ARQUIVO_ALERTAS, "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)


def limpar_expirados(alertas: dict) -> dict:
    agora = time.time()

    return {
        chave: timestamp
        for chave, timestamp in alertas.items()
        if (agora - float(timestamp)) < JANELA_REPETICAO_SEGUNDOS
    }


def foi_enviado_recentemente(chave: str, alertas: dict) -> bool:
    alertas_limpos = limpar_expirados(alertas)
    return chave in alertas_limpos


def registrar_envio(chave: str, alertas: dict) -> dict:
    alertas[chave] = time.time()
    return alertas
