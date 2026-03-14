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


def _normalizar_texto(texto):
    if not texto:
        return ""

    return " ".join(str(texto).lower().strip().split())


def _assinatura_promocao(promo):
    titulo = _normalizar_texto(promo.get("title", ""))
    link = _normalizar_texto(promo.get("link", ""))
    tipo = _normalizar_texto(promo.get("type", ""))
    programa = _normalizar_texto(promo.get("program", ""))

    return f"{tipo}|{programa}|{titulo}|{link}"


def deduplicar(promocoes):
    if not isinstance(promocoes, list):
        return []

    janela = timedelta(hours=JANELA_REPETICAO_HORAS)

    promocoes_ordenadas = sorted(
        promocoes,
        key=lambda p: _parse_data(p.get("created_at")) or datetime.min,
        reverse=True,
    )

    resultado = []
    vistos = {}

    for promo in promocoes_ordenadas:
        assinatura = _assinatura_promocao(promo)
        data_atual = _parse_data(promo.get("created_at")) or datetime.now()

        if assinatura not in vistos:
            vistos[assinatura] = data_atual
            resultado.append(promo)
            continue

        ultima_data = vistos[assinatura]

        if abs(ultima_data - data_atual) > janela:
            vistos[assinatura] = data_atual
            resultado.append(promo)

    return resultado
