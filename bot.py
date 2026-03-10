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

# -----------------------------
# FONTES
# -----------------------------

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

# -----------------------------
# REGRAS
# -----------------------------

BONUS_REGEX = r"\b(50|60|70|80|85|90|95|100)\s*%\b"

PALAVRAS_PROMO_REAL = [
    "transferencia bonificada",
    "transferência bonificada",
    "bonus de transferencia",
    "bônus de transferência",
    "ganhe ate",
    "ganhe até",
    "campanha valida",
    "campanha válida",
    "promocao valida",
    "promoção válida",
    "válido até",
    "valido ate",
]

PALAVRAS_PROMO_GERAIS = [
    "bonus",
    "bônus",
    "campanha",
    "promocao",
    "promoção",
]

PALAVRAS_TRANSFERENCIA = [
    "transferencia",
    "transferência",
    "transferir pontos",
    "transferir",
]

TERMOS_IGNORAR_TEXTO = [
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
    "ofertas especiais",
    "cashback",
    "selecao nintendo",
    "seleção nintendo",
    "transferencia entre contas",
    "transferência entre contas",
]

ROTAS_BLOQUEADAS_EXATAS = {
    "/",
    "/parceiros",
    "/promocoes",
    "/promoções",
    "/ofertas",
    "/shopping",
    "/home",
    "/transferencia-entre-contas",
    "/transferir-pontos",
    "/transferir-pontos-cartao",
    "/pt_br/promocoes",
    "/pt_br/parceiros",
    "/web/azul/promocoes",
    "/web/azul/parceiros",
}

TERMOS_BLOQUEADOS_NO_PATH = [
    "parceiros",
    "promocoes",
    "promoções",
    "ofertas",
    "shopping",
    "transferencia-entre-contas",
    "transferir-pontos",
    "transferir-pontos-cartao",
]

STOPWORDS = {
    "de", "da", "do", "das", "dos", "para", "com", "sem", "por", "em", "na", "no",
    "nas", "nos", "e", "ou", "um", "uma", "mais", "menos", "seu", "sua", "suas",
    "seus", "campanha", "promocao", "promoção", "bonus", "bônus", "transferencia",
    "transferência", "transferir", "pontos", "milhas", "cartao", "cartão", "clube",
    "ganhe", "cliente", "clientes", "banco", "programa", "oferta", "ofertas",
    "especial", "especiais", "valida", "válida", "ate", "até",
}

TTL_SINAL = 12 * 60 * 60  # 12 horas

# -----------------------------
# ESTADO
# -----------------------------

def estado_padrao():
    return {
        "sent": [],
        "signals": {}
    }


def carregar():
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return {"sent": data, "signals": {}}

        if isinstance(data, dict):
            data.setdefault("sent", [])
            data.setdefault("signals", {})
            return data

        return estado_padrao()
    except Exception:
        return estado_padrao()


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
    txt = normalizar(texto)
    achados = re.findall(BONUS_REGEX, txt)
    if not achados:
        return ""
    maior = max(int(x) for x in achados)
    return f"{maior}%"


def url_absoluta(base: str, href: str) -> str:
    if not href:
        return ""
    return urljoin(base, href)


def caminho_url(link: str) -> str:
    try:
        parsed = urlparse(link)
        path = (parsed.path or "/").strip().lower()
        return path if path else "/"
    except Exception:
        return "/"


def link_generico(link: str) -> bool:
    if not link:
        return True

    path = caminho_url(link)

    if path in ROTAS_BLOQUEADAS_EXATAS:
        return True

    if any(t in path for t in TERMOS_BLOQUEADOS_NO_PATH):
        return True

    partes = [p for p in path.split("/") if p]
    if len(partes) <= 1:
        return True

    return False


def texto_ruim(texto: str) -> bool:
    txt = normalizar(texto)
    return any(t in txt for t in TERMOS_IGNORAR_TEXTO)


def tem_sinal_promocional(texto: str) -> bool:
    txt = normalizar(texto)

    tem_bonus = extrair_bonus(txt) != ""
    tem_real = any(p in txt for p in PALAVRAS_PROMO_REAL)
    tem_geral = any(p in txt for p in PALAVRAS_PROMO_GERAIS)
    tem_transfer = any(p in txt for p in PALAVRAS_TRANSFERENCIA)

    if tem_bonus and tem_transfer:
        return True

    if tem_real:
        return True

    if tem_bonus and tem_geral:
        return True

    return False


def extrair_tokens_relevantes(texto: str):
    txt = normalizar(texto)
    palavras = re.findall(r"[a-z0-9]{4,}", txt)
    tokens = []
    for p in palavras:
        if p in STOPWORDS:
            continue
        if p.isdigit():
            continue
        if p not in tokens:
            tokens.append(p)
    return tokens[:6]


