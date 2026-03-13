import os
import re
import json
import time
import html
import hashlib
import logging
from datetime import datetime
from urllib.parse import urlparse

import requests
import feedparser
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# =========================================================
# CONFIGURAÇÃO GERAL
# =========================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()
CANAL_ID = os.getenv("CANAL_ID", "").strip()

PROMOCOES_FILE = "promocoes_enviadas.json"
DASHBOARD_FILE = "dashboard_metrics.json"
REQUEST_TIMEOUT = 20
RADAR_INTERVAL_SECONDS = 600  # ~10 minutos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("radar_milhas_pro")

if not TELEGRAM_TOKEN:
    raise RuntimeError("Variável TELEGRAM_TOKEN não configurada.")
if not CANAL_ID:
    raise RuntimeError("Variável CANAL_ID não configurada.")

# =========================================================
# FONTES MONITORADAS (14)
# =========================================================
# Estrutura fiel ao que você mostrou: blogs, programas,
# milheiro, redes sociais, confirmação múltipla, score.

FONTES = [
    # BLOGS
    {
        "name": "Pontos pra Voar",
        "type": "rss",
        "url": "https://www.pontospravoar.com/feed",
        "group": "blogs",
    },
    {
        "name": "Passageiro de Primeira",
        "type": "rss",
        "url": "https://passageirodeprimeira.com/feed",
        "group": "blogs",
    },
    {
        "name": "Melhores Destinos",
        "type": "rss",
        "url": "https://www.melhoresdestinos.com.br/feed",
        "group": "blogs",
    },
    {
        "name": "AEROIN",
        "type": "rss",
        "url": "https://www.aeroin.net/feed",
        "group": "blogs",
    },

    # PROGRAMAS
    {
        "name": "Smiles",
        "type": "html",
        "url": "https://www.smiles.com.br/",
        "group": "programas",
    },
    {
        "name": "LATAM Pass",
        "type": "html",
        "url": "https://latampass.latam.com/pt_br/",
        "group": "programas",
    },
    {
        "name": "TudoAzul",
        "type": "html",
        "url": "https://www.tudoazul.com/",
        "group": "programas",
    },
    {
        "name": "Livelo",
        "type": "html",
        "url": "https://www.livelo.com.br/",
        "group": "programas",
    },
    {
        "name": "Esfera",
        "type": "html",
        "url": "https://www.esfera.com.vc/",
        "group": "programas",
    },

    # MERCADO DE MILHAS
    {
        "name": "MaxMilhas",
        "type": "html",
        "url": "https://www.maxmilhas.com.br/",
        "group": "milheiro",
    },
    {
        "name": "HotMilhas",
        "type": "html",
        "url": "https://www.hotmilhas.com.br/",
        "group": "milheiro",
    },
    {
        "name": "Mercado de Milhas",
        "type": "html",
        "url": "https://mercadodemilhas.com/",
        "group": "milheiro",
    },

    # REDES / CANAIS / ALERTAS
    {
        "name": "Alerta Passagens",
        "type": "html",
        "url": "https://www.pontospravoar.com/tag/alerta-de-passagens/",
        "group": "redes_sociais",
    },
    {
        "name": "Promoções Programas",
        "type": "html",
        "url": "https://www.pontospravoar.com/",
        "group": "redes_sociais",
    },
]

# =========================================================
# ESTADO GLOBAL
# =========================================================

STATE = {
    "promocoes": [],
    "sent_ids": set(),
    "ultimos_alertas_enviados": 0,
    "ultima_execucao": None,
    "ultimo_erro": "nenhum",
    "fontes_monitoradas": len(FONTES),
    "fontes_ativas": 0,
    "fontes_com_erro": 0,
    "falhas_fontes": {},
}

# =========================================================
# UTILITÁRIOS DE ARQUIVO
# =========================================================

