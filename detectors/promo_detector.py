from utils.text_utils import (
    build_hash_id,
    detect_miles_amount,
    detect_percent,
    detect_price_brl,
    has_any,
    normalize_text,
    title_signature,
)

SOURCE_NAMES = [
    "pontos pra voar feed",
    "passageiro de primeira feed",
    "melhores destinos feed",
    "aeroin feed",
    "ppv latam pass",
    "ppv smiles",
    "ppv esfera",
    "ppv azul fidelidade",
    "ppv home",
    "latam pass oficial",
    "smiles oficial",
    "esfera oficial",
    "tudoazul oficial",
    "livelo oficial",
    "maxmilhas oficial",
]

HARD_BLOCK = [
    "shopee",
    "amazon",
    "mercado livre",
    "magalu",
    "assist card",
    "seguro",
    "lounge",
    "salas vip",
    "sunset mineiro",
    "hotel",
    "diárias",
    "cupom",
    "cashback",
    "varejo",
    "desconto em compras",
    "produto físico",
    "hero seguros",
    "guess",
    "seculus",
    "lojas parceiras",
    "pontos por real",
]

PROGRAMS = [
    "smiles",
    "latam pass",
    "latam",
    "azul fidelidade",
    "tudoazul",
    "livelo",
    "esfera",
    "connectmiles",
    "all accor",
    "accor",
    "krisflyer",
]

PASSAGENS_HINTS = [
    "alerta de passagens",
    "resgate",
    "trechos",
    "milhas",
    "pontos",
    "voos",
    "passagens",
    "ida e volta",
    "o trecho",
]

TRANSFER_HINTS = [
    "bônus na transferência",
    "bonus na transferencia",
    "transferência de pontos",
    "transferencia de pontos",
    "transferências bonificadas",
    "transferencias bonificadas",
    "transfira pontos",
    "transfira seus pontos",
    "converta pontos",
    "converta seus pontos",
    "receba até",
]

MILHEIRO_HINTS = [
    "milheiro",
    "maxmilhas",
    "compra de milhas",
    "mercado de milhas",
]

CLUBE_HINTS = [
    "clube smiles",
    "clube livelo",
    "clube esfera",
    "clube azul",
    "clube latam pass",
]

PASSAGENS_NEGATIVE = [
    "cadastre-se",
    "ganhe 2.500 pontos",
    "converta pontos",
    "bônus",
    "bonus",
    "assine",
    "clube",
]

TRANSFER_NEGATIVE = [
    "seguro",
    "assist card",
    "cupom",
    "hotel",
    "passagem cortesia",
]

def filtro_profissional(title: str, content: str) -> bool:
    combined = normalize_text(f"{title} {content}")

    if has_any(combined, HARD_BLOCK):
        return False

    if not (
        has_any(combined, PROGRAMS)
        or has_any(combined, PASSAGENS_HINTS)
        or has_any(combined, TRANSFER_HINTS)
        or has_any(combined, MILHEIRO_HINTS)
        or has_any(combined, CLUBE_HINTS)
    ):
        return False

    return True


def infer_program(source_name: str, title: str, content: str):
    combined = normalize_text(f"{title} {content}")
    source_norm = normalize_text(source_name)

    if "maxmilhas" in combined or "milheiro" in combined:
        return "Mercado de Milhas"
    if "smiles" in combined:
        return "Smiles"
    if "latam pass" in combined or "latam" in combined:
        return "LATAM Pass"
    if "azul fidelidade" in combined or "tudoazul" in combined or " pontos azul" in combined:
        return "TudoAzul"
    if "livelo" in combined:
        return "Livelo"
    if "esfera" in combined:
        return "Esfera"
    if "all accor" in combined or "accor" in combined:
        return "ALL Accor"
    if "krisflyer" in combined:
        return "KrisFlyer"

    # Nunca retornar nome de fonte como programa
    if source_norm in SOURCE_NAMES:
        return None

    return None


def classify_type(title: str, content: str) -> str:
    combined = normalize_text(f"{title} {content}")

    if has_any(combined, MILHEIRO_HINTS):
        return "milheiro"

    if (
        has_any(combined, TRANSFER_HINTS)
        and has_any(combined, PROGRAMS)
        and not has_any(combined, TRANSFER_NEGATIVE)
    ):
        return "transferencias"

    if (
        has_any(combined, PASSAGENS_HINTS)
        and ("milhas" in combined or "pontos" in combined or has_any(combined, PROGRAMS))
        and not has_any(combined, PASSAGENS_NEGATIVE)
    ):
        return "passagens"

    if (
        has_any(combined, CLUBE_HINTS)
        or ("bônus" in combined or "bonus" in combined)
        or ("assine" in combined and has_any(combined, PROGRAMS))
    ):
        return "promocoes"

    return "ignorar"


