import os
import re
import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Any

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
ADMIN_IDS = [
    int(x.strip())
    for x in _admin_raw.split(",")
    if x.strip().isdigit()
]

RADAR_INTERVAL_SECONDS = int(os.getenv("RADAR_INTERVAL_SECONDS", "3600"))
JANELA_REPETICAO_HORAS = int(os.getenv("JANELA_REPETICAO_HORAS", "24"))

PROMOCOES_FILE = "promocoes_enviadas.json"
METRICS_FILE = "dashboard_metrics.json"

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
MAX_RANKING = int(os.getenv("MAX_RANKING", "10"))

if not TELEGRAM_TOKEN:
    raise RuntimeError("Variável TELEGRAM_TOKEN não configurada.")

if not CANAL_ID:
    raise RuntimeError("Variável CANAL_ID não configurada.")

# =========================================================
# FONTES RSS
# =========================================================

FONTES_RSS = [
    "https://passageirodeprimeira.com/feed",
    "https://pontospravoar.com/feed",
    "https://www.melhoresdestinos.com.br/feed",
    "https://aeroin.net/feed",
]

# =========================================================
# FONTES OFICIAIS ESTÁVEIS
# =========================================================

FONTES_OFICIAIS = [
    # Smiles
    {"program": "Smiles", "type_hint": "milheiro", "url": "https://www.smiles.com.br/home"},
    {"program": "Smiles", "type_hint": "milheiro", "url": "https://www.smiles.com.br/clube-smiles"},
    {"program": "Smiles", "type_hint": "transferencias", "url": "https://www.smiles.com.br/promocoes"},

    # LATAM Pass
    {"program": "LATAM Pass", "type_hint": "passagens", "url": "https://latampass.latam.com/"},
    {"program": "LATAM Pass", "type_hint": "milheiro", "url": "https://latampass.latam.com/pt_br/comprar-milhas.html"},

    # TudoAzul
    {"program": "TudoAzul", "type_hint": "passagens", "url": "https://www.voeazul.com.br/br/pt/ofertas"},
    {"program": "TudoAzul", "type_hint": "milheiro", "url": "https://www.voeazul.com.br/br/pt/programa-fidelidade/clube-azul"},

    # Livelo
    {"program": "Livelo", "type_hint": "transferencias", "url": "https://www.livelo.com.br/"},
    {"program": "Livelo", "type_hint": "milheiro", "url": "https://www.livelo.com.br/clube"},

    # Esfera
    {"program": "Esfera", "type_hint": "transferencias", "url": "https://www.esfera.com.vc/"},
    {"program": "Esfera", "type_hint": "milheiro", "url": "https://www.esfera.com.vc/clube"},

    # ALL Accor
    {"program": "ALL Accor", "type_hint": "transferencias", "url": "https://all.accor.com/loyalty-program/index.pt.shtml"},

    # Iberia
    {"program": "Iberia", "type_hint": "passagens", "url": "https://www.iberia.com/br/ofertas/"},
]

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
        },
    )
    return data if isinstance(data, dict) else {}


def salvar_metricas(metricas: dict) -> None:
    if not isinstance(metricas, dict):
        metricas = {}
    _save_json(METRICS_FILE, metricas)

# =========================================================
# DEDUPLICADOR
# =========================================================

def _parse_data(valor):
    if not valor:
        return None

    if isinstance(valor, datetime):
        return valor

    formatos = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formatos:
        try:
            return datetime.strptime(str(valor), fmt)
        except Exception:
            continue

    return None


def _norm_assinatura(texto):
    return " ".join(str(texto or "").lower().strip().split())


def _assinatura(promo: dict) -> str:
    return "|".join(
        [
            _norm_assinatura(promo.get("type")),
            _norm_assinatura(promo.get("program")),
            _norm_assinatura(promo.get("title")),
            _norm_assinatura(promo.get("link")),
        ]
    )


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
# COLETA
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    )
}


def _extrair_texto_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    partes = []

    if soup.title and soup.title.get_text(strip=True):
        partes.append(soup.title.get_text(" ", strip=True))

    for tag in soup.find_all(["h1", "h2", "h3"]):
        txt = tag.get_text(" ", strip=True)
        if txt:
            partes.append(txt)

    for tag in soup.find_all(["p", "span", "div"]):
        txt = tag.get_text(" ", strip=True)
        if txt and len(txt) > 20:
            partes.append(txt)
        if len(" ".join(partes)) > 2500:
            break

    texto = " ".join(partes)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:3000]


