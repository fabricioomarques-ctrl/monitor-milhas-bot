def classificar_score(score):
    if score >= 90:
        return "🔴 OPORTUNIDADE IMPERDÍVEL"
    if score >= 75:
        return "🟡 OPORTUNIDADE FORTE"
    if score >= 60:
        return "🟢 BOA OPORTUNIDADE"
    return "⚪ OPORTUNIDADE PADRÃO"


def prioridade_origem(origem):
    mapa = {
        "banco": 4,
        "programa": 3,
        "blog": 2,
    }
    return mapa.get(origem, 1)


def enriquecer_score(item):
    score = int(item.get("score_base", 0))
    origem = item.get("origem", "")

    score += prioridade_origem(origem) * 3

    item["score"] = score
    item["classificacao"] = classificar_score(score)
    return item


def ordenar_resultados(resultados):
    enriquecidos = [enriquecer_score(dict(r)) for r in resultados]

    return sorted(
        enriquecidos,
        key=lambda x: (
            x.get("score", 0),
            prioridade_origem(x.get("origem", "")),
            x.get("bonus", 0),
            -x.get("preco", 999),
        ),
        reverse=True
    )
