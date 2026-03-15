import os
import re
import json
import html
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse, unquote
from xml.etree import ElementTree as ET

import feedparser
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# =========================================================
# CONFIG
# =========================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
CANAL_ID = os.getenv("CANAL_ID", "").strip()

_admin_raw = os.getenv("ADMIN_IDS", os.getenv("CHAT_ID", "")).strip()
ADMIN_IDS = [int(x.strip()) for x in _admin_raw.split(",") if x.strip().isdigit()]

RADAR_INTERVAL_SECONDS = int(os.getenv("RADAR_INTERVAL_SECONDS", "3600"))
JANELA_REPETICAO_HORAS = int(os.getenv("JANELA_REPETICAO_HORAS", "24"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
MAX_RANKING = int(os.getenv("MAX_RANKING", "10"))

PROMOCOES_FILE = "promocoes_enviadas.json"
METRICS_FILE = "dashboard_metrics.json"

if not TELEGRAM_TOKEN:
    raise RuntimeError("VariÃ¡vel TELEGRAM_TOKEN nÃ£o configurada.")
if not CANAL_ID:
    raise RuntimeError("VariÃ¡vel CANAL_ID nÃ£o configurada.")

# =========================================================
# FONTES
# =========================================================

FONTES_RSS = [
    "https://passageirodeprimeira.com/feed",
    "https://pontospravoar.com/feed",
    "https://www.melhoresdestinos.com.br/feed",
    "https://aeroin.net/feed",
    "https://www.melhorescartoes.com.br/feed",
    "https://onemileatatime.com/feed/",
    "https://viewfromthewing.com/feed/",
    "https://frequentmiler.com/feed/",
    "https://loyaltylobby.com/feed/",
    "https://upgradedpoints.com/feed/",
    "https://thepointsguy.com/feed/",
    "https://awardwallet.com/blog/feed/",
    "https://godsavethepoints.com/feed/",
    "https://thriftytraveler.com/feed/",
    "https://www.secretflying.com/feed/",
    "https://www.fly4free.com/feed/",
]

FONTES_OFICIAIS = [
    {"program": "Smiles", "type_hint": "transferencias", "url": "https://www.smiles.com.br/promocoes"},
    {"program": "Smiles", "type_hint": "milheiro", "url": "https://www.smiles.com.br/clube-smiles"},
    {"program": "Smiles", "type_hint": "milheiro", "url": "https://www.smiles.com.br/home"},
    {"program": "LATAM Pass", "type_hint": "passagens", "url": "https://latampass.latam.com"},
    {"program": "TudoAzul", "type_hint": "passagens", "url": "https://www.voeazul.com.br"},
    {"program": "Livelo", "type_hint": "transferencias", "url": "https://www.livelo.com.br"},
    {"program": "Livelo", "type_hint": "milheiro", "url": "https://www.livelo.com.br/clube"},
    {"program": "Esfera", "type_hint": "transferencias", "url": "https://www.esfera.com.vc"},
    {"program": "Esfera", "type_hint": "milheiro", "url": "https://www.esfera.com.vc/clube"},
    {"program": "ALL Accor", "type_hint": "transferencias", "url": "https://all.accor.com"},
]

SITEMAP_SOURCES = [
    {"program": "Smiles", "url": "https://www.smiles.com.br/sitemap.xml"},
    {"program": "Livelo", "url": "https://www.livelo.com.br/sitemap.xml"},
    {"program": "Esfera", "url": "https://www.esfera.com.vc/sitemap.xml"},
]

PUBLIC_MILEAGE_SOURCES = [
    {"program": "Mercado de Milhas", "url": "https://www.maxmilhas.com.br"},
    {"program": "Mercado de Milhas", "url": "https://123milhas.com/"},
    {"program": "Smiles", "url": "https://www.smiles.com.br/clube-smiles"},
    {"program": "Livelo", "url": "https://www.livelo.com.br/compra-de-pontos/produto/LIVCompraDePontos"},
    {"program": "Esfera", "url": "https://www.esfera.com.vc/clube"},
]

PROMO_PAGES = [
    {"program": "Smiles", "type_hint": "transferencias", "url": "https://www.smiles.com.br/promocoes"},
    {"program": "TudoAzul", "type_hint": "passagens", "url": "https://www.voeazul.com.br"},
    {"program": "Esfera", "type_hint": "transferencias", "url": "https://www.esfera.com.vc"},
    {"program": "Livelo", "type_hint": "transferencias", "url": "https://www.livelo.com.br"},
]

EARLY_DETECT_URLS = [
    {"program": "Smiles", "type_hint": None, "url": "https://www.smiles.com.br/promocoes"},
    {"program": "Smiles", "type_hint": "milheiro", "url": "https://www.smiles.com.br/clube-smiles"},
    {"program": "Smiles", "type_hint": None, "url": "https://www.smiles.com.br/home"},
    {"program": "LATAM Pass", "type_hint": None, "url": "https://latampass.latam.com"},
    {"program": "TudoAzul", "type_hint": None, "url": "https://www.voeazul.com.br"},
    {"program": "Livelo", "type_hint": None, "url": "https://www.livelo.com.br"},
    {"program": "Livelo", "type_hint": "milheiro", "url": "https://www.livelo.com.br/clube"},
    {"program": "Esfera", "type_hint": None, "url": "https://www.esfera.com.vc"},
    {"program": "Esfera", "type_hint": "milheiro", "url": "https://www.esfera.com.vc/clube"},
    {"program": "ALL Accor", "type_hint": None, "url": "https://all.accor.com"},
]

# =========================================================
# LIMPEZA / FILTROS
# =========================================================

NOISE_FRAGMENTS = [
    "radar ppv!",
    "radar ppv",
    "alerta de passagens ppv!",
    "alerta de passagens ppv",
    "seja bem-vindo a mais uma ediÃ§Ã£o do radar ppv",
    "a Ãºltima ediÃ§Ã£o do radar ppv da semana chegou",
    "a Ãºltima ediÃ§Ã£o do radar ppv",
    "resumo das promoÃ§Ãµes",
    "resumo promoÃ§Ãµes",
    "a promoÃ§Ã£o do",
    "a smiles estÃ¡ oferecendo",
    "o smiles voltou a oferecer",
    "nesta oferta, Ã© possÃ­vel",
    "confira os detalhes para participar e aproveitar a oferta",
    "atenÃ§Ã£o: a busca dessas emissÃµes foi realizada no momento da produÃ§Ã£o",
    "estÃ¡ planejando aquela viagem dos sonhos",
    "entÃ£o estÃ¡ no lugar certo",
    "no artigo de hoje, separamos",
    "o post",
]

GENERIC_TRANSFER_TERMS = [
    "radar ppv",
    "resumo das promoÃ§Ãµes",
    "resumo promoÃ§Ãµes",
    "seja bem-vindo a mais uma ediÃ§Ã£o",
    "a Ãºltima ediÃ§Ã£o",
    "ediÃ§Ã£o do radar",
]

TRANSFER_ACCEPT_TERMS = [
    "transferÃªncia bonificada",
    "transferencia bonificada",
    "acÃºmulo com parceiro",
    "acumulo com parceiro",
    "campanhas hÃ­bridas",
    "campanhas hibridas",
    "campanha hÃ­brida",
    "campanha hibrida",
    "transferÃªncia",
    "transferencia",
    "bÃ´nus",
    "bonus",
    "bonificada",
    "envie pontos",
    "converta pontos",
    "converta seus pontos",
    "transfira pontos",
    "transferir pontos",
]

TRANSFER_REJECT_TERMS = [
    "pontos por real gasto",
    "por real gasto",
    "varejo",
    "parceiros varejistas",
    "parceiro varejista",
    "campanha de acÃºmulo",
    "campanha de acumulo",
    "acÃºmulo comum",
    "acumulo comum",
    "credit card",
    "card",
    "welcome offer",
    "sign up",
    "signup",
    "apply now",
    "marriott card",
    "bonvoy card",
    "brilliant card",
    "amex card",
    "cartÃ£o",
    "cartao",
    "tier point",
    "tier points",
    "status bonus",
    "elite bonus",
    "american airlines flights",
    "mileage earnings",
    "tier bonuses",
]

TRANSFER_EXTRA_REJECT_TERMS = [
    "assine",
    "assinatura",
    "signature",
    "clube assinatura",
    "criar conta",
    "fazer login",
    "login",
    "boas vindas",
    "boas-vindas",
    "reativacao",
    "reativaÃ§Ã£o",
    "compre pontos",
    "compra de pontos",
    "comprar pontos",
    "comprar milhas",
    "hotÃ©is",
    "hoteis",
    "hotel",
    "desconto",
    "euros",
    "gaste em hotÃ©is",
    "gaste em hoteis",
    "all signature",
    "acelere seus benefÃ­cios",
    "acelere seus beneficios",
]

ANTI_SPAM_TERMS = [
    "radar ppv",
    "resumo da semana",
    "resumo do dia",
    "resumo das promoÃ§Ãµes",
    "promocoes que terminam hoje",
    "promoÃ§Ãµes que terminam hoje",
    "Ãºltima chamada",
    "ultima chamada",
    "Ãºltima ediÃ§Ã£o",
    "ultima ediÃ§Ã£o",
    "review",
    "guia",
    "dicas",
    "vale a pena",
    "como funciona",
    "melhores cartÃµes",
    "melhores cartoes",
]

RANKING_REJECT_TERMS = [
    "alerta ppv",
    "radar ppv",
    "no alerta ppv de hoje",
    "no alerta de hoje",
    "resumo das promoÃ§Ãµes",
    "resumo promocoes",
    "resumo da semana",
    "Ãºltima chamada",
    "ultima chamada",
    "ediÃ§Ã£o do radar",
    "edicao do radar",
    "seja bem-vindo",
    "seja bem vindo",
    "compre pontos",
    "compra de pontos",
    "comprar pontos",
    "criar conta",
    "fazer login",
    "boas vindas",
    "boas-vindas",
    "acelere seus benefÃ­cios",
    "acelere seus beneficios",
    "reativacao",
    "reativaÃ§Ã£o",
    "signature",
    "assine",
    "assinatura",
    "card",
    "credit card",
    "welcome offer",
    "signup",
    "sign up",
    "benefÃ­cios exclusivos",
    "beneficios exclusivos",
    "tudo isso e outros benefÃ­cios",
    "tudo isso e outros beneficios",
    "clube livelo",
    "benefÃ­cios do clube",
    "beneficios do clube",
]

EDITORIAL_GENERIC_TERMS = [
    "confira trechos",
    "no artigo de hoje",
    "separamos",
    "encontramos oportunidades",
    "estÃ¡ no lugar certo",
    "planejando aquela viagem",
    "resumo da semana",
    "resumo do dia",
    "ediÃ§Ã£o do radar",
    "Ãºltima chamada",
    "ultima chamada",
    "sugestÃµes de voos",
    "sugestoes de voos",
    "confira",
    "veja trechos",
    "alerta ppv",
]

PROGRAMAS = [
    "smiles",
    "clube smiles",
    "latam",
    "latam pass",
    "azul fidelidade",
    "tudoazul",
    "clube azul",
    "livelo",
    "esfera",
    "all accor",
    "accor",
    "krisflyer",
    "singapore",
    "iberia",
    "avios",
    "flying blue",
    "british airways",
    "tap",
    "amex",
    "american express",
]

BANCOS = [
    "itau",
    "itaÃº",
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
    "amex",
    "american express",
]

RUIDO = [
    "deixe um comentÃ¡rio",
    "deixe um comentario",
    "publicidade",
    "saiba mais",
    "10 horas atrÃ¡s",
    "horas atrÃ¡s",
    "vale a pena",
    "review",
    "guia",
    "dicas",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    )
}


def clean_text(texto: str) -> str:
    if not texto:
        return ""

    texto = str(texto)

    try:
        texto = texto.encode("latin1").decode("utf-8")
    except Exception:
        pass

    texto = html.unescape(texto)
    texto = texto.replace("&#8230;", ".")
    texto = texto.replace("\u2026", ".")
    texto = BeautifulSoup(texto, "html.parser").get_text(" ", strip=True)
    texto = re.sub(r"\s+", " ", texto).strip()

    lixo = ["Ã¢â¬Â¢", "Ã¢â¬", "Ã¢â¬â¢", "Ã¢â¬Å", "Ã", "Ã°", "Ã", "Ã¢", "Â¤", "ï¿½"]
    for item in lixo:
        texto = texto.replace(item, " ")

    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def normalize_spaces(texto: str) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def strip_noise_phrases(texto: str) -> str:
    t = texto
    low = t.lower()
    for frag in NOISE_FRAGMENTS:
        idx = low.find(frag)
        if idx != -1:
            t = t[:idx].strip()
            low = t.lower()
    return normalize_spaces(t)


def sentence_crop(texto: str, max_len: int = 170) -> str:
    texto = normalize_spaces(texto)
    if len(texto) <= max_len:
        return texto
    candidates = [". ", "! ", "? ", " - ", " â ", ": "]
    cut = -1
    for sep in candidates:
        pos = texto.rfind(sep, 0, max_len)
        cut = max(cut, pos)
    if cut > 40:
        return texto[:cut + 1].strip()
    cut = texto[:max_len].rsplit(" ", 1)[0].strip()
    return cut + "..."


def titulo_normalizado(titulo: str) -> str:
    t = clean_text(titulo).lower()
    t = re.sub(r"[^a-z0-9 ]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def canonicalize_brand_names(texto: str) -> str:
    if not texto:
        return ""

    subs = [
        (r"\blatam pass\b", "LATAM Pass"),
        (r"\blatam\b", "LATAM"),
        (r"\btudoazul\b", "TudoAzul"),
        (r"\bazul fidelidade\b", "Azul Fidelidade"),
        (r"\bsmiles\b", "Smiles"),
        (r"\blivelo\b", "Livelo"),
        (r"\besfera\b", "Esfera"),
        (r"\ball accor\b", "ALL Accor"),
        (r"\baccor\b", "Accor"),
        (r"\bkrisflyer\b", "KrisFlyer"),
        (r"\bbritish airways\b", "British Airways"),
        (r"\bflying blue\b", "Flying Blue"),
        (r"\biberia\b", "Iberia"),
        (r"\btap\b", "TAP"),
        (r"\bamex\b", "Amex"),
    ]

    out = texto
    for pat, repl in subs:
        out = re.sub(pat, repl, out, flags=re.I)

    out = re.sub(r"\s+", " ", out).strip()
    return out


def is_generic_transfer_post(texto: str) -> bool:
    t = clean_text(texto).lower()
    return any(term in t for term in GENERIC_TRANSFER_TERMS)


def is_strict_transfer_post(texto: str) -> bool:
    t = clean_text(texto).lower()
    has_accept = any(term in t for term in TRANSFER_ACCEPT_TERMS)
    has_reject = any(term in t for term in TRANSFER_REJECT_TERMS)
    has_extra_reject = any(term in t for term in TRANSFER_EXTRA_REJECT_TERMS)
    return has_accept and not has_reject and not has_extra_reject


def is_spammy_generic_post(title: str, summary: str) -> bool:
    texto = clean_text(f"{title} {summary}").lower()
    if any(term in texto for term in ANTI_SPAM_TERMS):
        if not re.search(r"(\d{2,3})\s*%|r\$\s*\d+[,.]?\d*|\b\d{3,6}\b", texto):
            return True
    return False


def title_from_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        slug = parsed.path.strip("/").split("/")[-1]
        slug = unquote(slug)
        slug = slug.replace("-", " ").replace("_", " ")
        slug = re.sub(r"\s+", " ", slug).strip()
        if not slug:
            return ""
        return slug[:140]
    except Exception:
        return ""


def cleanup_title_for_output(texto: str) -> str:
    texto = clean_text(texto)
    texto = strip_noise_phrases(texto)

    padroes = [
        r"^alerta de passagens ppv[!:\-\s]*",
        r"^alerta passagens ppv[!:\-\s]*",
        r"^radar ppv[!:\-\s]*",
        r"^no alerta ppv de hoje[,:\-\s]*",
        r"^no alerta de hoje[,:\-\s]*",
        r"^resumo das promoÃ§Ãµes[,:\-\s]*",
        r"^resumo promocoes[,:\-\s]*",
        r"^Ãºltima chamada[!:\-\s]*",
        r"^ultima chamada[!:\-\s]*",
        r"^seja bem[- ]vindo[a]?\s+a\s+mais\s+uma\s+ediÃ§Ã£o\s+do\s+.*",
        r"^seja bem[- ]vindo[a]?\s+a\s+mais\s+uma\s+edicao\s+do\s+.*",
    ]
    for padrao in padroes:
        texto = re.sub(padrao, "", texto, flags=re.I).strip()

    texto = re.sub(r"\s+", " ", texto).strip(" -:,.")
    texto = canonicalize_brand_names(texto)
    return texto


def build_short_title(title: str, summary: str = "", link: str = "", max_len: int = 140) -> str:
    title = clean_text(title)
    summary = clean_text(summary)

    if title.startswith("http://") or title.startswith("https://"):
        title = title_from_url(title)

    title = cleanup_title_for_output(title)
    summary = cleanup_title_for_output(summary)

    if summary.startswith("http://") or summary.startswith("https://"):
        summary = title_from_url(summary)

    base = title if title else summary
    if not base and link:
        base = title_from_url(link)

    for pat in [
        r"\bsaiba mais\b",
        r"\bpublicidade\b",
        r"\bdeixe um coment[aÃ¡]rio\b",
        r"\bsegue valendo!?+\b",
        r"\bprorrogou!?+\b",
        r"\b\d+\s+horas?\s+atr[aÃ¡]s\b",
        r"\b\d{1,2}\s+de\s+[a-zÃ§Ã£Ã©]+\s+de\s+\d{4}\b",
    ]:
        base = re.sub(pat, " ", base, flags=re.I)

    base = normalize_spaces(base)
    base = canonicalize_brand_names(base)
    return sentence_crop(base, max_len=max_len)


def is_editorial_generic(title: str, summary: str) -> bool:
    texto = clean_text(f"{title} {summary}").lower()
    return any(term in texto for term in EDITORIAL_GENERIC_TERMS)


def is_commercial_noise_for_ranking(title: str, summary: str, link: str) -> bool:
    texto = clean_text(f"{title} {summary}").lower()
    link_l = clean_text(link).lower()

    blocks = [
        "clube livelo",
        "ganhe pontos e aproveite benefÃ­cios",
        "ganhe pontos e aproveite beneficios",
        "benefÃ­cios exclusivos",
        "beneficios exclusivos",
        "tudo isso e outros benefÃ­cios",
        "tudo isso e outros beneficios",
        "criar conta",
        "fazer login",
        "login",
        "boas-vindas",
        "boas vindas",
        "acelere seus benefÃ­cios",
        "acelere seus beneficios",
        "compre pontos",
        "compra de pontos",
        "assine",
        "assinatura",
        "signature",
        "reativacao",
        "reativaÃ§Ã£o",
        "clube",
    ]

    if any(b in texto for b in blocks):
        if not re.search(r"(\d{2,3})\s*%|milheiro|r\$\s*\d+[,.]?\d*|3\.?\d{3}|4\.?\d{3}|5\.?\d{3}", texto):
            return True

    if any(x in link_l for x in ["login", "reativacao", "signature", "bonus-200"]):
        return True

    return False

# =========================================================
# STORAGE
# =========================================================


def _ensure_json_file(path: str, default: Any) -> None:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)


def _load_json(path: str, default: Any) -> Any:
    _ensure_json_file(path, default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def carregar_promocoes() -> list:
    data = _load_json(PROMOCOES_FILE, [])
    return data if isinstance(data, list) else []


def salvar_promocoes(promocoes: list) -> None:
    if not isinstance(promocoes, list):
        promocoes = []
    _save_json(PROMOCOES_FILE, promocoes)


def carregar_metricas() -> dict:
    data = _load_json(
        METRICS_FILE,
        {
            "fontes_monitoradas": 0,
            "fontes_ativas": 0,
            "fontes_com_erro": 0,
            "ultimos_alertas_enviados": 0,
            "ultima_execucao": None,
            "ultimo_erro": "nenhum",
            "falhas_fontes": {},
            "alertas_criticos": 0,
            "varredura_em_andamento": False,
            "promocoes_detectadas_ultimo_ciclo": 0,
            "startup_scan_concluido": False,
        },
    )
    return data if isinstance(data, dict) else {}


def salvar_metricas(metricas: dict) -> None:
    if not isinstance(metricas, dict):
        metricas = {}
    _save_json(METRICS_FILE, metricas)

# =========================================================
# DEDUP
# =========================================================


def _parse_data(valor):
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor
    formatos = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]
    for fmt in formatos:
        try:
            return datetime.strptime(str(valor), fmt)
        except Exception:
            continue
    return None


def _norm_assinatura(texto):
    return " ".join(str(texto or "").lower().strip().split())


def _semantic_transfer_key(title: str, program: str, bonus: int) -> str:
    t = clean_text(title).lower()
    parceiros = [
        ("krisflyer", "krisflyer"),
        ("smiles", "smiles"),
        ("latam pass", "latampass"),
        ("latam", "latampass"),
        ("tudoazul", "tudoazul"),
        ("azul", "tudoazul"),
        ("livelo", "livelo"),
        ("esfera", "esfera"),
        ("all accor", "allaccor"),
        ("accor", "allaccor"),
        ("iberia", "iberia"),
        ("avios", "iberia"),
        ("tap", "tap"),
        ("flying blue", "flyingblue"),
    ]
    parceiro = "geral"
    for raw, norm in parceiros:
        if raw in t and raw.lower() not in str(program).lower():
            parceiro = norm
            break
    return f"{str(program).lower()}|{parceiro}|{bonus}"


def _semantic_milheiro_key(title: str, program: str, milheiro: float | None) -> str:
    t = clean_text(title).lower()

    if "plano 1000" in t or "1.000" in t or "1000" in t:
        base = "clube-1000"
    elif "clube" in t:
        base = "clube"
    else:
        base = titulo_normalizado(t)[:60]

    faixa = ""
    if milheiro is not None:
        try:
            faixa = str(int(round(float(milheiro))))
        except Exception:
            faixa = ""

    return f"{str(program).lower()}|{base}|{faixa}"


def _assinatura(promo: dict) -> str:
    tipo = _norm_assinatura(promo.get("type"))
    program = _norm_assinatura(promo.get("program"))
    title = titulo_normalizado(promo.get("title"))
    bonus = int(promo.get("bonus_detectado") or 0)

    if tipo == "transferencias" and program and bonus:
        return f"{tipo}|{_semantic_transfer_key(title, program, bonus)}"

    if tipo == "milheiro":
        return f"{tipo}|{_semantic_milheiro_key(title, program, promo.get('milheiro_detectado'))}"

    if tipo == "passagens":
        sweet = "sweet" if promo.get("sweet_spot") else "normal"
        return f"{tipo}|{program}|{sweet}|{title[:100]}"

    return f"{tipo}|{program}|{title}"


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

# =========================================================
# HTTP / COLETA
# =========================================================


def safe_get(url: str) -> requests.Response:
    return requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)


