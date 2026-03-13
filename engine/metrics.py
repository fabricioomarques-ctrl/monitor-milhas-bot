import json
import os
from datetime import datetime

ARQUIVO_METRICS = "dashboard_metrics.json"


def _base_inicial():
    return {
        "last_run": "",
        "sources_monitored": 0,
        "sources_active": 0,
        "sources_error": 0,
        "sources": [],
        "items_collected": 0,
        "items_discarded": 0,
        "items_detected": 0,
        "items_sent": 0,
        "discard_reasons": {},
        "last_results": [],
        "last_error": "",
        "detectors_active": [
            "blogs",
            "programas",
            "milheiro",
            "redes sociais",
            "confirmacao multipla",
            "score automatico",
            "envio no canal",
        ],
    }


def carregar_metrics():
    if not os.path.exists(ARQUIVO_METRICS):
        return _base_inicial()

    try:
        with open(ARQUIVO_METRICS, "r", encoding="utf-8") as f:
            data = json.load(f)

        base = _base_inicial()
        base.update(data)
        return base
    except Exception:
        return _base_inicial()


def salvar_metrics(metrics: dict):
    with open(ARQUIVO_METRICS, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)


def criar_metrics_execucao():
    base = _base_inicial()
    base["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return base


def registrar_fontes(metrics: dict, fontes_meta: list[dict]):
    metrics["sources"] = fontes_meta
    metrics["sources_monitored"] = len(fontes_meta)
    metrics["sources_active"] = len([f for f in fontes_meta if f.get("status") == "ok"])
    metrics["sources_error"] = len([f for f in fontes_meta if f.get("status") == "erro"])


def registrar_coleta(metrics: dict, quantidade: int):
    metrics["items_collected"] = quantidade


def registrar_descarte(metrics: dict, motivo: str):
    metrics["items_discarded"] += 1
    metrics["discard_reasons"][motivo] = metrics["discard_reasons"].get(motivo, 0) + 1


def registrar_detectados(metrics: dict, quantidade: int):
    metrics["items_detected"] = quantidade


def registrar_enviados(metrics: dict, quantidade: int):
    metrics["items_sent"] = quantidade


def registrar_resultados(metrics: dict, resultados: list[dict], limite: int = 10):
    metrics["last_results"] = resultados[:limite]


def registrar_erro(metrics: dict, erro: str):
    metrics["last_error"] = erro
