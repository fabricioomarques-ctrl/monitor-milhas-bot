import os
import re
import json
import time
import unicodedata
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ARQUIVO = "promocoes_enviadas.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
        "Mobile/15E148 Safari/604.1"
    )
}

RSS_FEEDS = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://pontospravoar.com/feed",
    "https://estevaopelomundo.com.br/feed",
]

PROGRAMAS_SITES = {
    "Livelo": "https://www.livelo.com.br/ofertas",
    "Smiles": "https://www.smiles.com.br/promocoes",
    "LATAM": "https://www.latampass.com/pt_br/promocoes",
    "TudoAzul": "https://tudoazul.voeazul.com.br/web/azul/promocoes",
}

FONTES_ANTECIPADAS = {
    "Livelo": "https://www.livelo.com.br/parceiros",
    "Smiles": "https://www.smiles.com.br/parceiros",
    "LATAM": "https://www.latampass.com/pt_br/parceiros",
    "TudoAzul": "https://tudoazul.voeazul.com.br/parceiros",
}

MILHEIRO_SITES = [
    "https://www.maxmilhas.com.br",
    "https://www.hotmilhas.com.br",
]

BONUS = ["100%", "95%", "90%", "85%", "80%", "70%", "60%", "50%"]

PALAVRAS_PROMO_REAL = [
    "transferencia bonificada",
    "transferência bonificada",
    "bonus de transferencia",
    "bônus de transferência",
    "ganhe ate",
    "ganhe até",
    "promocao valida",
    "promoção válida",
    "campanha valida",
    "campanha válida",
]

PALAVRAS_PROMO_GERAIS = [
    "bonus",
    "bônus",
    "transferencia",
    "transferência",
    "transferir",
    "campanha",
    "promocao",
    "promoção",
]

IGNORAR_TEXTO = [
    "shopping",
    "produto",
    "produtos",
    "loja",
    "lojas",
    "cupom",
    "aniversario",
    "aniversário",
    "pontos por real",
    "clube livelo",
    "cashback",
    "ofertas especiais",
]

ROTAS_GENERICAS = {
    "/",
    "/parceiros",
    "/promocoes",
    "/promoções",
    "/ofertas",
    "/shopping",
    "/home",
    "/transferir-pontos",
    "/transferir-pontos-cartao",
    "/pt_br/promocoes",
    "/pt_br/parceiros",
    "/web/azul/promocoes",
    "/web/azul/parceiros",
}

STOPWORDS = {
    "de", "da", "do", "das", "dos", "para", "com", "sem", "por", "em", "na", "no",
    "nas", "nos", "e", "ou", "um", "uma", "ate", "até", "mais", "menos", "seu",
    "sua", "suas", "seus", "valida", "válida", "campanha", "promocao", "promoção",
    "bonus", "bônus", "transferencia", "transferência", "transferir", "pontos",
    "milhas", "cartao", "cartão", "clube", "ganhe", "cliente", "clientes",
    "banco", "programa", "oferta", "ofertas", "especial", "especiais",
}

# -----------------------------
# HISTÓRICO / ESTADO
# -----------------------------

def estrutura_padrao():
    return {
        "sent": [],
        "signals": {},
    }


def carregar():
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Migração automática caso o arquivo antigo seja uma lista simples
        if isinstance(data, list):
            return {
                "sent": data,
                "signals": {},
            }

        if isinstance(data, dict):
            data.setdefault("sent", [])
            data.setdefault("signals", {})
            return data

        return estrutura_padrao()

    except Exception:
        return estrutura_padrao()


def salvar():
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


estado = carregar()
ranking = {}


# -----------------------------
# HELPERS
# -----------------------------

def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def limpar_espacos(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def extrair_bonus(texto: str) -> str:
    texto = normalizar(texto)
    achados = re.findall(r"\b(\d{2,3})\s*%", texto)
    if not achados:
        return ""
    # Pega o maior percentual encontrado
    maior = max(int(x) for x in achados)
    return f"{maior}%"


def url_absoluta(base: str, href: str) -> str:
    if not href:
        return ""
    return urljoin(base, href)


def link_generico(link: str) -> bool:
    if not link:
        return True

    parsed = urlparse(link)
    path = (parsed.path or "/").strip().lower()

    if path in ROTAS_GENERICAS:
        return True

    partes = [p for p in path.split("/") if p]

    # Rotas muito curtas costumam ser páginas fixas
    if len(partes) <= 1 and path not in {"/transferencia-bonus", "/bonus-transferencia"}:
        return True

    termos_genericos = [
        "parceiros",
        "promocoes",
        "promoções",
        "ofertas",
        "shopping",
        "home",
    ]
    if any(t in path for t in termos_genericos):
        return True

    return False


def texto_ruim(texto: str) -> bool:
    txt = normalizar(texto)
    return any(p in txt for p in IGNORAR_TEXTO)


def tem_sinal_promocional(texto: str
