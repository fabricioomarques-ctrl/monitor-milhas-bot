import re
import hashlib

RUÍDO = [
    "guia",
    "dicas",
    "como",
    "review",
    "vale a pena",
    "análise"
]

PROGRAMAS = [
    "smiles",
    "latam",
    "latam pass",
    "tudoazul",
    "livelo",
    "esfera",
    "átomos",
    "pão de açúcar"
]

BANCOS = [
    "itau",
    "bradesco",
    "santander",
    "banco do brasil",
    "caixa",
    "c6",
    "inter",
    "xp",
    "btg",
    "neon",
    "nubank"
]


def limpar_texto(t):
    t = t.lower()
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def ruido(titulo):
    for r in RUÍDO:
        if r in titulo:
            return True
    return False


def detectar_categoria(texto):

    if "milhas" in texto and "partir de" in texto:
        return "passagens"

    if "bônus" in texto or "transfer" in texto:
        return "transferencias"

    if "milheiro" in texto or "r$" in texto and "milhas" in texto:
        return "milheiro"

    return None


def score_passagens(texto):

    numeros = re.findall(r"\d+", texto)

    if not numeros:
        return 7

    valor = int(numeros[0])

    if valor < 5000:
        return 9.5
    if valor < 10000:
        return 9
    if valor < 20000:
        return 8

    return 7


def score_transferencia(texto):

    bonus = re.findall(r"\d+%", texto)

    if not bonus:
        return 7

    valor = int(bonus[0].replace("%", ""))

    if valor >= 100:
        return 9.5
    if valor >= 80:
        return 9
    if valor >= 60:
        return 8

    return 7


def score_milheiro(texto):

    preco = re.findall(r"r\$\s*\d+[,.]?\d*", texto)

    if not preco:
        return 7

    valor = float(preco[0].replace("r$", "").replace(",", "."))

    if valor < 11:
        return 9.5
    if valor < 13:
        return 9
    if valor < 15:
        return 8

    return 7


def gerar_id(titulo, link):

    base = titulo + link
    return hashlib.md5(base.encode()).hexdigest()


def transformar_em_promocoes(itens):

    promocoes = []

    for item in itens:

        titulo = limpar_texto(item.get("title", ""))
        link = item.get("link", "")

        if ruido(titulo):
            continue

        categoria = detectar_categoria(titulo)

        if not categoria:
            continue

        if categoria == "passagens":
            score = score_passagens(titulo)

        elif categoria == "transferencias":
            score = score_transferencia(titulo)

        else:
            score = score_milheiro(titulo)

        promo = {
            "id": gerar_id(titulo, link),
            "title": titulo,
            "link": link,
            "type": categoria,
            "score": score,
            "program": detectar_programa(titulo)
        }

        promocoes.append(promo)

    return promocoes


def detectar_programa(texto):

    for p in PROGRAMAS:
        if p in texto:
            return p.title()

    return "Programa não identificado"


def format_promo_card(p):

    tipo = {
        "passagens": "✈️ PASSAGEM PROMOCIONAL",
        "transferencias": "💳 TRANSFERÊNCIA PROMOCIONAL",
        "milheiro": "💰 MILHEIRO BARATO"
    }

    return f"""
{tipo[p['type']]}

Programa: {p['program']}
Título: {p['title']}

Score: {p['score']}

Link:
{p['link']}
"""
