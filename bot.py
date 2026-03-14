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
    raise RuntimeError("Variável TELEGRAM_TOKEN não configurada.")
if not CANAL_ID:
    raise RuntimeError("Variável CANAL_ID não configurada.")

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

# Detector antecipado mais agressivo
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
    "seja bem-vindo a mais uma edição do radar ppv",
    "a última edição do radar ppv da semana chegou",
    "a última edição do radar ppv",
    "resumo das promoções",
    "resumo promoções",
    "a promoção do",
    "a smiles está oferecendo",
    "o smiles voltou a oferecer",
    "nesta oferta, é possível",
    "confira os detalhes para participar e aproveitar a oferta",
    "atenção: a busca dessas emissões foi realizada no momento da produção",
    "está planejando aquela viagem dos sonhos",
    "então está no lugar certo",
    "no artigo de hoje, separamos",
    "o post",
]

GENERIC_TRANSFER_TERMS = [
    "radar ppv",
    "resumo das promoções",
    "resumo promoções",
    "seja bem-vindo a mais uma edição",
    "a última edição",
    "edição do radar",
]

TRANSFER_ACCEPT_TERMS = [
    "transferência bonificada",
    "transferencia bonificada",
    "acúmulo com parceiro",
    "acumulo com parceiro",
    "campanhas híbridas",
    "campanhas hibridas",
    "campanha híbrida",
    "campanha hibrida",
    "transferência",
    "transferencia",
    "bônus",
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
    "parceiros",
    "parceiro varejista",
    "campanha de acúmulo",
    "campanha de acumulo",
    "acúmulo comum",
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
    "cartão",
    "cartao",
    "tier point",
    "tier points",
    "status bonus",
    "elite bonus",
    "american airlines flights",
    "mileage earnings",
    "tier bonuses",
]

