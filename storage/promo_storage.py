import json
import os
from typing import Any

from config import METRICS_FILE, PROMOCOES_FILE


def _load_json(path: str, default: Any):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_promocoes():
    data = _load_json(PROMOCOES_FILE, [])
    return data if isinstance(data, list) else []


def save_promocoes(data: list):
    _save_json(PROMOCOES_FILE, data)


def load_metrics():
    data = _load_json(
        METRICS_FILE,
        {
            "ultimos_alertas_enviados": 0,
            "ultima_execucao": None,
            "ultimo_erro": "nenhum",
            "fontes_monitoradas": 15,
            "fontes_ativas": 0,
            "fontes_com_erro": 0,
            "falhas_fontes": {},
        },
    )
    return data if isinstance(data, dict) else {}


def save_metrics(data: dict):
    _save_json(METRICS_FILE, data)
