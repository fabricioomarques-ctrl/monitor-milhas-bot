import hashlib
import re
from datetime import datetime


PROGRAMAS = [
    "smiles",
    "latam pass",
    "latam",
    "azul fidelidade",
    "tudoazul",
    "livelo",
    "esfera",
    "all accor",
    "krisflyer",
]

BANCOS = [
    "itau",
    "itaú",
    "bradesco",
    "santander",
    "banco do brasil",
    "bb",
    "caixa",
    "c6",
    "inter",
    "xp",
    "btg",
    "neon",
    "nubank",
    "sicoob",
    "sicredi",
]

RUIDO = [
    "deixe um comentário",
    "deixe um comentario",
    "publicidade",
    "saiba mais",
    "10 horas atrás",
    "horas atrás",
    "vale a pena",
    "review",
    "guia",
    "dicas",
]


def _clean_spaces(texto: str) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def limpar_titulo(texto: str) -> str:
    t = str(texto or "").lower()

    t = re.sub(r"\b\d{1,2}\s+de\s+[a-zçãé]+\s+de\s+\d{4}\b", " ", t, flags=re.I)
    t = re.sub(r"\b\d+\s+horas?\s+atr[aá]s\b", " ", t, flags=re.I)
    t = re.sub(r"\bsaiba mais\b", " ", t, flags=re.I)
    t = re.sub(r"\bpublicidade\b", " ", t, flags=re.I)
    t = re.sub(r"\bdeixe um coment[aá]rio\b", " ", t, flags=re.I)
    t = re.sub(r"\bsegue valendo!?+\b", " ", t, flags=re.I)
    t = re.sub(r"\bprorrogou!?+\b", " ", t, flags=re.I)
    t = re.sub(r"[|]+", " ", t)
    t = _clean_spaces(t)

    return t


def _norm(texto: str) -> str:
    return limpar_titulo(texto).lower()


def _has_any(texto: str, palavras: list[str]) -> bool:
    texto = _norm(texto)
    return any(p in texto for p in palavras)


def _detect_program(texto: str) -> str:
    t = _norm(texto)

    if "smiles" in t:
        return "Smiles"
    if "latam pass" in t or re.search(r"\blatam\b", t):
        return "LATAM Pass"
    if "azul fidelidade" in t or "tudoazul" in t:
        return "TudoAzul"
    if "livelo" in t:
        return "Livelo"
    if "esfera" in t:
        return "Esfera"
    if "all accor" in t or re.search(r"\baccor\b", t):
        return "ALL Accor"
    if "krisflyer" in t:
        return "KrisFlyer"
    if "maxmilhas" in t or "milheiro" in t:
        return "Mercado de Milhas"

    return "Programa não identificado"


def _detect_type(texto: str) -> str | None:
    t = _norm(texto)

    if _has_any(t, RUIDO):
        return None

    if "milheiro" in t or "maxmilhas" in t:
        return "milheiro"

    if (
        ("transfer" in t or "bônus" in t or "bonus" in t or "bonificada" in t)
        and (_has_any(t, BANCOS) or _has_any(t, PROGRAMAS))
    ):
        return "transferencias"

    if (
        ("milhas" in t or "pontos" in t)
        and (
            "passagens" in t
            or "passagem" in t
            or "trechos" in t
            or "voos" in t
            or "resgate" in t
            or "ida e volta" in t
            or "o trecho" in t
        )
        and _has_any(t, PROGRAMAS)
    ):
        return "passagens"

    return None


def _score_transferencias(texto: str) -> float:
    t = _norm(texto)
    match = re.search(r"(\d{2,3})\s*%", t)
    bonus = int(match.group(1)) if match else 0

    if bonus >= 100:
        return 9.5
    if bonus >= 90:
        return 9.0
    if bonus >= 80:
        return 8.5
    if bonus >= 70:
        return 8.0
    if bonus >= 60:
        return 7.5
    return 7.0


def _score_passagens(texto: str) -> float:
    t = _norm(texto)
    numeros = re.findall(r"(\d{3,6})", t)

    valores = []
    for n in numeros:
        try:
            valores.append(int(n))
        except Exception:
            continue

    pontos = min(valores) if valores else 0

    if pontos and pontos <= 5000:
        return 9.0
    if pontos and pontos <= 10000:
        return 8.5
    if pontos and pontos <= 25000:
        return 8.0
    return 7.5


def _score_milheiro(texto: str) -> float:
    t = _norm(texto)
    m = re.search(r"r\$\s*(\d+[,.]?\d*)", t)
    if not m:
        return 7.0

    try:
        valor = float(m.group(1).replace(",", "."))
    except Exception:
        valor = 99.0

    if valor <= 11:
        return 9.8
    if valor <= 13:
        return 9.0
    if valor <= 15:
        return 8.0
    return 7.0


def _classificacao(score: float) -> str:
    if score >= 9:
        return "🔴 PROMOÇÃO IMPERDÍVEL"
    if score >= 8:
        return "🟡 PROMOÇÃO MUITO BOA"
    return "🟢 PROMOÇÃO BOA"


def _build_id(titulo: str, link: str, tipo: str) -> str:
    base = f"{tipo}|{limpar_titulo(titulo)}|{str(link or '').strip()}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()


def transformar_em_promocoes(itens: list) -> list:
    promocoes = []

    for item in itens:
        titulo_bruto = item.get("title", "")
        link = item.get("link", "")

        titulo = limpar_titulo(titulo_bruto)
        tipo = _detect_type(titulo)

        if not tipo:
            continue

        program = _detect_program(titulo)

        if tipo == "passagens" and program == "Programa não identificado":
            continue

        if tipo == "transferencias":
            score = _score_transferencias(titulo)
        elif tipo == "milheiro":
            score = _score_milheiro(titulo)
        else:
            score = _score_passagens(titulo)

        promo = {
            "id": _build_id(titulo, link, tipo),
            "title": titulo,
            "link": link,
            "type": tipo,
            "program": program,
            "score": round(score, 1),
            "classification": _classificacao(score),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fontes_confirmadas": 1,
        }

        promocoes.append(promo)

    return promocoes
