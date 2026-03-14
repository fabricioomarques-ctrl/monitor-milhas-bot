import json
import os
from typing import Any

from config import METRICS_FILE, PROMOCOES_FILE


def _ensure_json_file(path: str, default: Any) -> None:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)


def _load_json(path: str, default: Any) -> Any:
    _ensure_json_file(path, default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def carregar_promocoes() -> list:
    data = _load_json(PROMOCOES_FILE, [])
    return data if isinstance(data, list) else []


def salvar_promocoes(promocoes: list) -> None:
    if not isinstance(promocoes, list):
        promocoes = []
    _save_json(PROMOCOES_FILE, promocoes)


def carregar_metricas() -> dict:
    data = _load_json(
        METRICS_FILE,
        {
            "fontes_monitoradas": 0,
            "fontes_ativas": 0,
            "fontes_com_erro": 0,
            "ultimos_alertas_enviados": 0,
            "ultima_execucao": None,
            "ultimo_erro": "nenhum",
            "falhas_fontes": {},
        },
    )
    return data if isinstance(data, dict) else {}


def salvar_metricas(metricas: dict) -> None:
    if not isinstance(metricas, dict):
        metricas = {}
    _save_json(METRICS_FILE, metricas)
