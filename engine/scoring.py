from utils.texto import slug_texto
from engine.ai_classifier import enriquecer_contexto


def calcular_score(item: dict) -> float:
    item = enriquecer_contexto(item)

    tipo = item.get("tipo", "")
    origem = item.get("origem", "")

    score = 5.0

    if tipo == "transferencia_bonificada":
        bonus = int(item.get("bonus", 0))

        if bonus >= 120:
            score = 10.0
        elif bonus >= 100:
            score = 9.0
        elif bonus >= 90:
            score = 8.5
        elif bonus >= 80:
            score = 7.5
        elif bonus >= 70:
            score = 7.3
        elif bonus >= 60:
            score = 7.0
        elif bonus >= 50:
            score = 6.5
        elif bonus >= 40:
            score = 6.0
        elif bonus >= 30:
            score = 5.5
        else:
            score = 5.0

    elif tipo == "milheiro_barato":
        preco = float(item.get("preco", 999))

        if preco <= 14:
            score = 9.8
        elif preco <= 15:
            score = 9.0
        elif preco <= 16:
            score = 8.0
        elif preco <= 17:
            score = 7.0
        elif preco <= 18:
            score = 6.0
        elif preco <= 20:
            score = 5.5
        else:
            score = 5.0

    elif tipo == "passagem_barata":
        milhas = int(item.get("milhas", 999999))

        if milhas <= 3500:
            score = 9.5
        elif milhas <= 5000:
            score = 9.0
        elif milhas <= 7000:
            score = 8.0
        elif milhas <= 9000:
            score = 7.0
        elif milhas <= 12000:
            score = 6.0
        else:
            score = 5.0

    if origem in ("programa", "banco"):
        score += 0.5

    if item.get("ai_urgencia"):
        score += 0.3

    if item.get("ai_oficial"):
        score += 0.2

    return min(round(score, 1), 10.0)


def classificar_score(score: float) -> str:
    if score >= 9.0:
        return "🔴 PROMOÇÃO IMPERDÍVEL"
    if score >= 7.5:
        return "🟡 PROMOÇÃO MUITO BOA"
    return "🟢 PROMOÇÃO BOA"


def ordenar_resultados(resultados: list[dict]) -> list[dict]:
    enriquecidos = []

    for item in resultados:
        novo = dict(item)
        novo["score"] = calcular_score(novo)
        novo["classificacao"] = classificar_score(novo["score"])
        enriquecidos.append(novo)

    return sorted(
        enriquecidos,
        key=lambda x: (
            x.get("score", 0),
            x.get("bonus", 0),
            -x.get("preco", 999),
            -x.get("milhas", 999999),
        ),
        reverse=True
    )


def chave_confirmacao(item: dict) -> str:
    tipo = item.get("tipo", "")
    titulo = slug_texto(item.get("titulo", ""))

    if tipo == "transferencia_bonificada":
        return f"{tipo}|{item.get('bonus', '')}|{titulo}"

    if tipo == "milheiro_barato":
        return f"{tipo}|{float(item.get('preco', 0)):.2f}|{titulo}"

    if tipo == "passagem_barata":
        return f"{tipo}|{item.get('milhas', '')}|{titulo}"

    return f"{tipo}|{titulo}"


def chave_duplicacao(item: dict) -> str:
    tipo = item.get("tipo", "")
    titulo = slug_texto(item.get("titulo", ""))

    if tipo == "transferencia_bonificada":
        return f"{tipo}|{item.get('bonus', '')}|{titulo}"

    if tipo == "milheiro_barato":
        return f"{tipo}|{float(item.get('preco', 0)):.2f}|{titulo}"

    if tipo == "passagem_barata":
        return f"{tipo}|{item.get('milhas', '')}|{titulo}"

    return f"{tipo}|{titulo}"