def classify_score(title: str, content: str, promo_type: str):
    combined = normalize_text(f"{title} {content}")
    price = detect_price_brl(combined)
    percent = detect_percent(combined)
    miles = detect_miles_amount(combined)

    if promo_type == "milheiro":
        if price is not None:
            if price <= 16:
                return 9.8, price
            if price <= 20:
                return 9.2, price
            if price <= 24:
                return 8.0, price
            return 7.0, price
        return 8.0, price

    if promo_type == "transferencias":
        if percent is not None:
            if percent >= 100:
                return 9.5, price
            if percent >= 90:
                return 9.0, price
            if percent >= 80:
                return 8.5, price
            if percent >= 70:
                return 8.0, price
            if percent >= 60:
                return 7.5, price
        return 7.2, price

    if promo_type == "passagens":
        if miles is not None and miles <= 6000:
            return 8.0, price
        if "a partir de" in combined or "resgate" in combined or "trechos" in combined:
            return 7.5, price
        return 7.2, price

    if promo_type == "promocoes":
        if "clube" in combined and ("milhas" in combined or "pontos" in combined):
            return 7.6, price
        return 7.0, price

    return 0.0, price


def classificar_promocao(score: float) -> str:
    if score >= 9:
        return "🔴 PROMOÇÃO IMPERDÍVEL"
    if score >= 8:
        return "🟡 PROMOÇÃO MUITO BOA"
    return "🟢 PROMOÇÃO BOA"


def classificador_ia_local(title: str, content: str, promo_type: str, score: float) -> dict:
    combined = normalize_text(f"{title} {content}")

    prioridade = "normal"
    if score >= 9:
        prioridade = "alta"
    elif score >= 8:
        prioridade = "média"

    antecipada = any(
        k in combined
        for k in [
            "campanha",
            "banner",
            "segue valendo",
            "acaba hoje",
            "último dia",
            "apenas hoje",
        ]
    )

    return {
        "tipo": promo_type,
        "prioridade": prioridade,
        "detecao_antecipada": antecipada,
        "confianca_local": round(min(10.0, score + 0.2), 1),
    }


def calcular_confirmacoes(candidates: list) -> dict:
    by_sig = {}
    for item in candidates:
        sig = title_signature(item["title"])
        by_sig.setdefault(sig, []).append(item)

    confirmations = {}
    for sig, grouped in by_sig.items():
        confirmations[sig] = len({g["source_name"] for g in grouped})
    return confirmations


def transformar_em_promocoes(raw_items: list) -> list:
    promotions = []
    confirmations = calcular_confirmacoes(raw_items)

    for item in raw_items:
        title = item["title"]
        content = item["content"]
        link = item["link"]

        if not filtro_profissional(title, content):
            continue

        promo_type = classify_type(title, content)
        if promo_type == "ignorar":
            continue

        program = infer_program(item["source_name"], title, content)
        if promo_type in ("passagens", "transferencias") and not program:
            continue

        score, price = classify_score(title, content, promo_type)
        if score < 7.0:
            continue

        sig = title_signature(title)
        fontes_confirmadas = confirmations.get(sig, 1)
        ai_data = classificador_ia_local(title, content, promo_type, score)

        promo_id = build_hash_id(item["source_name"], title, link)

        promotions.append(
            {
                "id": promo_id,
                "source_name": item["source_name"],
                "source_group": item["source_group"],
                "program": program or item["source_name"],
                "title": title.strip(),
                "content": content.strip(),
                "link": link.strip(),
                "type": promo_type,
                "score": round(score, 1),
                "classification": classificar_promocao(score),
                "price_brl": price,
                "fontes_confirmadas": fontes_confirmadas,
                "created_at": item.get("created_at"),
                "ai": ai_data,
            }
        )

    promotions.sort(key=lambda p: (p["score"], p["created_at"] or ""), reverse=True)
    return promotions


def format_promo_card(promo: dict) -> str:
    lines = [
        "━━━━━━━━━━━━━━",
        "💰 PROMOÇÃO CONFIRMADA",
        "",
        f"Programa: {promo['program']}",
        f"Título: {promo['title']}",
    ]

    if promo["type"] == "milheiro" and promo["price_brl"] is not None:
        valor = f"R$ {promo['price_brl']:.2f}".replace(".", ",")
        lines.append(f"Milheiro detectado: {valor}")

    lines.extend(
        [
            f"Fontes confirmadas: {promo['fontes_confirmadas']}",
            f"Score: {promo['score']}",
            promo["classification"],
            "",
            "Link:",
            promo["link"],
            "━━━━━━━━━━━━━━",
        ]
    )
    return "\n".join(lines)


def promo_resumo_ranking(promo: dict) -> str:
    score = promo["score"]

    if promo["type"] == "milheiro":
        if promo.get("price_brl") is not None:
            valor = f"R$ {promo['price_brl']:.2f}".replace(".", ",")
            return f"Milheiro barato {valor} | score {score}"
        return f"Milheiro barato | score {score}"

    return f"{promo['program']} | {promo['title']} | score {score}"


def dedupe_by_signature(promos: list[dict], limit=5) -> list[dict]:
    result = []
    seen = set()

    for promo in promos:
        sig = title_signature(f"{promo['type']} {promo['program']} {promo['title']}")
        if sig in seen:
            continue
        seen.add(sig)
        result.append(promo)
        if len(result) >= limit:
            break

    return result