def montar_chave_programa(programa: str, texto: str, link: str) -> str:
    bonus = extrair_bonus(texto)
    tokens = extrair_tokens_relevantes(texto)
    caminho = caminho_url(link)
    base = f"{programa}|{bonus}|{'-'.join(tokens)}|{caminho}"
    return normalizar(base)


def montar_chave_blog(programa: str, texto: str) -> str:
    bonus = extrair_bonus(texto)
    tokens = extrair_tokens_relevantes(texto)
    base = f"{programa}|{bonus}|{'-'.join(tokens)}"
    return normalizar(base)


def programa_no_texto(texto: str) -> str:
    txt = normalizar(texto)

    if "livelo" in txt:
        return "Livelo"
    if "smiles" in txt:
        return "Smiles"
    if "latam" in txt or "latam pass" in txt:
        return "LATAM"
    if "azul" in txt or "tudoazul" in txt:
        return "TudoAzul"

    return ""


def programa_da_url(url: str) -> str:
    txt = normalizar(url)

    if "livelo" in txt:
        return "Livelo"
    if "smiles" in txt:
        return "Smiles"
    if "latampass" in txt or "latam" in txt:
        return "LATAM"
    if "tudoazul" in txt or "voeazul" in txt or "azul" in txt:
        return "TudoAzul"

    return ""


def ja_enviado(chave: str) -> bool:
    return chave in estado["sent"]


def registrar_envio(chave: str):
    if chave not in estado["sent"]:
        estado["sent"].append(chave)
        salvar()


def limpar_sinais_antigos():
    agora = time.time()
    sinais = estado.get("signals", {})
    chaves_remover = []

    for k, dados in sinais.items():
        ultimo = dados.get("updated_at", 0)
        if agora - ultimo > TTL_SINAL:
            chaves_remover.append(k)

    for k in chaves_remover:
        sinais.pop(k, None)

    if chaves_remover:
        salvar()


def registrar_sinal(chave_evento: str, fonte: str, payload: dict):
    sinais = estado.setdefault("signals", {})
    agora = time.time()

    if chave_evento not in sinais:
        sinais[chave_evento] = {
            "sources": [],
            "payload": payload,
            "updated_at": agora,
        }

    if fonte not in sinais[chave_evento]["sources"]:
        sinais[chave_evento]["sources"].append(fonte)

    sinais[chave_evento]["payload"] = payload
    sinais[chave_evento]["updated_at"] = agora
    salvar()


def total_fontes_confirmadas(chave_evento: str) -> int:
    sinais = estado.get("signals", {})
    if chave_evento not in sinais:
        return 0
    return len(sinais[chave_evento].get("sources", []))


async def enviar_confirmado_se_precisar(context, chave_evento: str):
    sinal = estado.get("signals", {}).get(chave_evento)
    if not sinal:
        return

    if total_fontes_confirmadas(chave_evento) < 2:
        return

    chave_envio = f"confirmado|{chave_evento}"
    if ja_enviado(chave_envio):
        return

    payload = sinal["payload"]
    programa = payload.get("programa", "Programa")
    titulo = payload.get("titulo", "Promoção")
    link = payload.get("link", "")
    bonus = payload.get("bonus", "")
    fontes = ", ".join(sinal.get("sources", []))

    texto_bonus = f"\nBônus detectado: {bonus}" if bonus else ""

    msg = (
        f"✅ PROMOÇÃO CONFIRMADA EM 2 FONTES\n\n"
        f"Programa: {programa}\n"
        f"Título: {titulo}{texto_bonus}\n"
        f"Fontes: {fontes}\n"
    )

    if link:
        msg += f"\nLink:\n{link}"

    await context.bot.send_message(chat_id=CHAT_ID, text=msg)
    registrar_envio(chave_envio)
    ranking[f"{programa} confirmado"] = 15


def identificar_programa(nome_hint: str, texto: str, link: str) -> str:
    if nome_hint:
        return nome_hint

    por_texto = programa_no_texto(texto)
    if por_texto:
        return por_texto

    por_url = programa_da_url(link)
    if por_url:
        return por_url

    return "Programa"


def extrair_texto_link(tag) -> str:
    partes = []

    texto_tag = limpar_espacos(tag.get_text(" ", strip=True))
    if texto_tag:
        partes.append(texto_tag)

    title = limpar_espacos(tag.get("title", ""))
    aria = limpar_espacos(tag.get("aria-label", ""))

    if title:
        partes.append(title)
    if aria:
        partes.append(aria)

    return limpar_espacos(" | ".join(partes))


