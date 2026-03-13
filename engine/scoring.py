from utils.texto import normalizar_texto


def calcular_score(item):
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

    elif tipo == "milheiro_barato":
        preco = float(item.get("preco", 999))

        if preco <= 14:
            score = 9.5
        elif preco <= 15:
            score = 8.5
        elif preco <= 16:
            score = 8.0
        elif preco <= 18:
            score = 7.5

    elif tipo == "passagem_barata":
        milhas = int(item.get("milhas", 999999))

        if milhas <= 3000:
            score = 9.0
        elif milhas <= 4000:
            score = 8.5
        elif milhas <= 5000:
            score = 7.5

    # fonte oficial vale mais
    if origem in ("programa", "banco"):
        score += 0.5

    return min(round(score, 1), 10.0)


def classificar_score(score):
    if score >= 9:
        return "🔴 PROMOÇÃO IMPERDÍVEL"
    if score >= 7.5:
        return "🟡 PROMOÇÃO MUITO BOA"
    return "🟢 PROMOÇÃO BOA"


def ordenar_resultados(resultados):
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


def chave_confirmacao(item):
    titulo = normalizar_texto(item.get("titulo", ""))
    link = item.get("link", "")
    tipo = item.get("tipo", "")

    if tipo == "transferencia_bonificada":
        bonus = str(item.get("bonus", ""))
        return f"{tipo}|{bonus}|{titulo[:80]}|{link[:80]}"

    if tipo == "milheiro_barato":
        return f"{tipo}|{item.get('preco', '')}|{titulo[:80]}"

    if tipo == "passagem_barata":
        return f"{tipo}|{item.get('milhas', '')}|{titulo[:80]}"

    return f"{tipo}|{titulo[:80]}|{link[:80]}"