def coletar_rss():
    itens = []
    falhas = {}

    for url in FONTES_RSS:
        try:
            feed = feedparser.parse(url)
            entries = getattr(feed, "entries", [])
            for entry in entries[:20]:
                itens.append(
                    {
                        "title": entry.get("title", "") or "",
                        "link": entry.get("link", "") or "",
                        "summary": entry.get("summary", "") or "",
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
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            texto = _extrair_texto_html(resp.text)

            itens.append(
                {
                    "title": texto,
                    "link": url,
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


def coletar_todas_fontes():
    itens_rss, falhas_rss = coletar_rss()
    itens_oficiais, falhas_oficiais = coletar_paginas_oficiais()

    itens = itens_rss + itens_oficiais
    falhas = {}
    falhas.update(falhas_rss)
    falhas.update(falhas_oficiais)

    return itens, falhas

# =========================================================
# DETECÇÃO / SCORE
# =========================================================

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
    "iberia",
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
    if "tap" in t:
        return "TAP"
    if "amex" in t or "american express" in t:
        return "Amex"
    if "maxmilhas" in t or "milheiro" in t:
        return "Mercado de Milhas"

    return "Programa não identificado"


def _detectar_bonus_alto(texto: str) -> int:
    t = _norm(texto)
    achados = re.findall(r"(\d{2,3})\s*%", t)
    bonus = [int(x) for x in achados if x.isdigit()]
    return max(bonus) if bonus else 0


def _detect_type(texto: str, type_hint: str | None = None):
    t = _norm(texto)

    if _has_any(t, RUIDO):
        return None

    hinted = type_hint if type_hint in {"milheiro", "transferencias", "passagens"} else None

    if "milheiro" in t or "maxmilhas" in t:
        return "milheiro"

    if "compra de pontos" in t or "compra milhas" in t or "comprar milhas" in t:
        return "milheiro"

    if (
        ("transfer" in t or "bônus" in t or "bonus" in t or "bonificada" in t)
        and (_has_any(t, BANCOS) or _has_any(t, PROGRAMAS))
    ):
        return "transferencias"

    if (
        ("milhas" in t or "pontos" in t or "avios" in t)
        and (
            "passagens" in t
            or "passagem" in t
            or "trechos" in t
            or "voos" in t
            or "resgate" in t
            or "ida e volta" in t
            or "o trecho" in t
            or "voos baratos" in t
            or "ofertas" in t
        )
        and _has_any(t, PROGRAMAS)
    ):
        return "passagens"

    return hinted


def _score_transferencias(texto: str) -> float:
    bonus = _detectar_bonus_alto(texto)

    if bonus >= 120:
        return 9.8
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
        summary = item.get("summary", "")
        texto_base = f"{titulo_bruto} {summary}"
        link = item.get("link", "")
        type_hint = item.get("type_hint")
        program_hint = item.get("program_hint")

        titulo = limpar_titulo(texto_base)
        tipo = _detect_type(titulo, type_hint=type_hint)

        if not tipo:
            continue

        program = _detect_program(titulo, program_hint=program_hint)

        if tipo == "passagens" and program == "Programa não identificado":
            continue

        if tipo == "transferencias":
            score = _score_transferencias(titulo)
        elif tipo == "milheiro":
            score = _score_milheiro(titulo)
        else:
            score = _score_passagens(titulo)

        bonus_detectado = _detectar_bonus_alto(titulo)

        promo = {
            "id": _build_id(titulo, link, tipo),
            "title": titulo[:500],
            "link": link,
            "type": tipo,
            "program": program,
            "score": round(score, 1),
            "classification": _classificacao(score),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fontes_confirmadas": 1,
            "bonus_detectado": bonus_detectado,
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

    def persistir(self):
        salvar_promocoes(self.promocoes)
        salvar_metricas(self.metricas)


STATE = RadarState()


def executar_varredura():
    itens, falhas = coletar_todas_fontes()

    fontes_monitoradas = len(FONTES_RSS) + len(FONTES_OFICIAIS)
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
    for promo in promocoes_detectadas:
        if promo.get("id") not in ids_existentes:
            novas.append(promo)
            historico.append(promo)

    historico = deduplicar(historico)
    STATE.promocoes = historico[-800:] if len(historico) > 800 else historico
    STATE.persistir()

    return {
        "novas": novas,
        "detectadas": len(promocoes_detectadas),
    }


def get_state_snapshot():
    STATE.promocoes = carregar_promocoes()
    STATE.metricas = carregar_metricas()

    return {
        "promocoes": STATE.promocoes,
        "metricas": STATE.metricas,
    }


def get_promocoes_por_tipo(tipo: str, limit: int = 5) -> list:
    snapshot = get_state_snapshot()
    promos = [p for p in snapshot["promocoes"] if p.get("type") == tipo]
    promos = sorted(promos, key=lambda p: p.get("score", 0), reverse=True)
    return promos[:limit]


def get_ranking(limit: int = 5) -> list:
    snapshot = get_state_snapshot()
    promos = sorted(snapshot["promocoes"], key=lambda p: p.get("score", 0), reverse=True)
    return promos[:limit]

# =========================================================
# DASHBOARD / STATUS
# =========================================================

def build_status_text(interval_seconds: int) -> str:
    snapshot = get_state_snapshot()
    promocoes = snapshot["promocoes"]
    metricas = snapshot["metricas"]

    return (
        "🟢 Radar online\n\n"
        f"⏱ Intervalo do radar: {interval_seconds} segundos\n"
        f"📥 Promoções detectadas: {len(promocoes)}\n"
        f"🛰 Fontes monitoradas: {metricas.get('fontes_monitoradas', 0)}\n"
        f"✅ Fontes ativas: {metricas.get('fontes_ativas', 0)}\n"
        f"❌ Fontes com erro: {metricas.get('fontes_com_erro', 0)}\n\n"
        "Detectores ativos:\n"
        "✓ blogs\n"
        "✓ programas oficiais\n"
        "✓ transferências\n"
        "✓ milheiro\n"
        "✓ score automático\n"
        "✓ envio no canal\n\n"
        f"📤 Últimos alertas enviados: {metricas.get('ultimos_alertas_enviados', 0)}\n"
        f"🕒 Última execução: {metricas.get('ultima_execucao') or 'ainda não executado'}\n"
        f"⚠️ Último erro: {metricas.get('ultimo_erro', 'nenhum')}"
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

# =========================================================
# BOT TELEGRAM
# =========================================================

SCAN_LOCK = asyncio.Lock()
_APP = None


def is_admin(update: Update) -> bool:
    if not ADMIN_IDS:
        return True
    if not update.effective_chat:
        return False
    return update.effective_chat.id in ADMIN_IDS


def format_card(promo: dict) -> str:
    texto = "💰 PROMOÇÃO CONFIRMADA\n\n"
    texto += f"Programa: {promo.get('program', 'Programa não identificado')}\n"
    texto += f"Título: {promo.get('title', '')}\n"
    if promo.get("bonus_detectado", 0):
        texto += f"Bônus detectado: {promo.get('bonus_detectado')}%\n"
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
        partes.append(f"Score: {promo.get('score', 0)}")
        partes.append(f"{promo.get('classification', '🟢 PROMOÇÃO BOA')}")
        partes.append("Link:")
        partes.append(str(promo.get("link", "")))
    partes.append("━━━━━━━━━━━━━━")
    return "\n".join(partes)


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

        return {
            "detectadas": detectadas,
            "novas": len(novas),
        }


async def _scheduled_scan():
    try:
        await _run_scan()
    except Exception as e:
        STATE.metricas["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE.metricas["ultimo_erro"] = str(e)
        STATE.persistir()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✈️ Radar de Milhas PRO MAX\n\n"
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
    await update.message.reply_text(
        build_status_text(RADAR_INTERVAL_SECONDS),
        disable_web_page_preview=True,
    )


async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Comando disponível apenas para o administrador.")
        return

    await update.message.reply_text(build_debug_text(), disable_web_page_preview=True)


async def cmd_promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_ranking(limit=5)
    await update.message.reply_text(
        format_lista("🔥 Últimas promoções", promos),
        disable_web_page_preview=True,
    )


async def cmd_transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_promocoes_por_tipo("transferencias", limit=5)
    if not promos:
        texto = (
            "💳 Promoções de transferências de pontos monitoradas\n\n"
            "Nenhuma transferência promocional ativa detectada no momento."
        )
    else:
        texto = format_lista("💳 Promoções de transferências de pontos monitoradas", promos)

    await update.message.reply_text(texto, disable_web_page_preview=True)


async def cmd_passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_promocoes_por_tipo("passagens", limit=5)
    await update.message.reply_text(
        format_lista("✈️ Últimos alertas de passagens", promos),
        disable_web_page_preview=True,
    )


async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = get_ranking(limit=MAX_RANKING if MAX_RANKING < 6 else 5)

    if not promos:
        await update.message.reply_text(
            "🏆 Ranking promoções\n\nNenhuma promoção registrada ainda.",
            disable_web_page_preview=True,
        )
        return

    linhas = ["🏆 Ranking promoções", ""]
    medalhas = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣"}

    for i, promo in enumerate(promos, start=1):
        prefixo = medalhas.get(i, f"{i}.")
        linhas.append(
            f"{prefixo} {promo.get('program', 'Programa não identificado')} | "
            f"{promo.get('title', '')} | score {promo.get('score', 0)}"
        )

    await update.message.reply_text("\n".join(linhas), disable_web_page_preview=True)


async def cmd_testeradar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Comando disponível apenas para o administrador.")
        return

    if SCAN_LOCK.locked():
        await update.message.reply_text(
            "⏳ Já existe uma varredura em andamento. Aguarde terminar.",
            disable_web_page_preview=True,
        )
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
            f"Último erro: {STATE.metricas.get('ultimo_erro', 'nenhum')}",
            disable_web_page_preview=True,
        )
    except Exception as e:
        STATE.metricas["ultimo_erro"] = str(e)
        STATE.persistir()
        await update.message.reply_text(
            f"❌ Erro ao executar o radar: {e}",
            disable_web_page_preview=True,
        )


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
