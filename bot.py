import os
import re
import json
import html
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urljoin, urlparse
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
    # Brasil
    "https://passageirodeprimeira.com/feed",
    "https://pontospravoar.com/feed",
    "https://www.melhoresdestinos.com.br/feed",
    "https://aeroin.net/feed",
    "https://www.melhorescartoes.com.br/feed",
    "https://www.falandodeviagem.com.br/viewtopic.php?f=26&t=13216&start=0&view=print",  # may fail safely
    # Global milhas / loyalty
    "https://onemileatatime.com/feed/",
    "https://viewfromthewing.com/feed/",
    "https://frequentmiler.com/feed/",
    "https://loyaltylobby.com/feed/",
    "https://upgradedpoints.com/feed/",
    "https://thepointsguy.com/feed/",
    "https://awardwallet.com/blog/feed/",
    "https://godsavethepoints.com/feed/",
    "https://thriftytraveler.com/feed/",
    "https://www.flyertalk.com/forum/external.php?type=RSS2",
    "https://www.secretflying.com/feed/",
    "https://www.fly4free.com/feed/",
]

FONTES_OFICIAIS = [
    {"program": "Smiles", "type_hint": "transferencias", "url": "https://www.smiles.com.br/promocoes"},
    {"program": "Smiles", "type_hint": "milheiro", "url": "https://www.smiles.com.br/clube-smiles"},
    {"program": "Smiles", "type_hint": "milheiro", "url": "https://www.smiles.com.br/home"},
    {"program": "LATAM Pass", "type_hint": "passagens", "url": "https://latampass.latam.com/"},
    {"program": "TudoAzul", "type_hint": "passagens", "url": "https://www.voeazul.com.br/"},
    {"program": "Livelo", "type_hint": "transferencias", "url": "https://www.livelo.com.br/"},
    {"program": "Livelo", "type_hint": "milheiro", "url": "https://www.livelo.com.br/clube"},
    {"program": "Esfera", "type_hint": "transferencias", "url": "https://www.esfera.com.vc/"},
    {"program": "Esfera", "type_hint": "milheiro", "url": "https://www.esfera.com.vc/clube"},
    {"program": "ALL Accor", "type_hint": "transferencias", "url": "https://all.accor.com/loyalty-program/index.pt.shtml"},
    {"program": "Iberia", "type_hint": "passagens", "url": "https://www.iberia.com/"},
    {"program": "TAP", "type_hint": "passagens", "url": "https://www.flytap.com/"},
    {"program": "Flying Blue", "type_hint": "passagens", "url": "https://www.flyingblue.com/"},
    {"program": "British Airways", "type_hint": "passagens", "url": "https://www.britishairways.com/"},
    {"program": "KrisFlyer", "type_hint": "passagens", "url": "https://www.singaporeair.com/"},
    {"program": "Amex", "type_hint": "transferencias", "url": "https://www.americanexpress.com/"},
]

SITEMAP_SOURCES = [
    {"program": "Smiles", "url": "https://www.smiles.com.br/sitemap.xml"},
    {"program": "Livelo", "url": "https://www.livelo.com.br/sitemap.xml"},
    {"program": "Esfera", "url": "https://www.esfera.com.vc/sitemap.xml"},
    {"program": "LATAM Pass", "url": "https://latampass.latam.com/sitemap.xml"},
]

PUBLIC_MILEAGE_SOURCES = [
    {"program": "Mercado de Milhas", "url": "https://www.maxmilhas.com.br"},
    {"program": "Mercado de Milhas", "url": "https://123milhas.com/"},
    {"program": "Smiles", "url": "https://www.smiles.com.br/clube-smiles"},
    {"program": "Livelo", "url": "https://www.livelo.com.br/compra-de-pontos/produto/LIVCompraDePontos"},
    {"program": "Esfera", "url": "https://www.esfera.com.vc/clube"},
]

# =========================================================
# TEXT CLEANING
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
    "transferÃªncia bonificada", "transferencia bonificada",
    "acÃºmulo com parceiro", "acumulo com parceiro",
    "campanhas hÃ­bridas", "campanhas hibridas",
    "campanha hÃ­brida", "campanha hibrida",
    "transferÃªncia", "transferencia",
    "bÃ´nus", "bonus", "bonificada",
    "envie pontos", "converta pontos", "converta seus pontos",
    "transfira pontos", "transferir pontos",
]

TRANSFER_REJECT_TERMS = [
    "pontos por real gasto", "por real gasto",
    "varejo", "parceiros", "parceiro varejista",
    "campanha de acÃºmulo", "campanha de acumulo",
    "acÃºmulo comum", "acumulo comum",
]