def resumo_promocoes():
    sinais = estado.get("signals", {})
    if not sinais:
        return "Nenhum sinal de promoção detectado ainda."

    linhas = []
    for _, dados in list(sinais.items())[:10]:
        payload = dados.get("payload", {})
        programa = payload.get("programa", "Programa")
        titulo = payload.get("titulo", "Promoção")
        bonus = payload.get("bonus", "")
        fontes = ", ".join(dados.get("sources", []))
        linha = f"• {programa} — {titulo}"
        if bonus:
            linha += f" ({bonus})"
        if fontes:
            linha += f" | fontes: {fontes}"
        linhas.append(linha[:220])

    return "\n".join(linhas) if linhas else "Nenhum sinal de promoção detectado ainda."


def resumo_transferencias():
    sinais = estado.get("signals", {})
    linhas = []

    for _, dados in sinais.items():
        payload = dados.get("payload", {})
        titulo = normalizar(payload.get("titulo", ""))
        bonus = payload.get("bonus", "")
        programa = payload.get("programa", "Programa")

        if any(p in titulo for p in PALAVRAS_TRANSFERENCIA) or bonus:
            linha = f"• {programa} — {payload.get('titulo', 'Transferência')}"
            if bonus:
                linha += f" ({bonus})"
            linhas.append(linha[:220])

    return "\n".join(linhas[:10]) if linhas else "Nenhuma transferência promocional detectada ainda."


# -----------------------------
# COMANDOS
# -----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = """
✈️ Radar de Milhas PRO+++ Ultra

/menu
/promocoes
/transferencias
/passagens
/ranking
/status
"""
    await update.message.reply_text(texto)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = """
📡 MENU

/promocoes
/transferencias
/passagens
/ranking
/status
"""
    await update.message.reply_text(texto)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    confirmados = 0
    for k in estado.get("sent", []):
        if str(k).startswith("confirmado|"):
            confirmados += 1

    texto = f"""
🟢 RADAR ONLINE

Promoções detectadas hoje: {len(ranking)}
Promoções confirmadas: {confirmados}

Detectores ativos:

✔ blogs
✔ programas
✔ milheiro
✔ radar antecipado
✔ confirmação em 2 fontes
"""
    await update.message.reply_text(texto)


async def ranking_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ranking:
        await update.message.reply_text("Nenhuma promoção detectada ainda.")
        return

    texto = "🏆 Ranking promoções\n\n"
    ordenado = sorted(ranking.items(), key=lambda x: x[1], reverse=True)

    pos = 1
    for titulo, score in ordenado[:10]:
        texto += f"{pos}️⃣ {titulo}\n"
        pos += 1

    await update.message.reply_text(texto)


async def promocoes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = "🔥 RESUMO DE PROMOÇÕES\n\n" + resumo_promocoes()
    await update.message.reply_text(texto)


async def transferencias_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = "🔁 RESUMO DE TRANSFERÊNCIAS\n\n" + resumo_transferencias()
    await update.message.reply_text(texto)


async def passagens_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = """
✈️ MONITOR DE PASSAGENS ATIVO

Detectando:
• possível erro tarifário
• promoções relâmpago
• sinais de oportunidade por milhas