def parse_html_text(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    parts = []

    if soup.title and soup.title.get_text(strip=True):
        parts.append(soup.title.get_text(" ", strip=True))

    for tag in soup.find_all(["h1", "h2", "h3"]):
        txt = tag.get_text(" ", strip=True)
        if txt:
            parts.append(txt)

    for tag in soup.find_all(["p", "span", "div", "li", "a"]):
        txt = tag.get_text(" ", strip=True)
        if txt and len(txt) > 20:
            parts.append(txt)
        if len(" ".join(parts)) > 5000:
            break

    return clean_text(" ".join(parts))[:5000]


def coletar_rss():
    itens = []
    falhas = {}

    for url in FONTES_RSS:
        try:
            feed = feedparser.parse(url)
            entries = getattr(feed, "entries", [])
            for entry in entries[:25]:
                title = clean_text(entry.get("title", "") or "")
                summary = clean_text(entry.get("summary", "") or "")
                link = entry.get("link", "") or ""

                if is_spammy_generic_post(title, summary):
                    continue

                itens.append(
                    {
                        "title": title,
                        "link": link,
                        "summary": summary,
                        "source_url": url,
                        "source_kind": "rss",
                        "type_hint": None,
                        "program_hint": None,
                    }
                )
        except Exception as e:
            falhas[url] = str(e)

    return itens, falhas


def coletar_paginas_oficiais():
    itens = []
    falhas = {}

    for fonte in FONTES_OFICIAIS:
        url = fonte["url"]
        try:
            resp = safe_get(url)
            resp.raise_for_status()
            texto = parse_html_text(resp.text)
            itens.append(
                {
                    "title": texto[:220],
                    "link": str(resp.url),
                    "summary": texto,
                    "source_url": url,
                    "source_kind": "official",
                    "type_hint": fonte.get("type_hint"),
                    "program_hint": fonte.get("program"),
                }
            )
        except Exception as e:
            falhas[url] = str(e)

    return itens, falhas


def _parse_sitemap_xml(xml_text: str) -> list:
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return []

    ns = {}
    if root.tag.startswith("{"):
        ns_uri = root.tag.split("}")[0].strip("{")
        ns = {"sm": ns_uri}

    urls = []

    if root.tag.endswith("sitemapindex"):
        path = ".//sm:loc" if ns else ".//loc"
        for loc in root.findall(path, ns):
            if loc.text:
                urls.append(loc.text.strip())
        return urls

    path = ".//sm:url/sm:loc" if ns else ".//url/loc"
    for loc in root.findall(path, ns):
        if loc.text:
            urls.append(loc.text.strip())

    return urls


def _interesting_url(url: str) -> bool:
    u = url.lower()
    keywords = [
        "promo", "promoco", "oferta", "offer", "bonus", "bÃ´nus",
        "clube", "milha", "mile", "points", "pontos", "passagem",
        "flight", "travel", "shopping", "turbo", "buy-points",
        "comprar", "compra", "resgate", "reativacao",
    ]
    return any(k in u for k in keywords)


def coletar_sitemaps():
    itens = []
    falhas = {}

    for fonte in SITEMAP_SOURCES:
        try:
            resp = safe_get(fonte["url"])
            resp.raise_for_status()
            first_level = _parse_sitemap_xml(resp.text)
            collected = []

            if any(u.endswith(".xml") for u in first_level):
                for sitemap_url in first_level[:8]:
                    try:
                        s_resp = safe_get(sitemap_url)
                        s_resp.raise_for_status()
                        collected.extend(_parse_sitemap_xml(s_resp.text)[:40])
                    except Exception:
                        continue
            else:
                collected = first_level[:50]

            filtered = []
            seen = set()
            for url in collected:
                if _interesting_url(url) and url not in seen:
                    seen.add(url)
                    filtered.append(url)

            for url in filtered[:25]:
                slug_title = title_from_url(url)
                itens.append(
                    {
                        "title": slug_title if slug_title else url,
                        "link": url,
                        "summary": slug_title if slug_title else url,
                        "source_url": fonte["url"],
                        "source_kind": "sitemap",
                        "type_hint": None,
                        "program_hint": fonte["program"],
                    }
                )
        except Exception as e:
            falhas[fonte["url"]] = str(e)

    return itens, falhas


def coletar_milheiro_publico():
    itens = []
    falhas = {}

    for fonte in PUBLIC_MILEAGE_SOURCES:
        try:
            resp = safe_get(fonte["url"])
            resp.raise_for_status()
            texto = parse_html_text(resp.text)
            itens.append(
                {
                    "title": texto[:220],
                    "link": str(resp.url),
                    "summary": texto,
                    "source_url": fonte["url"],
                    "source_kind": "marketplace",
                    "type_hint": "milheiro",
                    "program_hint": fonte["program"],
                }
            )
        except Exception as e:
            falhas[fonte["url"]] = str(e)

    return itens, falhas


def coletar_paginas_promocionais():
    itens = []
    falhas = {}

    for fonte in PROMO_PAGES:
        try:
            resp = safe_get(fonte["url"])
            resp.raise_for_status()
            texto = parse_html_text(resp.text)
            itens.append(
                {
                    "title": texto[:220],
                    "link": str(resp.url),
                    "summary": texto,
                    "source_url": fonte["url"],
                    "source_kind": "promo_page",
                    "type_hint": fonte.get("type_hint"),
                    "program_hint": fonte.get("program"),
                }
            )
        except Exception as e:
            falhas[fonte["url"]] = str(e)

    return itens, falhas


def coletar_detector_antecipado():
    itens = []
    falhas = {}

    for fonte in EARLY_DETECT_URLS:
        url = fonte["url"]
        try:
            resp = safe_get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            candidates = []

            if soup.title and soup.title.get_text(strip=True):
                candidates.append(soup.title.get_text(" ", strip=True))

            for tag in soup.find_all(["a", "h1", "h2", "h3", "span", "div", "li"]):
                txt = tag.get_text(" ", strip=True)
                href = ""
                if tag.name == "a":
                    href = tag.get("href", "") or ""

                if txt and len(txt) > 12:
                    candidates.append(txt)

                if href and _interesting_url(href):
                    candidates.append(title_from_url(href))

                if len(candidates) > 120:
                    break

            merged = " ".join([c for c in candidates if c]).strip()
            merged = clean_text(merged)[:5000]

            itens.append(
                {
                    "title": merged[:220],
                    "link": str(resp.url),
                    "summary": merged,
                    "source_url": url,
                    "source_kind": "early_detect",
                    "type_hint": fonte.get("type_hint"),
                    "program_hint": fonte.get("program"),
                }
            )
        except Exception as e:
            falhas[url] = str(e)

    return itens, falhas


def coletar_todas_fontes():
    itens = []
    falhas = {}

    for collector in [
        coletar_rss,
        coletar_paginas_oficiais,
        coletar_sitemaps,
        coletar_milheiro_publico,
        coletar_paginas_promocionais,
        coletar_detector_antecipado,
    ]:
        c_itens, c_falhas = collector()
        itens.extend(c_itens)
        falhas.update(c_falhas)

    return itens, falhas

# =========================================================
# DETECÃÃO
# =========================================================


def _detect_program(texto: str, program_hint=None):
    if program_hint:
        return program_hint

    t = clean_text(texto).lower()

    mapping = {
        "smiles": "Smiles",
        "clube smiles": "Smiles",
        "latam pass": "LATAM Pass",
        "latam": "LATAM Pass",
        "azul fidelidade": "TudoAzul",
        "tudoazul": "TudoAzul",
        "clube azul": "TudoAzul",
        "azul": "TudoAzul",
        "livelo": "Livelo",
        "esfera": "Esfera",
        "all accor": "ALL Accor",
        "accor": "ALL Accor",
        "krisflyer": "KrisFlyer",
        "amex": "Amex",
        "american express": "Amex",
        "british airways": "British Airways",
        "avios": "Iberia",
        "iberia": "Iberia",
        "tap": "TAP",
    }

    for k, v in mapping.items():
        if k in t:
            return v

    return None


def _detectar_bonus_alto(texto: str) -> int:
    t = clean_text(texto).lower()
    achados = re.findall(r"(\d{2,3})\s*%", t)
    bonus = [int(x) for x in achados if x.isdigit()]
    return max(bonus) if bonus else 0


def _detectar_milheiro(texto: str) -> float | None:
    t = clean_text(texto).lower()
    patterns = [
        r"milheiro[^0-9r\$]{0,20}r\$\s*(\d+[,.]?\d*)",
        r"r\$\s*(\d+[,.]?\d*)[^0-9]{0,20}milheiro",
        r"milhas[^0-9]{0,10}r\$\s*(\d+[,.]?\d*)",
    ]
    for pat in patterns:
        m = re.search(pat, t)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except Exception:
                pass

    m = re.search(r"r\$\s*(\d+[,.]?\d*)", t)
    if m and ("milheiro" in t or "clube" in t or "comprar milhas" in t or "compra de pontos" in t):
        try:
            return float(m.group(1).replace(",", "."))
        except Exception:
            return None

    return None


def _detectar_sweet_spot(texto: str) -> bool:
    t = clean_text(texto).lower()
    if any(k in t for k in ["executiva", "business", "primeira classe", "first class"]):
        if re.search(r"\b(3[0-9]|4[0-9]|5[0-9]|6[0-9]|7[0-9]|8[0-9])\.?\d{3}\b", t):
            return True
    if any(k in t for k in ["miami", "orlando", "europa", "madrid", "lisboa", "paris", "roma", "nova york", "new york", "rio de janeiro"]):
        if re.search(r"\b(3|4|5|6|7|8|9)\d{3,4}\b", t):
            return True
    if any(k in t for k in ["off no resgate", "desconto no resgate", "25% off", "30% off"]):
        return True
    return False


def _detect_type(texto: str, type_hint: str | None = None):
    t = clean_text(texto).lower()
    if any(r in t for r in RUIDO):
        return None

    hinted = type_hint if type_hint in {"milheiro", "transferencias", "passagens"} else None

    if "milheiro" in t or "maxmilhas" in t or "hotmilhas" in t:
        return "milheiro"

    if "compra de pontos" in t or "compra milhas" in t or "comprar milhas" in t:
        return "milheiro"

    if (
        ("transfer" in t or "bÃ´nus" in t or "bonus" in t or "bonificada" in t or "converta pontos" in t or "envie pontos" in t)
        and any(b in t for b in BANCOS + PROGRAMAS)
    ):
        return "transferencias"

    if (
        ("milhas" in t or "pontos" in t or "avios" in t)
        and (
            "passagens" in t or "passagem" in t or "trechos" in t or "voos" in t
            or "resgate" in t or "ida e volta" in t or "o trecho" in t
            or "voos baratos" in t or "ofertas" in t or "off no resgate" in t
        )
        and any(p in t for p in PROGRAMAS)
    ):
        return "passagens"

    return hinted


def _score_transferencias(texto: str) -> float:
    bonus = _detectar_bonus_alto(texto)
    if bonus >= 150:
        return 10.0
    if bonus >= 120:
        return 9.9
    if bonus >= 100:
        return 9.7
    if bonus >= 90:
        return 9.4
    if bonus >= 80:
        return 9.1
    if bonus >= 70:
        return 8.8
    if bonus >= 60:
        return 8.4
    if bonus >= 50:
        return 7.8
    if bonus >= 40:
        return 7.0
    if bonus >= 30:
        return 6.5
    return 6.0


def _score_passagens(texto: str) -> float:
    t = clean_text(texto).lower()
    if _detectar_sweet_spot(t):
        return 9.3
    if "25% off" in t or "off no resgate" in t or "desconto no resgate" in t:
        return 9.0

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
    valor = _detectar_milheiro(texto)
    if valor is None:
        return 7.0
    if valor <= 10:
        return 10.0
    if valor <= 11:
        return 9.8
    if valor <= 12:
        return 9.4
    if valor <= 13:
        return 9.0
    if valor <= 15:
        return 8.0
    return 7.0


def _classificacao(score: float) -> str:
    if score >= 9.0:
        return "ð´ PROMOÃÃO IMPERDÃVEL"
    if score >= 8.0:
        return "ð¡ PROMOÃÃO MUITO BOA"
    if score >= 7.0:
        return "ð¢ PROMOÃÃO BOA"
    return "âª PROMOÃÃO REGULAR"


def _alerta_prioridade(tipo: str, score: float, bonus: int, milheiro: float | None, sweet_spot: bool) -> str:
    if tipo == "transferencias" and bonus >= 100:
        return "ð¨ BÃNUS ALTO DETECTADO"
    if tipo == "transferencias" and bonus >= 80:
        return "ð¥ BÃNUS FORTE DETECTADO"
    if tipo == "milheiro" and milheiro is not None and milheiro <= 10:
        return "ð¨ MILHEIRO MUITO BARATO"
    if tipo == "milheiro" and milheiro is not None and milheiro <= 11:
        return "ð¥ MILHEIRO BARATO DETECTADO"
    if tipo == "passagens" and sweet_spot:
        return "ð¨ RESGATE BARATO DETECTADO"
    if score >= 9.0:
        return "ð¨ ALERTA CRÃTICO"
    if score >= 8.0:
        return "ð¥ ALERTA IMPORTANTE"
    if score >= 7.0:
        return "ð¢ PROMOÃÃO BOA"
    return "âª INFORMATIVO"


def _peso_categoria(tipo: str) -> float:
    if tipo == "milheiro":
        return 1.0
    if tipo == "transferencias":
        return 0.9
    if tipo == "passagens":
        return 0.8
    return 0.3


def _bonus_fonte(source_kind: str) -> float:
    if source_kind == "early_detect":
        return 0.55
    if source_kind == "official":
        return 0.40
    if source_kind == "promo_page":
        return 0.34
    if source_kind == "sitemap":
        return 0.24
    if source_kind == "marketplace":
        return 0.20
    return 0.0


def _penalidade_editorial(title: str, summary: str, source_kind: str) -> float:
    title_l = clean_text(title).lower()
    summary_l = clean_text(summary).lower()
    texto = f"{title_l} {summary_l}"

    penalty = 0.0
    if source_kind == "rss" and is_editorial_generic(title, summary):
        penalty += 0.60
    if any(term in texto for term in ["confira", "encontramos oportunidades", "sugestÃµes de voos", "sugestoes de voos"]):
        penalty += 0.35
    if any(term in texto for term in ["clube livelo", "benefÃ­cios exclusivos", "beneficios exclusivos"]):
        penalty += 0.80
    return penalty


def _build_id(titulo: str, link: str, tipo: str, program: str = "", bonus: int = 0) -> str:
    base_parts = [tipo, titulo_normalizado(titulo)]

    if tipo == "transferencias":
        base_parts.append(str(program or "").lower())
        if bonus:
            base_parts.append(str(bonus))

    if tipo == "milheiro":
        val = _detectar_milheiro(titulo)
        if val is not None:
            base_parts.append(str(int(round(val))))

    base = "|".join(base_parts)
    return hashlib.md5(base.encode("utf-8")).hexdigest()


def transformar_em_promocoes(itens: list) -> list:
    promocoes = []

    for item in itens:
        titulo_bruto = item.get("title", "")
        summary = item.get("summary", "")
        link = item.get("link", "")
        type_hint = item.get("type_hint")
        program_hint = item.get("program_hint")
        source_kind = item.get("source_kind", "rss")

        if is_spammy_generic_post(titulo_bruto, summary):
            continue

        texto_base = f"{titulo_bruto} {summary}".strip()
        tipo = _detect_type(texto_base, type_hint=type_hint)
        if not tipo:
            continue

        titulo_curto = build_short_title(titulo_bruto, summary, link=link, max_len=125)
        if not titulo_curto:
            continue

        if titulo_curto.startswith("http://") or titulo_curto.startswith("https://"):
            titulo_curto = title_from_url(titulo_curto)

        titulo_curto = cleanup_title_for_output(titulo_curto)
        if not titulo_curto:
            continue

        program = _detect_program(texto_base, program_hint=program_hint)

        if tipo == "passagens" and not program:
            continue

        if tipo == "transferencias":
            if not program:
                continue
            if is_generic_transfer_post(texto_base):
                continue
            if not is_strict_transfer_post(texto_base):
                continue

        if tipo == "transferencias":
            score = _score_transferencias(texto_base)
        elif tipo == "milheiro":
            score = _score_milheiro(texto_base)
        else:
            score = _score_passagens(texto_base)

        bonus = _detectar_bonus_alto(texto_base)
        milheiro = _detectar_milheiro(texto_base)
        sweet_spot = _detectar_sweet_spot(texto_base)
        prioridade = _alerta_prioridade(tipo, score, bonus, milheiro, sweet_spot)

        ranking_score = round(
            score * _peso_categoria(tipo)
            + _bonus_fonte(source_kind)
            - _penalidade_editorial(titulo_curto, summary, source_kind),
            2,
        )

        promo = {
            "id": _build_id(titulo_curto, link, tipo, program or "", bonus),
            "title": titulo_curto,
            "link": link,
            "type": tipo,
            "program": canonicalize_brand_names(program or "Programa nÃ£o identificado"),
            "score": round(score, 1),
            "classification": _classificacao(score),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fontes_confirmadas": 1,
            "bonus_detectado": bonus,
            "milheiro_detectado": milheiro,
            "sweet_spot": sweet_spot,
            "alert_priority": prioridade,
            "ranking_score": ranking_score,
            "source_kind": source_kind,
        }
        promocoes.append(promo)

    return promocoes

# =========================================================
# RADAR ENGINE
# =========================================================


class RadarState:
    def __init__(self):
        self.promocoes = carregar_promocoes()
        self.metricas = carregar_metricas()
        self.metricas.setdefault("fontes_monitoradas", 0)
        self.metricas.setdefault("fontes_ativas", 0)
        self.metricas.setdefault("fontes_com_erro", 0)
        self.metricas.setdefault("ultimos_alertas_enviados", 0)
        self.metricas.setdefault("ultima_execucao", None)
        self.metricas.setdefault("ultimo_erro", "nenhum")
        self.metricas.setdefault("falhas_fontes", {})
        self.metricas.setdefault("alertas_criticos", 0)
        self.metricas.setdefault("varredura_em_andamento", False)
        self.metricas.setdefault("promocoes_detectadas_ultimo_ciclo", 0)
        self.metricas.setdefault("startup_scan_concluido", False)

    def persistir(self):
        salvar_promocoes(self.promocoes)
        salvar_metricas(self.metricas)


STATE = RadarState()


def total_fontes_monitoradas() -> int:
    return (
        len(FONTES_RSS)
        + len(FONTES_OFICIAIS)
        + len(SITEMAP_SOURCES)
        + len(PUBLIC_MILEAGE_SOURCES)
        + len(PROMO_PAGES)
        + len(EARLY_DETECT_URLS)
    )


def executar_varredura():
    metricas = carregar_metricas()
    metricas["varredura_em_andamento"] = True
    metricas["fontes_monitoradas"] = metricas.get("fontes_monitoradas", 0) or total_fontes_monitoradas()
    salvar_metricas(metricas)

    try:
        itens, falhas = coletar_todas_fontes()

        fontes_monitoradas = total_fontes_monitoradas()
        fontes_com_erro = len(falhas)
        fontes_ativas = max(fontes_monitoradas - fontes_com_erro, 0)

        promocoes_detectadas = transformar_em_promocoes(itens)
        promocoes_detectadas = deduplicar(promocoes_detectadas)

        historico = carregar_promocoes()
        ids_existentes = {p.get("id") for p in historico}

        novas = []
        criticos = 0

        for promo in promocoes_detectadas:
            if promo.get("id") not in ids_existentes:
                novas.append(promo)
                historico.append(promo)
                if str(promo.get("alert_priority", "")).startswith("ð¨"):
                    criticos += 1

        historico = deduplicar(historico)
        historico = historico[-1500:] if len(historico) > 1500 else historico
        salvar_promocoes(historico)

        metricas = carregar_metricas()
        metricas["fontes_monitoradas"] = fontes_monitoradas
        metricas["fontes_ativas"] = fontes_ativas
        metricas["fontes_com_erro"] = fontes_com_erro
        metricas["falhas_fontes"] = falhas
        metricas["promocoes_detectadas_ultimo_ciclo"] = len(promocoes_detectadas)
        metricas["alertas_criticos"] = criticos
        metricas["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metricas["ultimo_erro"] = "nenhum"
        metricas["varredura_em_andamento"] = False
        metricas["startup_scan_concluido"] = True
        salvar_metricas(metricas)

        STATE.promocoes = historico
        STATE.metricas = metricas
        return {"novas": novas, "detectadas": len(promocoes_detectadas)}
    except Exception as e:
        metricas = carregar_metricas()
        metricas["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metricas["ultimo_erro"] = str(e)
        metricas["varredura_em_andamento"] = False
        salvar_metricas(metricas)
        STATE.metricas = metricas
        raise


def get_state_snapshot():
    promocoes = carregar_promocoes()
    metricas = carregar_metricas()

    metricas.setdefault("fontes_monitoradas", 0)
    metricas.setdefault("fontes_ativas", 0)
    metricas.setdefault("fontes_com_erro", 0)
    metricas.setdefault("ultimos_alertas_enviados", 0)
    metricas.setdefault("ultima_execucao", None)
    metricas.setdefault("ultimo_erro", "nenhum")
    metricas.setdefault("falhas_fontes", {})
    metricas.setdefault("alertas_criticos", 0)
    metricas.setdefault("varredura_em_andamento", False)
    metricas.setdefault("promocoes_detectadas_ultimo_ciclo", 0)
    metricas.setdefault("startup_scan_concluido", False)

    if not metricas.get("fontes_monitoradas"):
        metricas["fontes_monitoradas"] = total_fontes_monitoradas()

    STATE.promocoes = promocoes
    STATE.metricas = metricas
    return {"promocoes": promocoes, "metricas": metricas}


def get_promocoes_por_tipo(tipo: str, limit: int = 5) -> list:
    snapshot = get_state_snapshot()
    promos = [p for p in snapshot["promocoes"] if p.get("type") == tipo]
    promos = [p for p in promos if p.get("program") != "Programa nÃ£o identificado"]

    if tipo == "transferencias":
        bloqueios = [
            "credit card", "card", "welcome offer", "sign up", "signup",
            "marriott", "bonvoy", "brilliant card", "cartÃ£o", "cartao",
            "tier point", "tier points", "status bonus", "american airlines flights",
            "ba adds tier point", "tier bonuses",
            "compre pontos", "compra de pontos", "reativacao", "reativaÃ§Ã£o",
            "criar conta", "fazer login", "login", "boas vindas", "boas-vindas",
            "assine", "assinatura", "signature", "all signature",
            "hotel", "hoteis", "hotÃ©is", "desconto", "euros",
            "gaste em hotÃ©is", "gaste em hoteis",
            "acelere seus beneficios", "acelere seus benefÃ­cios",
        ]
        filtradas = []
        for p in promos:
            titulo = clean_text(p.get("title", "")).lower()
            link = clean_text(p.get("link", "")).lower()

            if any(term in titulo for term in bloqueios):
                continue
            if any(term in link for term in ["reativacao", "bonus-200", "signature"]):
                continue
            if titulo.startswith("http://") or titulo.startswith("https://"):
                continue

            bonus = int(p.get("bonus_detectado") or 0)
            if bonus < 30:
                continue

            filtradas.append(p)

        promos = filtradas

    promos = deduplicar(promos)
    promos = sorted(promos, key=lambda p: (p.get("ranking_score", 0), p.get("score", 0)), reverse=True)
    return promos[:limit]


def get_ranking(limit: int = 5) -> list:
    snapshot = get_state_snapshot()
    promos = [p for p in snapshot["promocoes"] if p.get("program") != "Programa nÃ£o identificado"]

    filtradas = []
    for p in promos:
        titulo = clean_text(p.get("title", ""))
        resumo = clean_text(p.get("title", ""))
        link = clean_text(p.get("link", "")).lower()

        titulo_l = titulo.lower()

        if any(term in titulo_l for term in RANKING_REJECT_TERMS):
            continue
        if titulo_l.startswith("http://") or titulo_l.startswith("https://"):
            continue
        if any(term in link for term in ["reativacao", "bonus-200", "signature", "login"]):
            continue
        if is_commercial_noise_for_ranking(titulo, resumo, link):
            continue

        if p.get("type") == "transferencias" and int(p.get("bonus_detectado") or 0) < 40:
            continue

        if p.get("type") == "milheiro" and p.get("milheiro_detectado") is None:
            continue

        if p.get("type") == "passagens":
            if any(term in titulo_l for term in ["confira", "sugestÃµes de voos", "sugestoes de voos"]):
                # aceita sÃ³ se for muito forte
                if float(p.get("score", 0)) < 9.0:
                    continue

        filtradas.append(p)

    filtradas = deduplicar(filtradas)
    filtradas = sorted(filtradas, key=lambda p: (p.get("ranking_score", 0), p.get("score", 0)), reverse=True)
    return filtradas[:limit]

# =========================================================
# TELEGRAM TEXT
# =========================================================


def build_status_text(interval_seconds: int) -> str:
    snapshot = get_state_snapshot()
    promocoes = snapshot["promocoes"]
    metricas = snapshot["metricas"]

    fontes_monitoradas = metricas.get("fontes_monitoradas", 0)
    fontes_ativas = metricas.get("fontes_ativas", 0)
    fontes_com_erro = metricas.get("fontes_com_erro", 0)
    promocoes_detectadas = metricas.get("promocoes_detectadas_ultimo_ciclo", 0)
    ultima_execucao = metricas.get("ultima_execucao") or "ainda nÃ£o executado"
    ultimo_erro = metricas.get("ultimo_erro", "nenhum")

    if metricas.get("varredura_em_andamento") and promocoes_detectadas == 0 and promocoes:
        promocoes_detectadas = len(promocoes)

    return (
        "ð¢ Radar online\n\n"
        f"â± Intervalo do radar: {interval_seconds} segundos\n"
        f"ð¥ PromoÃ§Ãµes detectadas: {promocoes_detectadas}\n"
        f"ð° Fontes monitoradas: {fontes_monitoradas}\n"
        f"â Fontes ativas: {fontes_ativas}\n"
        f"â Fontes com erro: {fontes_com_erro}\n"
        f"ð¨ Alertas crÃ­ticos no Ãºltimo ciclo: {metricas.get('alertas_criticos', 0)}\n"
        f"â³ Varredura em andamento: {'sim' if metricas.get('varredura_em_andamento') else 'nÃ£o'}\n\n"
        "Detectores ativos:\n"
        "â blogs\n"
        "â programas oficiais\n"
        "â sitemap e pÃ¡ginas internas\n"
        "â pÃ¡ginas promocionais\n"
        "â detector antecipado de promoÃ§Ãµes\n"
        "â transferÃªncias\n"
        "â milheiro barato\n"
        "â passagens baratas\n"
        "â score automÃ¡tico\n"
        "â envio no canal\n\n"
        f"ð¤ Ãltimos alertas enviados: {metricas.get('ultimos_alertas_enviados', 0)}\n"
        f"ð Ãltima execuÃ§Ã£o: {ultima_execucao}\n"
        f"â ï¸ Ãltimo erro: {ultimo_erro}"
    )


def build_debug_text() -> str:
    snapshot = get_state_snapshot()
    metricas = snapshot["metricas"]
    falhas = metricas.get("falhas_fontes", {})

    texto = (
        "ð  DEBUG RADAR\n"
        "ââââââââââââââ\n\n"
        f"Fontes monitoradas: {metricas.get('fontes_monitoradas', 0)}\n"
        f"Fontes ativas: {metricas.get('fontes_ativas', 0)}\n"
        f"Fontes com erro: {metricas.get('fontes_com_erro', 0)}\n"
        f"Ãltima execuÃ§Ã£o: {metricas.get('ultima_execucao') or 'ainda nÃ£o executado'}\n"
        f"Ãltimo erro geral: {metricas.get('ultimo_erro', 'nenhum')}\n\n"
        "Falhas por fonte\n"
        "ââââââââââââââ\n\n"
    )

    if not falhas:
        texto += "Nenhuma falha crÃ­tica detectada."
    else:
        for fonte, erro in falhas.items():
            texto += f"â¢ {fonte}: {erro}\n"

    return texto.strip()


def format_card(promo: dict) -> str:
    prioridade = promo.get("alert_priority", "ð¢ PROMOÃÃO BOA")
    texto = f"{prioridade}\n\n"
    texto += f"Programa: {promo.get('program', 'Programa nÃ£o identificado')}\n"
    texto += f"TÃ­tulo: {promo.get('title', '')}\n"
    if promo.get("bonus_detectado", 0):
        texto += f"BÃ´nus detectado: {promo.get('bonus_detectado')}%\n"
    if promo.get("milheiro_detectado") is not None:
        texto += f"Milheiro detectado: R$ {promo.get('milheiro_detectado'):.2f}\n"
    if promo.get("sweet_spot"):
        texto += "Sweet spot detectado: Sim\n"
    texto += f"Fonte: {promo.get('source_kind', 'rss')}\n"
    texto += f"Fontes confirmadas: {promo.get('fontes_confirmadas', 1)}\n"
    texto += f"Score: {promo.get('score', 0)}\n"
    texto += f"{promo.get('classification', 'ð¢ PROMOÃÃO BOA')}\n\n"
    texto += "Link:\n"
    texto += str(promo.get("link", ""))
    return texto


def format_lista(titulo: str, promocoes: list) -> str:
    if not promocoes:
        return f"{titulo}\n\nNenhuma promoÃ§Ã£o registrada ainda."

    partes = [titulo, ""]
    for promo in promocoes:
        partes.append("ââââââââââââââ")
        partes.append(f"Programa: {promo.get('program', 'Programa nÃ£o identificado')}")
        partes.append(f"TÃ­tulo: {promo.get('title', '')}")
        if promo.get("bonus_detectado", 0):
            partes.append(f"BÃ´nus detectado: {promo.get('bonus_detectado')}%")
        if promo.get("milheiro_detectado") is not None:
            partes.append(f"Milheiro detectado: R$ {promo.get('milheiro_detectado'):.2f}")
        if promo.get("sweet_spot"):
            partes.append("Sweet spot detectado: Sim")
        partes.append(f"Prioridade: {promo.get('alert_priority', 'ð¢ PROMOÃÃO BOA')}")
        partes.append(f"Score: {promo.get('score', 0)}")
        partes.append(f"{promo.get('classification', 'ð¢ PROMOÃÃO BOA')}")
        partes.append("Link:")
        partes.append(str(promo.get("link", "")))
    partes.append("ââââââââââââââ")
    return "\n".join(partes)

# =========================================================
# TELEGRAM BOT
# =========================================================

SCAN_LOCK = asyncio.Lock()
_APP = None


def is_admin(update: Update) -> bool:
    if not ADMIN_IDS:
        return True
    if not update.effective_chat:
        return False
    return update.effective_chat.id in ADMIN_IDS


async def _run_scan() -> dict:
    async with SCAN_LOCK:
        result = await asyncio.to_thread(executar_varredura)
        novas = result.get("novas", [])
        detectadas = result.get("detectadas", 0)

        for promo in novas:
            await _APP.bot.send_message(
                chat_id=CANAL_ID,
                text=format_card(promo),
                disable_web_page_preview=True,
            )

        metricas = carregar_metricas()
        metricas["ultimos_alertas_enviados"] = len(novas)
        metricas["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metricas["ultimo_erro"] = "nenhum"
        metricas["varredura_em_andamento"] = False
        metricas["startup_scan_concluido"] = True
        salvar_metricas(metricas)

        STATE.metricas = metricas
        STATE.promocoes = carregar_promocoes()
        return {"detectadas": detectadas, "novas": len(novas)}


async def _scheduled_scan():
    try:
        await _run_scan()
    except Exception as e:
        metricas = carregar_metricas()
        metricas["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metricas["ultimo_erro"] = str(e)
        metricas["varredura_em_andamento"] = False
        salvar_metricas(metricas)
        STATE.metricas = metricas


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "âï¸ Radar de Milhas PRO\n\n"
        "/menu\n"
        "/promocoes\n"
        "/transferencias\n"
        "/passagens\n"
        "/ranking\n"
        "/status",
        disable_web_page_preview=True,
    )


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ð¡ MENU\n\n"
        "/promocoes\n"
        "/transferencias\n"
        "/passagens\n"
        "/ranking\n"
        "/status\n"
        "/testeradar\n"
        "/debug",
        disable_web_page_preview=True,
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_status_text(RADAR_INTERVAL_SECONDS), disable_web_page_preview=True)


async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("â Comando disponÃ­vel apenas para o administrador.")
        return
    await update.message.reply_text(build_debug_text(), disable_web_page_preview=True)


async def cmd_promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_ranking(limit=5)
    await update.message.reply_text(format_lista("ð¥ Ãltimas promoÃ§Ãµes", promos), disable_web_page_preview=True)


async def cmd_transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_promocoes_por_tipo("transferencias", limit=5)
    if not promos:
        texto = "ð³ PromoÃ§Ãµes de transferÃªncias de pontos monitoradas\n\nNenhuma transferÃªncia promocional ativa detectada no momento."
    else:
        texto = format_lista("ð³ PromoÃ§Ãµes de transferÃªncias de pontos monitoradas", promos)
    await update.message.reply_text(texto, disable_web_page_preview=True)


async def cmd_passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_promocoes_por_tipo("passagens", limit=5)
    await update.message.reply_text(format_lista("âï¸ Ãltimos alertas de passagens", promos), disable_web_page_preview=True)


async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_ranking(limit=MAX_RANKING if MAX_RANKING < 6 else 5)
    if not promos:
        await update.message.reply_text(
            "ð Ranking oportunidades\n\nNenhuma promoÃ§Ã£o registrada ainda.",
            disable_web_page_preview=True,
        )
        return

    linhas = ["ð Ranking oportunidades", ""]
    for i, promo in enumerate(promos, start=1):
        linhas.append(f"{i}. {promo.get('program', 'Programa nÃ£o identificado')}")
        linhas.append(f"{promo.get('title', '')}")
        linhas.append(f"Prioridade: {promo.get('alert_priority', 'ð¢ PROMOÃÃO BOA')}")
        linhas.append(f"Score: {promo.get('score', 0)}")
        linhas.append(f"{promo.get('classification', 'ð¢ PROMOÃÃO BOA')}")
        if i != len(promos):
            linhas.append("")
            linhas.append("ââââââââââââââ")
            linhas.append("")

    await update.message.reply_text("\n".join(linhas), disable_web_page_preview=True)


async def cmd_testeradar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("â Comando disponÃ­vel apenas para o administrador.")
        return

    if SCAN_LOCK.locked():
        await update.message.reply_text(
            "â³ JÃ¡ existe uma varredura em andamento. Aguarde terminar.",
            disable_web_page_preview=True,
        )
        return

    await update.message.reply_text("ð§ª Teste manual do radar iniciado...", disable_web_page_preview=True)
    try:
        result = await _run_scan()
        metricas = carregar_metricas()
        await update.message.reply_text(
            "â Teste manual concluÃ­do.\n\n"
            f"Fontes monitoradas: {metricas.get('fontes_monitoradas', 0)}\n"
            f"Fontes ativas: {metricas.get('fontes_ativas', 0)}\n"
            f"Fontes com erro: {metricas.get('fontes_com_erro', 0)}\n"
            f"PromoÃ§Ãµes analisadas: {result.get('detectadas', 0)}\n"
            f"Novas promoÃ§Ãµes enviadas: {result.get('novas', 0)}\n"
            f"Alertas crÃ­ticos no Ãºltimo ciclo: {metricas.get('alertas_criticos', 0)}\n"
            f"Ãltimo erro: {metricas.get('ultimo_erro', 'nenhum')}",
            disable_web_page_preview=True,
        )
    except Exception as e:
        metricas = carregar_metricas()
        metricas["ultimo_erro"] = str(e)
        metricas["varredura_em_andamento"] = False
        salvar_metricas(metricas)
        await update.message.reply_text(f"â Erro ao executar o radar: {e}", disable_web_page_preview=True)


async def _startup_scan_with_delay():
    await asyncio.sleep(3)
    if not SCAN_LOCK.locked():
        await _scheduled_scan()


async def post_init(application):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _scheduled_scan,
        "interval",
        seconds=RADAR_INTERVAL_SECONDS,
        next_run_time=datetime.now() + timedelta(seconds=RADAR_INTERVAL_SECONDS),
        id="radar_scan",
        replace_existing=True,
    )
    scheduler.start()
    application.bot_data["scheduler"] = scheduler

    metricas = carregar_metricas()
    metricas["varredura_em_andamento"] = True
    metricas["fontes_monitoradas"] = metricas.get("fontes_monitoradas", 0) or total_fontes_monitoradas()
    salvar_metricas(metricas)

    asyncio.create_task(_startup_scan_with_delay())


async def post_shutdown(application):
    scheduler = application.bot_data.get("scheduler")
    if scheduler:
        scheduler.shutdown(wait=False)


def main():
    global _APP

    _APP = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    _APP.add_handler(CommandHandler("start", cmd_start))
    _APP.add_handler(CommandHandler("menu", cmd_menu))
    _APP.add_handler(CommandHandler("status", cmd_status))
    _APP.add_handler(CommandHandler("debug", cmd_debug))
    _APP.add_handler(CommandHandler("promocoes", cmd_promocoes))
    _APP.add_handler(CommandHandler("transferencias", cmd_transferencias))
    _APP.add_handler(CommandHandler("passagens", cmd_passagens))
    _APP.add_handler(CommandHandler("ranking", cmd_ranking))
    _APP.add_handler(CommandHandler("testeradar", cmd_testeradar))

    _APP.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