PROGRAMAS = [
    "smiles", "latam pass", "latam", "azul fidelidade", "tudoazul",
    "livelo", "esfera", "all accor", "krisflyer", "iberia",
    "tap", "amex", "american express", "flying blue", "avios",
    "british airways", "delta", "emirates", "qatar", "turkish",
]

BANCOS = [
    "itau", "itaÃº", "bradesco", "santander", "banco do brasil", "bb", "caixa",
    "c6", "inter", "xp", "btg", "neon", "nubank", "sicoob", "sicredi",
    "amex", "american express",
]

RUIDO = [
    "deixe um comentÃ¡rio", "deixe um comentario", "publicidade", "saiba mais",
    "10 horas atrÃ¡s", "horas atrÃ¡s", "vale a pena", "review", "guia", "dicas",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    )
}

def clean_text(texto: str) -> str:
    texto = html.unescape(str(texto or ""))
    texto = texto.replace("&#8230;", ".")
    texto = texto.replace("\u2026", ".")
    texto = BeautifulSoup(texto, "html.parser").get_text(" ", strip=True)
    texto = re.sub(r'https?://\S+', ' ', texto)
    texto = re.sub(r'<[^>]+>', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
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

def build_short_title(title: str, summary: str = "", max_len: int = 140) -> str:
    title = clean_text(title)
    summary = clean_text(summary)
    title = strip_noise_phrases(title)
    summary = strip_noise_phrases(summary)
    base = title if title else summary
    for pat in [
        r"\bsaiba mais\b", r"\bpublicidade\b", r"\bdeixe um coment[aÃ¡]rio\b",
        r"\bsegue valendo!?+\b", r"\bprorrogou!?+\b",
        r"\b\d+\s+horas?\s+atr[aÃ¡]s\b",
        r"\b\d{1,2}\s+de\s+[a-zÃ§Ã£Ã©]+\s+de\s+\d{4}\b",
    ]:
        base = re.sub(pat, " ", base, flags=re.I)
    base = normalize_spaces(base)
    return sentence_crop(base, max_len=max_len)

def compact_text(texto: str, max_len: int = 95) -> str:
    texto = clean_text(texto)
    texto = strip_noise_phrases(texto)
    texto = normalize_spaces(texto)
    if len(texto) <= max_len:
        return texto
    cut = texto[:max_len].rsplit(" ", 1)[0].strip()
    return cut + "..."

def is_generic_transfer_post(texto: str) -> bool:
    t = clean_text(texto).lower()
    return any(term in t for term in GENERIC_TRANSFER_TERMS)

def is_strict_transfer_post(texto: str) -> bool:
    t = clean_text(texto).lower()
    has_accept = any(term in t for term in TRANSFER_ACCEPT_TERMS)
    has_reject = any(term in t for term in TRANSFER_REJECT_TERMS)
    return has_accept and not has_reject

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

def _assinatura(promo: dict) -> str:
    return "|".join([
        _norm_assinatura(promo.get("type")),
        _norm_assinatura(promo.get("program")),
        _norm_assinatura(promo.get("title")),
        _norm_assinatura(promo.get("link")),
    ])

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
# HTTP HELPERS
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
    for tag in soup.find_all(["p", "span", "div", "li"]):
        txt = tag.get_text(" ", strip=True)
        if txt and len(txt) > 20:
            parts.append(txt)
        if len(" ".join(parts)) > 3500:
            break
    return clean_text(" ".join(parts))[:4000]

# =========================================================
# COLLECTORS
# =========================================================

def coletar_rss():
    itens = []
    falhas = {}
    for url in FONTES_RSS:
        try:
            feed = feedparser.parse(url)
            entries = getattr(feed, "entries", [])
            for entry in entries[:25]:
                itens.append(
                    {
                        "title": clean_text(entry.get("title", "") or ""),
                        "link": entry.get("link", "") or "",
                        "summary": clean_text(entry.get("summary", "") or ""),
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
                    "title": texto,
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
        "comprar", "compra", "resgate",
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
                for sitemap_url in first_level[:5]:
                    try:
                        s_resp = safe_get(sitemap_url)
                        s_resp.raise_for_status()
                        collected.extend(_parse_sitemap_xml(s_resp.text)[:20])
                    except Exception:
                        continue
            else:
                collected = first_level[:30]

            filtered = []
            seen = set()
            for url in collected:
                if _interesting_url(url) and url not in seen:
                    seen.add(url)
                    filtered.append(url)

            for url in filtered[:20]:
                itens.append({
                    "title": urlparse(url).path.replace("-", " ").replace("/", " "),
                    "link": url,
                    "summary": url,
                    "source_url": fonte["url"],
                    "source_kind": "sitemap",
                    "type_hint": None,
                    "program_hint": fonte["program"],
                })
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
            itens.append({
                "title": texto,
                "link": str(resp.url),
                "summary": texto,
                "source_url": fonte["url"],
                "source_kind": "marketplace",
                "type_hint": "milheiro",
                "program_hint": fonte["program"],
            })
        except Exception as e:
            falhas[fonte["url"]] = str(e)
    return itens, falhas

def coletar_todas_fontes():
    itens = []
    falhas = {}

    for collector in [coletar_rss, coletar_paginas_oficiais, coletar_sitemaps, coletar_milheiro_publico]:
        c_itens, c_falhas = collector()
        itens.extend(c_itens)
        falhas.update(c_falhas)

    return itens, falhas

# =========================================================
# DETECTION
# =========================================================

def _norm(texto: str) -> str:
    return build_short_title(texto, "", 220).lower()

def _detect_program(texto: str, program_hint: str | None = None) -> str:
    if program_hint:
        return program_hint
    t = _norm(texto)
    if "smiles" in t:
        return "Smiles"
    if "latam pass" in t or re.search(r"\blatam\b", t):
        return "LATAM Pass"
    if "azul fidelidade" in t or "tudoazul" in t or "clube azul" in t:
        return "TudoAzul"
    if "livelo" in t:
        return "Livelo"
    if "esfera" in t:
        return "Esfera"
    if "all accor" in t or re.search(r"\baccor\b", t):
        return "ALL Accor"
    if "krisflyer" in t:
        return "KrisFlyer"
    if "iberia" in t or "avios" in t:
        return "Iberia"
    if "flying blue" in t:
        return "Flying Blue"
    if "british airways" in t or "avios" in t:
        return "British Airways"
    if "tap" in t:
        return "TAP"
    if "amex" in t or "american express" in t:
        return "Amex"
    if "maxmilhas" in t or "milheiro" in t or "hotmilhas" in t:
        return "Mercado de Milhas"
    return "Programa nÃ£o identificado"

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
    # fallback broad
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

def _build_id(titulo: str, link: str, tipo: str) -> str:
    base = f"{tipo}|{build_short_title(titulo, '', 220)}|{str(link or '').strip()}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()

def transformar_em_promocoes(itens: list) -> list:
    promocoes = []
    for item in itens:
        titulo_bruto = item.get("title", "")
        summary = item.get("summary", "")
        link = item.get("link", "")
        type_hint = item.get("type_hint")
        program_hint = item.get("program_hint")

        texto_base = f"{titulo_bruto} {summary}".strip()
        tipo = _detect_type(texto_base, type_hint=type_hint)
        if not tipo:
            continue

        titulo_curto = build_short_title(titulo_bruto, summary, max_len=125)
        if not titulo_curto:
            continue

        program = _detect_program(texto_base, program_hint=program_hint)

        if tipo == "passagens" and program == "Programa nÃ£o identificado":
            continue
        if tipo == "transferencias":
            if program == "Programa nÃ£o identificado":
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

        promo = {
            "id": _build_id(titulo_curto, link, tipo),
            "title": titulo_curto,
            "link": link,
            "type": tipo,
            "program": program,
            "score": round(score, 1),
            "classification": _classificacao(score),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fontes_confirmadas": 1,
            "bonus_detectado": bonus,
            "milheiro_detectado": milheiro,
            "sweet_spot": sweet_spot,
            "alert_priority": prioridade,
            "ranking_score": ranking_score,
            "source_kind": item.get("source_kind", "rss"),
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

    def persistir(self):
        salvar_promocoes(self.promocoes)
        salvar_metricas(self.metricas)

STATE = RadarState()

def executar_varredura():
    itens, falhas = coletar_todas_fontes()

    fontes_monitoradas = len(FONTES_RSS) + len(FONTES_OFICIAIS) + len(SITEMAP_SOURCES) + len(PUBLIC_MILEAGE_SOURCES)
    fontes_com_erro = len(falhas)
    fontes_ativas = max(fontes_monitoradas - fontes_com_erro, 0)

    STATE.metricas["fontes_monitoradas"] = fontes_monitoradas
    STATE.metricas["fontes_ativas"] = fontes_ativas
    STATE.metricas["fontes_com_erro"] = fontes_com_erro
    STATE.metricas["falhas_fontes"] = falhas

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
    STATE.promocoes = historico[-1200:] if len(historico) > 1200 else historico
    STATE.metricas["alertas_criticos"] = criticos
    STATE.persistir()

    return {"novas": novas, "detectadas": len(promocoes_detectadas)}

def get_state_snapshot():
    STATE.promocoes = carregar_promocoes()
    STATE.metricas = carregar_metricas()
    return {"promocoes": STATE.promocoes, "metricas": STATE.metricas}

def get_promocoes_por_tipo(tipo: str, limit: int = 5) -> list:
    snapshot = get_state_snapshot()
    promos = [p for p in snapshot["promocoes"] if p.get("type") == tipo]
    promos = sorted(promos, key=lambda p: (p.get("ranking_score", 0), p.get("score", 0)), reverse=True)
    return promos[:limit]

def get_ranking(limit: int = 5) -> list:
    snapshot = get_state_snapshot()
    promos = sorted(
        snapshot["promocoes"],
        key=lambda p: (p.get("ranking_score", 0), p.get("score", 0)),
        reverse=True,
    )
    return promos[:limit]

# =========================================================
# TELEGRAM TEXT
# =========================================================

def build_status_text(interval_seconds: int) -> str:
    snapshot = get_state_snapshot()
    promocoes = snapshot["promocoes"]
    metricas = snapshot["metricas"]
    return (
        "ð¢ Radar online\n\n"
        f"â± Intervalo do radar: {interval_seconds} segundos\n"
        f"ð¥ PromoÃ§Ãµes detectadas: {len(promocoes)}\n"
        f"ð° Fontes monitoradas: {metricas.get('fontes_monitoradas', 0)}\n"
        f"â Fontes ativas: {metricas.get('fontes_ativas', 0)}\n"
        f"â Fontes com erro: {metricas.get('fontes_com_erro', 0)}\n"
        f"ð¨ Alertas crÃ­ticos no Ãºltimo ciclo: {metricas.get('alertas_criticos', 0)}\n\n"
        "Detectores ativos:\n"
        "â blogs\n"
        "â programas oficiais\n"
        "â sitemap e pÃ¡ginas internas\n"
        "â transferÃªncias\n"
        "â milheiro barato\n"
        "â passagens baratas\n"
        "â score automÃ¡tico\n"
        "â envio no canal\n\n"
        f"ð¤ Ãltimos alertas enviados: {metricas.get('ultimos_alertas_enviados', 0)}\n"
        f"ð Ãltima execuÃ§Ã£o: {metricas.get('ultima_execucao') or 'ainda nÃ£o executado'}\n"
        f"â ï¸ Ãltimo erro: {metricas.get('ultimo_erro', 'nenhum')}"
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

        STATE.metricas["ultimos_alertas_enviados"] = len(novas)
        STATE.metricas["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.metricas["ultimo_erro"] = "nenhum"
        STATE.persistir()

        return {"detectadas": detectadas, "novas": len(novas)}

async def _scheduled_scan():
    try:
        await _run_scan()
    except Exception as e:
        STATE.metricas["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.metricas["ultimo_erro"] = str(e)
        STATE.persistir()

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
    promos = [p for p in promos if p.get("program") != "Programa nÃ£o identificado"]
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
        await update.message.reply_text("ð Ranking promoÃ§Ãµes\n\nNenhuma promoÃ§Ã£o registrada ainda.", disable_web_page_preview=True)
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
        await update.message.reply_text("â³ JÃ¡ existe uma varredura em andamento. Aguarde terminar.", disable_web_page_preview=True)
        return
    await update.message.reply_text("ð§ª Teste manual do radar iniciado...", disable_web_page_preview=True)
    try:
        result = await _run_scan()
        await update.message.reply_text(
            "â Teste manual concluÃ­do.\n\n"
            f"Fontes monitoradas: {STATE.metricas.get('fontes_monitoradas', 0)}\n"
            f"Fontes ativas: {STATE.metricas.get('fontes_ativas', 0)}\n"
            f"Fontes com erro: {STATE.metricas.get('fontes_com_erro', 0)}\n"
            f"PromoÃ§Ãµes analisadas: {result.get('detectadas', 0)}\n"
            f"Novas promoÃ§Ãµes enviadas: {result.get('novas', 0)}\n"
            f"Alertas crÃ­ticos no Ãºltimo ciclo: {STATE.metricas.get('alertas_criticos', 0)}\n"
            f"Ãltimo erro: {STATE.metricas.get('ultimo_erro', 'nenhum')}",
            disable_web_page_preview=True,
        )
    except Exception as e:
        STATE.metricas["ultimo_erro"] = str(e)
        STATE.persistir()
        await update.message.reply_text(f"â Erro ao executar o radar: {e}", disable_web_page_preview=True)

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