Obs.: o filtro principal continua bloqueando páginas genéricas.
"""
    await update.message.reply_text(texto)


# -----------------------------
# RADAR BLOGS
# -----------------------------

async def monitor_blogs(context):
    limpar_sinais_antigos()

    for feed in RSS_FEEDS:
        try:
            noticias = feedparser.parse(feed)

            for post in noticias.entries[:8]:
                titulo = limpar_espacos(getattr(post, "title", ""))
                link = limpar_espacos(getattr(post, "link", ""))

                if not titulo or not link:
                    continue

                txt = normalizar(titulo)

                if texto_ruim(txt):
                    continue

                if not tem_sinal_promocional(txt):
                    continue

                programa = programa_no_texto(titulo)
                bonus = extrair_bonus(titulo)
                chave_evento = montar_chave_blog(programa or "Blog", titulo)

                registrar_sinal(
                    chave_evento=chave_evento,
                    fonte="blog",
                    payload={
                        "programa": programa or "Programa",
                        "titulo": titulo,
                        "link": link,
                        "bonus": bonus,
                    },
                )

                await enviar_confirmado_se_precisar(context, chave_evento)

                chave_envio = f"blog|{chave_evento}"
                if ja_enviado(chave_envio):
                    continue

                msg = f"🔥 SINAL EM BLOG\n\n{titulo}\n{link}"
                await context.bot.send_message(chat_id=CHAT_ID, text=msg)

                registrar_envio(chave_envio)
                ranking[titulo[:60]] = 10
                return

        except Exception:
            pass


# -----------------------------
# RADAR PROGRAMAS
# -----------------------------

async def monitor_programas(context):
    limpar_sinais_antigos()

    for nome, url in PROGRAMAS_SITES.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            links = soup.find_all("a", href=True)

            for tag in links:
                href = tag.get("href", "").strip()
                link = url_absoluta(url, href)

                if not link:
                    continue

                if link_generico(link):
                    continue

                texto = extrair_texto_link(tag)
                texto_norm = normalizar(texto)

                if not texto_norm:
                    continue

                if texto_ruim(texto_norm):
                    continue

                if not tem_sinal_promocional(texto_norm):
                    continue

                programa = identificar_programa(nome, texto, link)
                bonus = extrair_bonus(texto)

                chave_evento = montar_chave_programa(programa, texto, link)

                registrar_sinal(
                    chave_evento=chave_evento,
                    fonte="programa",
                    payload={
                        "programa": programa,
                        "titulo": texto[:140],
                        "link": link,
                        "bonus": bonus,
                    },
                )

                await enviar_confirmado_se_precisar(context, chave_evento)

                chave_envio = f"programa|{chave_evento}"
                if ja_enviado(chave_envio):
                    continue

                msg = (
                    f"🚨 POSSÍVEL PROMOÇÃO\n\n"
                    f"Programa: {programa}\n\n"
                    f"Título detectado:\n{texto[:180]}\n\n"
                    f"Link detectado:\n{link}"
                )

                await context.bot.send_message(chat_id=CHAT_ID, text=msg)

                registrar_envio(chave_envio)
                ranking[f"{programa} sinal"] = 8
                return

        except Exception:
            pass


# -----------------------------
# RADAR MILHEIRO
# -----------------------------

async def monitor_milheiro(context):
    for site in MILHEIRO_SITES:
        try:
            r = requests.get(site, headers=HEADERS, timeout=15)
            texto = normalizar(r.text)

            if "r$ 15" in texto or "r$15" in texto or "r$ 16" in texto or "r$16" in texto or "r$ 17" in texto or "r$17" in texto:
                chave = f"milheiro|{site}"

                if ja_enviado(chave):
                    continue

                msg = (
                    f"💰 MILHEIRO BARATO\n\n"
                    f"Possível oportunidade detectada\n\n"
                    f"{site}"
                )

                await context.bot.send_message(chat_id=CHAT_ID, text=msg)

                registrar_envio(chave)
                ranking["milheiro barato"] = 6

        except Exception:
            pass


# -----------------------------
# RADAR ANTECIPADO
# -----------------------------

async def radar_antecipado(context):
    limpar_sinais_antigos()

    for nome, url in FONTES_ANTECIPADAS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            texto_pagina = limpar_espacos(soup.get_text(" ", strip=True))
            texto_norm = normalizar(texto_pagina)

            tem_bonus = extrair_bonus(texto_norm) != ""
            tem_transfer = any(p in texto_norm for p in PALAVRAS_TRANSFERENCIA)
            tem_frase_real = any(p in texto_norm for p in PALAVRAS_PROMO_REAL)

            if not ((tem_bonus and tem_transfer) or tem_frase_real):
                continue

            programa = nome
            bonus = extrair_bonus(texto_norm)
            chave_evento = montar_chave_blog(programa, f"{programa} {bonus} antecipado")

            registrar_sinal(
                chave_evento=chave_evento,
                fonte="antecipado",
                payload={
                    "programa": programa,
                    "titulo": f"Sinal antecipado em parceiros - {programa}",
                    "link": url,
                    "bonus": bonus,
                },
            )

            await enviar_confirmado_se_precisar(context, chave_evento)

            # Não envia alerta isolado de /parceiros
            ranking[f"{programa} antecipado"] = 4

        except Exception:
            pass


# -----------------------------
# MAIN
# -----------------------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("promocoes", promocoes_cmd))
    app.add_handler(CommandHandler("transferencias", transferencias_cmd))
    app.add_handler(CommandHandler("passagens", passagens_cmd))
    app.add_handler(CommandHandler("ranking", ranking_cmd))
    app.add_handler(CommandHandler("status", status))

    job = app.job_queue
    job.run_repeating(monitor_blogs, interval=600, first=20)
    job.run_repeating(monitor_programas, interval=900, first=40)
    job.run_repeating(monitor_milheiro, interval=1200, first=60)
    job.run_repeating(radar_antecipado, interval=1500, first=80)

    print("Radar PRO+++ Ultra iniciado")
    app.run_polling()


if __name__ == "__main__":
    main()