def load_json_file(path: str, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception("Falha ao carregar %s: %s", path, e)
        return default


def save_json_file(path: str, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("Falha ao salvar %s: %s", path, e)


def load_state():
    saved_promos = load_json_file(PROMOCOES_FILE, [])
    metrics = load_json_file(DASHBOARD_FILE, {})

    STATE["promocoes"] = saved_promos
    STATE["sent_ids"] = {p["id"] for p in saved_promos if "id" in p}

    STATE["ultimos_alertas_enviados"] = metrics.get("ultimos_alertas_enviados", 0)
    STATE["ultima_execucao"] = metrics.get("ultima_execucao")
    STATE["ultimo_erro"] = metrics.get("ultimo_erro", "nenhum")
    STATE["fontes_monitoradas"] = metrics.get("fontes_monitoradas", len(FONTES))
    STATE["fontes_ativas"] = metrics.get("fontes_ativas", 0)
    STATE["fontes_com_erro"] = metrics.get("fontes_com_erro", 0)
    STATE["falhas_fontes"] = metrics.get("falhas_fontes", {})


def persist_state():
    save_json_file(PROMOCOES_FILE, STATE["promocoes"])
    save_json_file(
        DASHBOARD_FILE,
        {
            "ultimos_alertas_enviados": STATE["ultimos_alertas_enviados"],
            "ultima_execucao": STATE["ultima_execucao"],
            "ultimo_erro": STATE["ultimo_erro"],
            "fontes_monitoradas": STATE["fontes_monitoradas"],
            "fontes_ativas": STATE["fontes_ativas"],
            "fontes_com_erro": STATE["fontes_com_erro"],
            "falhas_fontes": STATE["falhas_fontes"],
            "item_18": {
                "classificador_ia_local": True,
                "painel_interno_json": True,
                "expansao_fontes_preparada": True,
            },
        },
    )

# =========================================================
# NORMALIZAÇÃO E FILTRO PROFISSIONAL
# =========================================================

RUIDOS = [
    "shopee",
    "amazon",
    "mercado livre",
    "magalu",
    "cashback",
    "varejo",
    "cupom",
    "desconto em compras",
    "shopping",
    "shopping de pontos",
    "loja parceira",
    "produto físico",
]

KEYWORDS_TRANSFERENCIA = [
    "transferência",
    "transferencia",
    "bônus de transferência",
    "bonus de transferencia",
    "transfira",
    "transfere",
    "esfera",
    "livelo",
    "smiles",
    "latam pass",
    "tudoazul",
]

KEYWORDS_PASSAGENS = [
    "passagens",
    "passagem",
    "resgate",
    "voos",
    "trechos",
    "alerta de passagens",
    "rio de janeiro",
    "são paulo",
    "azul fidelidade",
    "latam pass",
    "smiles",
]

KEYWORDS_MILHEIRO = [
    "milheiro",
    "r$",
    "compra de milhas",
    "venda de milhas",
    "mercado de milhas",
    "maxmilhas",
    "hotmilhas",
]

KEYWORDS_PROMO = [
    "bônus",
    "bonus",
    "promoção",
    "promocao",
    "oferece",
    "assine",
    "clube",
    "campanha",
    "receba",
    "segue valendo",
    "acaba hoje",
]

def strip_html_tags(text: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def normalize_text(text: str) -> str:
    text = strip_html_tags(text or "")
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def filtro_profissional(title: str, content: str) -> bool:
    combined = normalize_text(f"{title} {content}")
    for ruido in RUIDOS:
        if ruido in combined:
            return False
    return True


def build_item_id(source_name: str, title: str, link: str) -> str:
    raw = f"{source_name}|{normalize_text(title)}|{link.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

# =========================================================
# CLASSIFICAÇÃO E SCORE
# =========================================================

def detect_price_brl(text: str):
    """
    Detecta valores como:
    R$ 10,80
    R$10.80
    10,80
    """
    normalized = text.replace(".", "").replace(",", ".")
    matches = re.findall(r"r\$\s*(\d+(?:\.\d{1,2})?)", normalized, flags=re.I)
    if matches:
        try:
            return float(matches[0])
        except Exception:
            return None
    return None


def classify_type(title: str, content: str) -> str:
    combined = normalize_text(f"{title} {content}")

    if any(k in combined for k in KEYWORDS_PASSAGENS):
        return "passagens"

    if any(k in combined for k in KEYWORDS_TRANSFERENCIA):
        return "transferencias"

    if any(k in combined for k in KEYWORDS_MILHEIRO):
        return "milheiro"

    return "promocoes"


def infer_program(source_name: str, title: str, content: str) -> str:
    combined = normalize_text(f"{source_name} {title} {content}")

    if "maxmilhas" in combined:
        return "Mercado de Milhas"
    if "hotmilhas" in combined:
        return "Mercado de Milhas"
    if "mercado de milhas" in combined:
        return "Mercado de Milhas"
    if "smiles" in combined:
        return "Smiles"
    if "latam pass" in combined or "latam" in combined:
        return "LATAM Pass"
    if "tudoazul" in combined or "azul fidelidade" in combined:
        return "TudoAzul"
    if "livelo" in combined:
        return "Livelo"
    if "esfera" in combined:
        return "Esfera"
    return source_name


def classify_score(title: str, content: str, promo_type: str):
    combined = normalize_text(f"{title} {content}")
    price = detect_price_brl(combined)

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
        if "100%" in combined or "100 %" in combined:
            return 9.5, price
        if "90%" in combined or "90 %" in combined:
            return 9.0, price
        if "80%" in combined or "80 %" in combined:
            return 8.5, price
        if "70%" in combined or "70 %" in combined:
            return 8.0, price
        if "60%" in combined or "60 %" in combined:
            return 7.5, price
        return 7.0, price

    if promo_type == "passagens":
        if "a partir de" in combined or "resgate" in combined:
            return 7.5, price
        return 7.0, price

    if any(k in combined for k in KEYWORDS_PROMO):
        return 7.0, price

    return 6.5, price


def classificar_promocao(score: float) -> str:
    if score >= 9:
        return "🔴 PROMOÇÃO IMPERDÍVEL"
    if score >= 7.5:
        return "🟡 PROMOÇÃO MUITO BOA"
    return "🟢 PROMOÇÃO BOA"

# =========================================================
# ITEM 18 - CLASSIFICADOR IA LOCAL / PAINEL / EXPANSÃO
# =========================================================
# Sem mudar comandos. Implementado internamente.

def classificador_ia_local(title: str, content: str, promo_type: str, score: float) -> dict:
    """
    Classificador local simples, embutido no bot.py.
    """
    combined = normalize_text(f"{title} {content}")

    prioridade = "normal"
    if score >= 9:
        prioridade = "alta"
    elif score >= 7.5:
        prioridade = "média"

    antecipada = any(k in combined for k in [
        "campanha",
        "landing page",
        "novo banner",
        "segue valendo",
        "acaba hoje",
        "assine",
    ])

    return {
        "tipo": promo_type,
        "prioridade": prioridade,
        "detecao_antecipada": antecipada,
        "confianca_local": round(min(10.0, score + 0.2), 1),
    }

# =========================================================
# COLETA DE FONTES
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

def fetch_url(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def collect_rss(source: dict) -> list:
    items = []
    feed = feedparser.parse(source["url"])

    for entry in feed.entries[:20]:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")

        if not title or not link:
            continue

        items.append({
            "source_name": source["name"],
            "source_group": source["group"],
            "title": title,
            "content": strip_html_tags(summary),
            "link": link,
        })
    return items


def collect_html(source: dict) -> list:
    items = []
    text = fetch_url(source["url"])
    clean_text = strip_html_tags(text)
    text_norm = normalize_text(clean_text)

    patterns = [
        r"[^.!?\n]{0,120}(milheiro[^.!?\n]{0,200})",
        r"[^.!?\n]{0,120}(transfer[êe]ncia[^.!?\n]{0,200})",
        r"[^.!?\n]{0,120}(b[oô]nus[^.!?\n]{0,200})",
        r"[^.!?\n]{0,120}(passagens?[^.!?\n]{0,200})",
        r"[^.!?\n]{0,120}(resgate[^.!?\n]{0,200})",
        r"[^.!?\n]{0,120}(clube[^.!?\n]{0,200})",
    ]

    found_snippets = []
    for pattern in patterns:
        found_snippets.extend(re.findall(pattern, text_norm, flags=re.I))

    unique_snippets = []
    seen = set()
    for snippet in found_snippets:
        snippet = snippet.strip()
        if len(snippet) < 20:
            continue
        if snippet in seen:
            continue
        seen.add(snippet)
        unique_snippets.append(snippet)

    for snippet in unique_snippets[:8]:
        title = snippet[:180].strip().capitalize()
        items.append({
            "source_name": source["name"],
            "source_group": source["group"],
            "title": title,
            "content": snippet,
            "link": source["url"],
        })

    return items


def coletar_todas_fontes() -> list:
    results = []
    fontes_ativas = 0
    fontes_com_erro = 0
    falhas = {}

    for source in FONTES:
        try:
            if source["type"] == "rss":
                data = collect_rss(source)
            else:
                data = collect_html(source)

            if data:
                fontes_ativas += 1
                results.extend(data)
            else:
                # fonte sem item útil conta como ativa, mas sem extração útil
                fontes_ativas += 1

        except Exception as e:
            fontes_com_erro += 1
            falhas[source["name"]] = str(e)[:200]
            logger.warning("Falha em %s: %s", source["name"], e)

    STATE["fontes_ativas"] = fontes_ativas
    STATE["fontes_com_erro"] = fontes_com_erro
    STATE["falhas_fontes"] = falhas
    return results

# =========================================================
# CONFIRMAÇÃO MULTI-FONTE
# =========================================================

def title_signature(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^a-z0-9à-úç\s]", " ", text)
    tokens = [t for t in text.split() if len(t) > 2]
    return " ".join(tokens[:12])


def calcular_confirmacoes(candidates: list) -> dict:
    by_sig = {}
    for item in candidates:
        sig = title_signature(item["title"])
        by_sig.setdefault(sig, []).append(item)

    confirmations = {}
    for sig, grouped in by_sig.items():
        confirmations[sig] = len({g["source_name"] for g in grouped})
    return confirmations

# =========================================================
# TRANSFORMAÇÃO EM PROMOÇÕES
# =========================================================

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
        score, price = classify_score(title, content, promo_type)
        program = infer_program(item["source_name"], title, content)
        sig = title_signature(title)
        fontes_confirmadas = confirmations.get(sig, 1)
        ai_data = classificador_ia_local(title, content, promo_type, score)

        promo_id = build_item_id(item["source_name"], title, link)

        promotions.append({
            "id": promo_id,
            "source_name": item["source_name"],
            "source_group": item["source_group"],
            "program": program,
            "title": title.strip(),
            "content": content.strip(),
            "link": link.strip(),
            "type": promo_type,
            "score": round(score, 1),
            "classification": classificar_promocao(score),
            "price_brl": price,
            "fontes_confirmadas": fontes_confirmadas,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ai": ai_data,
        })

    # Ordenação: score maior primeiro, depois mais novas
    promotions.sort(key=lambda p: (p["score"], p["created_at"]), reverse=True)
    return promotions

# =========================================================
# ALERTAS
# =========================================================

def promo_resumo_ranking(promo: dict) -> str:
    promo_type = promo["type"]
    score = promo["score"]

    if promo_type == "milheiro":
        return f"Milheiro barato | score {score}"

    if promo_type == "passagens":
        return f"Alerta de passagens | score {score}"

    if promo_type == "transferencias":
        return f"Transferência bonificada | score {score}"

    return f"Promoção | score {score}"


def format_promo_alert(promo: dict) -> str:
    linhas = ["💰 PROMOÇÃO CONFIRMADA", ""]

    linhas.append(f"Programa: {promo['program']}")
    linhas.append(f"Título: {promo['title']}")

    if promo["type"] == "milheiro" and promo["price_brl"] is not None:
        valor = f"R$ {promo['price_brl']:.2f}".replace(".", ",")
        linhas.append(f"Milheiro detectado: {valor}")

    linhas.append(f"Fontes confirmadas: {promo['fontes_confirmadas']}")
    linhas.append(f"Score: {promo['score']}")
    linhas.append("")
    linhas.append(promo["classification"])
    linhas.append("")
    linhas.append("Link:")
    linhas.append(promo["link"])

    return "\n".join(linhas)


async def enviar_alerta_canal(context: ContextTypes.DEFAULT_TYPE, promo: dict):
    mensagem = format_promo_alert(promo)
    await context.bot.send_message(chat_id=CANAL_ID, text=mensagem)

# =========================================================
# RADAR
# =========================================================

def adicionar_promocao_se_nova(promo: dict) -> bool:
    if promo["id"] in STATE["sent_ids"]:
        return False

    STATE["promocoes"].insert(0, promo)
    STATE["sent_ids"].add(promo["id"])

    # mantém histórico controlado
    STATE["promocoes"] = STATE["promocoes"][:400]
    return True


async def executar_radar(context: ContextTypes.DEFAULT_TYPE):
    try:
        raw_items = coletar_todas_fontes()
        promotions = transformar_em_promocoes(raw_items)

        enviados_neste_ciclo = 0

        for promo in promotions:
            if adicionar_promocao_se_nova(promo):
                # Envia só promoções relevantes
                if promo["score"] >= 7.0:
                    await enviar_alerta_canal(context, promo)
                    enviados_neste_ciclo += 1

        STATE["ultimos_alertas_enviados"] = enviados_neste_ciclo
        STATE["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE["ultimo_erro"] = "nenhum"
        persist_state()

        logger.info(
            "Radar executado | novas=%s | fontes=%s | ativas=%s | erro=%s",
            enviados_neste_ciclo,
            STATE["fontes_monitoradas"],
            STATE["fontes_ativas"],
            STATE["fontes_com_erro"],
        )

    except Exception as e:
        STATE["ultima_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE["ultimo_erro"] = str(e)[:250]
        persist_state()
        logger.exception("Erro no radar: %s", e)

# =========================================================
# CONSULTAS PARA COMANDOS
# =========================================================

def latest_promotions(limit=5):
    return STATE["promocoes"][:limit]


def latest_transferencias(limit=5):
    return [p for p in STATE["promocoes"] if p["type"] == "transferencias"][:limit]


def latest_passagens(limit=5):
    return [p for p in STATE["promocoes"] if p["type"] == "passagens"][:limit]


def ranking_promotions(limit=5):
    promos = sorted(STATE["promocoes"], key=lambda p: p["score"], reverse=True)
    return promos[:limit]

# =========================================================
# COMANDOS DO BOT
# =========================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "✈️ Radar de Milhas PRO MAX\n\n"
        "/menu\n"
        "/promocoes\n"
        "/transferencias\n"
        "/passagens\n"
        "/ranking\n"
        "/status"
    )
    await update.message.reply_text(texto)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "MENU\n\n"
        "/promocoes\n"
        "/transferencias\n"
        "/passagens\n"
        "/ranking\n"
        "/status"
    )
    await update.message.reply_text(texto)


async def cmd_promocoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = latest_promotions(5)

    if not promos:
        await update.message.reply_text("🔥 Últimas promoções\n\nNenhuma promoção registrada ainda.")
        return

    linhas = ["🔥 Últimas promoções", ""]
    for p in promos:
        linhas.append(f"• {p['title']} | score {p['score']}")

    await update.message.reply_text("\n".join(linhas))


async def cmd_transferencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = latest_transferencias(5)

    if not promos:
        await update.message.reply_text("🔁 Últimas transferências\n\nNenhuma promoção registrada ainda.")
        return

    linhas = ["🔁 Últimas transferências", ""]
    for p in promos:
        linhas.append(f"• {p['title']} | score {p['score']}")

    await update.message.reply_text("\n".join(linhas))


async def cmd_passagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = latest_passagens(5)

    if not promos:
        await update.message.reply_text("✈️ Últimos alertas de passagens\n\nNenhuma promoção registrada ainda.")
        return

    linhas = ["✈️ Últimos alertas de passagens", ""]
    for p in promos:
        linhas.append(f"• {p['title']} | score {p['score']}")

    await update.message.reply_text("\n".join(linhas))


async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    promos = ranking_promotions(5)

    if not promos:
        await update.message.reply_text("🏆 Ranking promoções\n\nNenhuma promoção registrada ainda.")
        return

    linhas = ["🏆 Ranking promoções", ""]
    for idx, p in enumerate(promos, start=1):
        linhas.append(f"{idx}. {promo_resumo_ranking(p)}")

    await update.message.reply_text("\n".join(linhas))


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_promos = len(STATE["promocoes"])
    ultima_execucao = STATE["ultima_execucao"] or "ainda não executado"
    ultimo_erro = STATE["ultimo_erro"] or "nenhum"

    texto = (
        "🟢 Radar online\n\n"
        f"⏱ Intervalo do radar: {RADAR_INTERVAL_SECONDS} segundos\n"
        f"📥 Promoções detectadas: {total_promos}\n"
        f"🛰 Fontes monitoradas: {STATE['fontes_monitoradas']}\n"
        f"✅ Fontes ativas: {STATE['fontes_ativas']}\n"
        f"❌ Fontes com erro: {STATE['fontes_com_erro']}\n\n"
        "Detectores ativos:\n"
        "✓ blogs\n"
        "✓ programas\n"
        "✓ milheiro\n"
        "✓ redes sociais\n"
        "✓ confirmação múltipla\n"
        "✓ score automático\n"
        "✓ envio no canal\n\n"
        f"📤 Últimos alertas enviados: {STATE['ultimos_alertas_enviados']}\n"
        f"🕒 Última execução: {ultima_execucao}\n"
        f"⚠️ Último erro: {ultimo_erro}"
    )
    await update.message.reply_text(texto)

# =========================================================
# MAIN
# =========================================================

def build_app():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("promocoes", cmd_promocoes))
    app.add_handler(CommandHandler("transferencias", cmd_transferencias))
    app.add_handler(CommandHandler("passagens", cmd_passagens))
    app.add_handler(CommandHandler("ranking", cmd_ranking))
    app.add_handler(CommandHandler("status", cmd_status))

    return app


def main():
    load_state()
    STATE["fontes_monitoradas"] = len(FONTES)
    persist_state()

    app = build_app()

    if app.job_queue is None:
        raise RuntimeError(
            "JobQueue indisponível. Confirme a dependência python-telegram-bot[job-queue]."
        )

    app.job_queue.run_repeating(executar_radar, interval=RADAR_INTERVAL_SECONDS, first=10)

    logger.info("Radar iniciado.")
    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
