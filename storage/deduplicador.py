from datetime import datetime, timedelta

from config import JANELA_REPETICAO_HORAS


def _parse_data(valor):
    if not valor:
        return None

    if isinstance(valor, datetime):
        return valor

    formatos = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formatos:
        try:
            return datetime.strptime(str(valor), fmt)
        except Exception:
            continue

    return None


def _norm(texto):
    return " ".join(str(texto or "").lower().strip().split())


def _assinatura(promo: dict) -> str:
    return "|".join(
        [
            _norm(promo.get("type")),
            _norm(promo.get("program")),
            _norm(promo.get("title")),
            _norm(promo.get("link")),
        ]
    )


def deduplicar(promocoes: list) -> list:
    if not isinstance(promocoes, list):
        return []

    janela = timedelta(hours=JANELA_REPETICAO_HORAS)
    ordenadas = sorted(
        promocoes,
        key=lambda p: _parse_data(p.get("created_at")) or datetime.min,
        reverse=True,
    )

    resultado = []
    vistos = {}

    for promo in ordenadas:
        assinatura = _assinatura(promo)
        data_atual = _parse_data(promo.get("created_at")) or datetime.now()

        if assinatura not in vistos:
            vistos[assinatura] = data_atual
            resultado.append(promo)
            continue

        if abs(vistos[assinatura] - data_atual) > janela:
            vistos[assinatura] = data_atual
            resultado.append(promo)

    return resultado