ANTI_SPAM_TERMS = [
    "radar ppv",
    "resumo da semana",
    "resumo do dia",
    "resumo das promoções",
    "última chamada",
    "ultima chamada",
    "última edição",
    "ultima edição",
    "review",
    "guia",
    "dicas",
    "vale a pena",
    "como funciona",
    "melhores cartões",
    "melhores cartoes",
    "promoções que terminam hoje",
    "promocoes que terminam hoje",
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
    "amex",
    "american express",
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

    lixo = ["â€¢", "â€", "â€™", "â€œ", "Ã", "ð", "Â", "â", "¤", "�"]
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
    candidates = [". ", "! ", "? ", " - ", " – ", ": "]
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


def is_generic_transfer_post(texto: str) -> bool:
    t = clean_text(texto).lower()
    return any(term in t for term in GENERIC_TRANSFER_TERMS)


def is_strict_transfer_post(texto: str) -> bool:
    t = clean_text(texto).lower()
    has_accept = any(term in t for term in TRANSFER_ACCEPT_TERMS)
    has_reject = any(term in t for term in TRANSFER_REJECT_TERMS)
    return has_accept and not has_reject


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


def build_short_title(title: str, summary: str = "", link: str = "", max_len: int = 140) -> str:
    title = clean_text(title)
    summary = clean_text(summary)

    if title.startswith("http://") or title.startswith("https://"):
        title = title_from_url(title)

    title = strip_noise_phrases(title)
    summary = strip_noise_phrases(summary)

    if summary.startswith("http://") or summary.startswith("https://"):
        summary = title_from_url(summary)

    base = title if title else summary
    if not base and link:
        base = title_from_url(link)

    for pat in [
        r"\bsaiba mais\b",
        r"\bpublicidade\b",
        r"\bdeixe um coment[aá]rio\b",
        r"\bsegue valendo!?+\b",
        r"\bprorrogou!?+\b",
        r"\b\d+\s+horas?\s+atr[aá]s\b",
        r"\b\d{1,2}\s+de\s+[a-zçãé]+\s+de\s+\d{4}\b",
    ]:
        base = re.sub(pat, " ", base, flags=re.I)

    base = normalize_spaces(base)
    return sentence_crop(base, max_len=max_len)

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
        "promo", "promoco", "oferta", "offer", "bonus", "bônus",
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
# DETECÇÃO
# =========================================================


def _detect_program(texto: str, program_hint=None):
    if program_hint:
        return program_hint

    t = clean_text(texto).lower()

    mapping = {
        "smiles": "Smiles",
        "clube smiles": "Smiles",
        "latam": "LATAM Pass",
        "latam pass": "LATAM Pass",
        "azul": "TudoAzul",
        "tudoazul": "TudoAzul",
        "clube azul": "TudoAzul",
        "livelo": "Livelo",
        "esfera": "Esfera",
        "accor": "ALL Accor",
        "all accor": "ALL Accor",
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
    if any(k in t for k in ["miami", "orlando", "europa", "madrid", "lisboa", "paris", "roma", "nova york", "new york"]):
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
        ("transfer" in t or "bônus" in t or "bonus" in t or "bonificada" in t or "converta pontos" in t or "envie pontos" in t)
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
        return "🔴 PROMOÇÃO IMPERDÍVEL"
    if score >= 8.0:
        return "🟡 PROMOÇÃO MUITO BOA"
    if score >= 7.0:
        return "🟢 PROMOÇÃO BOA"
    return "⚪ PROMOÇÃO REGULAR"


def _alerta_prioridade(tipo: str, score: float, bonus: int, milheiro: float | None, sweet_spot: bool) -> str:
    if tipo == "transferencias" and bonus >= 100:
        return "🚨 BÔNUS ALTO DETECTADO"
    if tipo == "transferencias" and bonus >= 80:
        return "🔥 BÔNUS FORTE DETECTADO"
    if tipo == "milheiro" and milheiro is not None and milheiro <= 10:
        return "🚨 MILHEIRO MUITO BARATO"
    if tipo == "milheiro" and milheiro is not None and milheiro <= 11:
        return "🔥 MILHEIRO BARATO DETECTADO"
    if tipo == "passagens" and sweet_spot:
        return "🚨 RESGATE BARATO DETECTADO"
    if score >= 9.0:
        return "🚨 ALERTA CRÍTICO"
    if score >= 8.0:
        return "🔥 ALERTA IMPORTANTE"
    if score >= 7.0:
        return "🟢 PROMOÇÃO BOA"
    return "⚪ INFORMATIVO"


def _peso_categoria(tipo: str) -> float:
    if tipo == "milheiro":
        return 1.0
    if tipo == "transferencias":
        return 0.9
    if tipo == "passagens":
        return 0.8
    return 0.3


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
        ranking_score = round(score * _peso_categoria(tipo), 2)

        # detector antecipado ganha um pequeno peso extra
        if source_kind in {"sitemap", "official", "promo_page", "early_detect"}:
            ranking_score = round(ranking_score + 0.15, 2)

        promo = {
            "id": _build_id(titulo_curto, link, tipo, program or "", bonus),
            "title": titulo_curto,
            "link": link,
            "type": tipo,
            "program": program or "Programa não identificado",
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
    STATE.metricas["varredura_em_andamento"] = True
    STATE.metricas["fontes_monitoradas"] = total_fontes_monitoradas()
    STATE.persistir()

    try:
        itens, falhas = coletar_todas_fontes()

        fontes_monitoradas = total_fontes_monitoradas()
        fontes_com_erro = len(falhas)
        fontes_ativas = max(fontes_monitoradas - fontes_com_erro, 0)

        STATE.metricas["fontes_monitoradas"] = fontes_monitoradas
        STATE.metricas["fontes_ativas"] = fontes_ativas
        STATE.metricas["fontes_com_erro"] = fontes_com_erro
        STATE.metricas["falhas_fontes"] = falhas

        promocoes_detectadas = transformar_em_promocoes(itens)
        promocoes_detectadas = deduplicar(promocoes_detectadas)
        STATE.metricas["promocoes_detectadas_ultimo_ciclo"] = len(promocoes_detectadas)
        STATE.persistir()

        historico = carregar_promocoes()
        ids_existentes = {p.get("id") for p in historico}

        novas = []
        criticos = 0

        for promo in promocoes_detectadas:
            if promo.get("id") not in ids_existentes:
                novas.append(promo)
                historico.append(promo)
                if str(promo.get("alert_priority", "")).startswith("🚨"):
                    criticos += 1

        historico = deduplicar(historico)
        STATE.promocoes = historico[-1500:] if len(historico) > 1500 else historico
        STATE.metricas["alertas_criticos"] = criticos
        STATE.metricas["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.metricas["ultimo_erro"] = "nenhum"
        STATE.metricas["varredura_em_andamento"] = False
        STATE.persistir()

        return {"novas": novas, "detectadas": len(promocoes_detectadas)}
    except Exception as e:
        STATE.metricas["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.metricas["ultimo_erro"] = str(e)
        STATE.metricas["varredura_em_andamento"] = False
        STATE.persistir()
        raise


def get_state_snapshot():
    STATE.promocoes = carregar_promocoes()
    STATE.metricas = carregar_metricas()
    return {"promocoes": STATE.promocoes, "metricas": STATE.metricas}


def get_promocoes_por_tipo(tipo: str, limit: int = 5) -> list:
    snapshot = get_state_snapshot()
    promos = [p for p in snapshot["promocoes"] if p.get("type") == tipo]
    promos = [p for p in promos if p.get("program") != "Programa não identificado"]

    if tipo == "transferencias":
        bloqueios = [
            "credit card", "card", "welcome offer", "sign up", "signup",
            "marriott", "bonvoy", "brilliant card", "cartão", "cartao",
            "tier point", "tier points", "status bonus", "american airlines flights",
            "ba adds tier point", "tier bonuses",
        ]
        filtradas = []
        for p in promos:
            titulo = clean_text(p.get("title", "")).lower()
            if any(term in titulo for term in bloqueios):
                continue
            if titulo.startswith("http://") or titulo.startswith("https://"):
                continue
            filtradas.append(p)
        promos = filtradas

    promos = deduplicar(promos)
    promos = sorted(promos, key=lambda p: (p.get("ranking_score", 0), p.get("score", 0)), reverse=True)
    return promos[:limit]


def get_ranking(limit: int = 5) -> list:
    snapshot = get_state_snapshot()
    promos = [p for p in snapshot["promocoes"] if p.get("program") != "Programa não identificado"]

    filtradas = []
    for p in promos:
        titulo = clean_text(p.get("title", "")).lower()
        if any(term in titulo for term in ANTI_SPAM_TERMS):
            continue
        if titulo.startswith("http://") or titulo.startswith("https://"):
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
    metricas = snapshot["metricas"]

    fontes_monitoradas = metricas.get("fontes_monitoradas", 0)
    fontes_ativas = metricas.get("fontes_ativas", 0)
    fontes_com_erro = metricas.get("fontes_com_erro", 0)
    promocoes_detectadas = metricas.get("promocoes_detectadas_ultimo_ciclo", 0)
    ultima_execucao = metricas.get("ultima_execucao") or "ainda não executado"
    ultimo_erro = metricas.get("ultimo_erro", "nenhum")

    if metricas.get("varredura_em_andamento") and fontes_monitoradas == 0:
        fontes_monitoradas = total_fontes_monitoradas()

    return (
        "🟢 Radar online\n\n"
        f"⏱ Intervalo do radar: {interval_seconds} segundos\n"
        f"📥 Promoções detectadas: {promocoes_detectadas}\n"
        f"🛰 Fontes monitoradas: {fontes_monitoradas}\n"
        f"✅ Fontes ativas: {fontes_ativas}\n"
        f"❌ Fontes com erro: {fontes_com_erro}\n"
        f"🚨 Alertas críticos no último ciclo: {metricas.get('alertas_criticos', 0)}\n"
        f"⏳ Varredura em andamento: {'sim' if metricas.get('varredura_em_andamento') else 'não'}\n\n"
        "Detectores ativos:\n"
        "✓ blogs\n"
        "✓ programas oficiais\n"
        "✓ sitemap e páginas internas\n"
        "✓ páginas promocionais\n"
        "✓ detector antecipado de promoções\n"
        "✓ transferências\n"
        "✓ milheiro barato\n"
        "✓ passagens baratas\n"
        "✓ score automático\n"
        "✓ envio no canal\n\n"
        f"📤 Últimos alertas enviados: {metricas.get('ultimos_alertas_enviados', 0)}\n"
        f"🕒 Última execução: {ultima_execucao}\n"
        f"⚠️ Último erro: {ultimo_erro}"
    )


def build_debug_text() -> str:
    snapshot = get_state_snapshot()
    metricas = snapshot["metricas"]
    falhas = metricas.get("falhas_fontes", {})

    texto = (
        "🛠 DEBUG RADAR\n"
        "━━━━━━━━━━━━━━\n\n"
        f"Fontes monitoradas: {metricas.get('fontes_monitoradas', 0)}\n"
        f"Fontes ativas: {metricas.get('fontes_ativas', 0)}\n"
        f"Fontes com erro: {metricas.get('fontes_com_erro', 0)}\n"
        f"Última execução: {metricas.get('ultima_execucao') or 'ainda não executado'}\n"
        f"Último erro geral: {metricas.get('ultimo_erro', 'nenhum')}\n\n"
        "Falhas por fonte\n"
        "━━━━━━━━━━━━━━\n\n"
    )

    if not falhas:
        texto += "Nenhuma falha crítica detectada."
    else:
        for fonte, erro in falhas.items():
            texto += f"• {fonte}: {erro}\n"

    return texto.strip()


def format_card(promo: dict) -> str:
    prioridade = promo.get("alert_priority", "🟢 PROMOÇÃO BOA")
    texto = f"{prioridade}\n\n"
    texto += f"Programa: {promo.get('program', 'Programa não identificado')}\n"
    texto += f"Título: {promo.get('title', '')}\n"
    if promo.get("bonus_detectado", 0):
        texto += f"Bônus detectado: {promo.get('bonus_detectado')}%\n"
    if promo.get("milheiro_detectado") is not None:
        texto += f"Milheiro detectado: R$ {promo.get('milheiro_detectado'):.2f}\n"
    if promo.get("sweet_spot"):
        texto += "Sweet spot detectado: Sim\n"
    texto += f"Fonte: {promo.get('source_kind', 'rss')}\n"
    texto += f"Fontes confirmadas: {promo.get('fontes_confirmadas', 1)}\n"
    texto += f"Score: {promo.get('score', 0)}\n"
    texto += f"{promo.get('classification', '🟢 PROMOÇÃO BOA')}\n\n"
    texto += "Link:\n"
    texto += str(promo.get("link", ""))
    return texto


def format_lista(titulo: str, promocoes: list) -> str:
    if not promocoes:
        return f"{titulo}\n\nNenhuma promoção registrada ainda."

    partes = [titulo, ""]
    for promo in promocoes:
        partes.append("━━━━━━━━━━━━━━")
        partes.append(f"Programa: {promo.get('program', 'Programa não identificado')}")
        partes.append(f"Título: {promo.get('title', '')}")
        if promo.get("bonus_detectado", 0):
            partes.append(f"Bônus detectado: {promo.get('bonus_detectado')}%")
        if promo.get("milheiro_detectado") is not None:
            partes.append(f"Milheiro detectado: R$ {promo.get('milheiro_detectado'):.2f}")
        if promo.get("sweet_spot"):
            partes.append("Sweet spot detectado: Sim")
        partes.append(f"Prioridade: {promo.get('alert_priority', '🟢 PROMOÇÃO BOA')}")
        partes.append(f"Score: {promo.get('score', 0)}")
        partes.append(f"{promo.get('classification', '🟢 PROMOÇÃO BOA')}")
        partes.append("Link:")
        partes.append(str(promo.get("link", "")))
    partes.append("━━━━━━━━━━━━━━")
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

        STATE.metricas["ultimos_alertas_enviados"] = len(novas)
        STATE.metricas["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.metricas["ultimo_erro"] = "nenhum"
        STATE.metricas["varredura_em_andamento"] = False
        STATE.persistir()

        return {"detectadas": detectadas, "novas": len(novas)}


async def _scheduled_scan():
    try:
        await _run_scan()
    except Exception as e:
        STATE.metricas["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.metricas["ultimo_erro"] = str(e)
        STATE.metricas["varredura_em_andamento"] = False
        STATE.persistir()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✈️ Radar de Milhas PRO\n\n"
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
        "📡 MENU\n\n"
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
        await update.message.reply_text("⛔ Comando disponível apenas para o administrador.")
        return
    await update.message.reply_text(build_debug_text(), disable_web_page_preview=True)


async def cmd_promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_ranking(limit=5)
    await update.message.reply_text(format_lista("🔥 Últimas promoções", promos), disable_web_page_preview=True)


async def cmd_transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_promocoes_por_tipo("transferencias", limit=5)
    if not promos:
        texto = "💳 Promoções de transferências de pontos monitoradas\n\nNenhuma transferência promocional ativa detectada no momento."
    else:
        texto = format_lista("💳 Promoções de transferências de pontos monitoradas", promos)
    await update.message.reply_text(texto, disable_web_page_preview=True)


async def cmd_passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_promocoes_por_tipo("passagens", limit=5)
    await update.message.reply_text(format_lista("✈️ Últimos alertas de passagens", promos), disable_web_page_preview=True)


async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_ranking(limit=MAX_RANKING if MAX_RANKING < 6 else 5)
    if not promos:
        await update.message.reply_text("🏆 Ranking oportunidades\n\nNenhuma promoção registrada ainda.", disable_web_page_preview=True)
        return

    linhas = ["🏆 Ranking oportunidades", ""]
    for i, promo in enumerate(promos, start=1):
        linhas.append(f"{i}. {promo.get('program', 'Programa não identificado')}")
        linhas.append(f"{promo.get('title', '')}")
        linhas.append(f"Prioridade: {promo.get('alert_priority', '🟢 PROMOÇÃO BOA')}")
        linhas.append(f"Score: {promo.get('score', 0)}")
        linhas.append(f"{promo.get('classification', '🟢 PROMOÇÃO BOA')}")
        if i != len(promos):
            linhas.append("")
            linhas.append("━━━━━━━━━━━━━━")
            linhas.append("")
    await update.message.reply_text("\n".join(linhas), disable_web_page_preview=True)


async def cmd_testeradar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Comando disponível apenas para o administrador.")
        return

    if SCAN_LOCK.locked():
        await update.message.reply_text("⏳ Já existe uma varredura em andamento. Aguarde terminar.", disable_web_page_preview=True)
        return

    await update.message.reply_text("🧪 Teste manual do radar iniciado...", disable_web_page_preview=True)
    try:
        result = await _run_scan()
        await update.message.reply_text(
            "✅ Teste manual concluído.\n\n"
            f"Fontes monitoradas: {STATE.metricas.get('fontes_monitoradas', 0)}\n"
            f"Fontes ativas: {STATE.metricas.get('fontes_ativas', 0)}\n"
            f"Fontes com erro: {STATE.metricas.get('fontes_com_erro', 0)}\n"
            f"Promoções analisadas: {result.get('detectadas', 0)}\n"
            f"Novas promoções enviadas: {result.get('novas', 0)}\n"
            f"Alertas críticos no último ciclo: {STATE.metricas.get('alertas_criticos', 0)}\n"
            f"Último erro: {STATE.metricas.get('ultimo_erro', 'nenhum')}",
            disable_web_page_preview=True,
        )
    except Exception as e:
        STATE.metricas["ultimo_erro"] = str(e)
        STATE.metricas["varredura_em_andamento"] = False
        STATE.persistir()
        await update.message.reply_text(f"❌ Erro ao executar o radar: {e}", disable_web_page_preview=True)


async def post_init(application):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _scheduled_scan,
        "interval",
        seconds=RADAR_INTERVAL_SECONDS,
        next_run_time=datetime.now(),
        id="radar_scan",
        replace_existing=True,
    )
    scheduler.start()
    application.bot_data["scheduler"] = scheduler


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
