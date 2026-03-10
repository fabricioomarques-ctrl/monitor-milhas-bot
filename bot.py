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
CANAL_ID = os.getenv("CANAL_ID")

ARQUIVO_ESTADO = "historico.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
        "Mobile/15E148 Safari/604.1"
    )
}

# ==========================================
# FONTES
# ==========================================

RSS_FEEDS = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://pontospravoar.com/feed",
    "https://estevaopelomundo.com.br/feed",
]

PROGRAMAS = {
    "Livelo": "https://www.livelo.com.br/promocoes",
    "Smiles": "https://www.smiles.com.br/promocoes",
    "LATAM Pass": "https://www.latampass.com/pt_br/promocoes",
    "TudoAzul": "https://tudoazul.voeazul.com.br/web/azul/promocoes",
}

MILHEIRO = [
    "https://www.maxmilhas.com.br",
    "https://www.hotmilhas.com.br",
]

SOCIAL = {
    "Livelo": "https://nitter.net/livelo",
    "Smiles": "https://nitter.net/smilesoficial",
    "LATAM Pass": "https://nitter.net/latampass",
    "Azul": "https://nitter.net/voeazul",
}

# ==========================================
# REGRAS
# ==========================================

BONUS_REGEX = r"\b(30|40|50|60|70|80|85|90|95|100)\s*%\b"
MILHEIRO_REGEX = r"r\$\s*(1[4-8](?:[.,]\d{1,2})?)"

PROGRAMAS_MARCAS = [
    "livelo",
    "smiles",
    "latam",
    "latam pass",
    "tudoazul",
    "azul",
    "esfera",
]

TERMOS_TRANSFERENCIA = [
    "transferência bonificada",
    "transferencia bonificada",
    "bônus de transferência",
    "bonus de transferencia",
    "transferência",
    "transferencia",
    "transferir pontos",
]

TERMOS_RESGATE = [
    "milhas",
    "milha",
    "resgate",
    "emitir",
    "emissão",
    "emissao",
    "passagem com milhas",
    "voo com milhas",
]

TERMOS_CLUBE = [
    "clube smiles",
    "clube livelo",
    "clube latam pass",
    "clube azul",
    "clube tudoazul",
]

TERMOS_BLOQUEADOS = [
    "hotel",
    "hotéis",
    "hoteis",
    "resort",
    "cruzeiro",
    "seguro viagem",
    "seguro",
    "ingresso",
    "ingressos",
    "cvc",
    "pacote",
    "pacotes",
    "shopping livelo",
    "shopping smiles",
    "shopping",
    "pontos por real",
    "pontos por r$",
    "por real gasto",
    "cashback",
    "cupom",
    "natura",
    "extra",
    "lacoste",
    "beleza",
    "eletrônicos",
    "eletronicos",
    "moda",
    "casa",
    "varejo",
    "parceiros do shopping",
    "mês do consumidor",
    "mes do consumidor",
    "ofertas em eletrônicos",
    "ofertas em eletronicos",
    "grandes marcas",
]

ROTAS_GENERICAS = {
    "/",
    "/promocoes",
    "/promoções",
    "/ofertas",
    "/parceiros",
    "/home",
    "/shopping",
    "/pt_br/promocoes",
    "/pt_br/parceiros",
    "/web/azul/promocoes",
    "/web/azul/parceiros",
}

TTL_SINAIS = 24 * 60 * 60

# ==========================================
# ESTADO
# ==========================================

def estado_padrao():
    return {
        "enviados": [],
        "sinais": {},
        "alertas": [],
        "ranking": {},
    }


def carregar_estado():
    try:
        with open(ARQUIVO_ESTADO, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return estado_padrao()

        data.setdefault("enviados", [])
        data.setdefault("sinais", {})
        data.setdefault("alertas", [])
        data.setdefault("ranking", {})
        return data
    except Exception:
        return estado_padrao()


def salvar_estado():
    with open(ARQUIVO_ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


estado = carregar_estado()

# ==========================================
# HELPERS
# ==========================================

def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def limpar_espacos(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def extrair_bonus(texto: str) -> int:
    txt = normalizar(texto)
    m = re.search(BONUS_REGEX, txt)
    if not m:
        return 0
    return int(m.group(1))


def extrair_valor_milheiro(texto: str) -> float:
    txt = normalizar(texto).replace(",", ".")
    m = re.search(MILHEIRO_REGEX, txt)
    if not m:
        return 0.0
    try:
        return float(m.group(1))
    except Exception:
        return 0.0


def url_absoluta(base: str, href: str) -> str:
    if not href:
        return ""
    return urljoin(base, href)


def caminho_url(url: str) -> str:
    try:
        return (urlparse(url).path or "/").strip().lower() or "/"
    except Exception:
        return "/"


def link_generico(url: str) -> bool:
    path = caminho_url(url)
    if path in ROTAS_GENERICAS:
        return True
    partes = [p for p in path.split("/") if p]
    return len(partes) <= 1


def ja_enviado(chave: str) -> bool:
    return chave in estado["enviados"]


def registrar_envio(chave: str):
    if chave not in estado["enviados"]:
        estado["enviados"].append(chave)
        salvar_estado()


def limpar_sinais_antigos():
    agora = time.time()
    remover = []
    for chave, dados in estado["sinais"].items():
        if agora - dados.get("updated_at", 0) > TTL_SINAIS:
            remover.append(chave)

    for chave in remover:
        estado["sinais"].pop(chave, None)

    if remover:
        salvar_estado()


def texto_bloqueado(texto: str) -> bool:
    txt = normalizar(texto)
    return any(t in txt for t in TERMOS_BLOQUEADOS)


def eh_transferencia(texto: str) -> bool:
    txt = normalizar(texto)
    return any(t in txt for t in TERMOS_TRANSFERENCIA)


def eh_resgate(texto: str) -> bool:
    txt = normalizar(texto)
    return any(t in txt for t in TERMOS_RESGATE)


def eh_clube(texto: str) -> bool:
    txt = normalizar(texto)
    return any(t in txt for t in TERMOS_CLUBE)


def nome_programa_no_texto(texto: str) -> str:
    txt = normalizar(texto)
    if "livelo" in txt:
        return "Livelo"
    if "smiles" in txt:
        return "Smiles"
    if "latam" in txt:
        return "LATAM Pass"
    if "azul" in txt or "tudoazul" in txt:
        return "TudoAzul"
    if "esfera" in txt:
        return "Esfera"
    return ""


def filtro_ultra(texto: str) -> bool:
    txt = normalizar(texto)

    if not txt:
        return False

    if texto_bloqueado(txt):
        return False

    tem_bonus = extrair_bonus(txt) > 0
    tem_programa = any(p in txt for p in PROGRAMAS_MARCAS)

    if eh_transferencia(txt):
        return True

    if eh_resgate(txt):
        return True

    if eh_clube(txt):
        return True

    if tem_bonus and tem_programa:
        return True

    return False


def tipo_evento(texto: str, valor_milheiro: float = 0.0) -> str:
    txt = normalizar(texto)
    if valor_milheiro > 0:
        return "milheiro"
    if eh_transferencia(txt):
        return "transferencia"
    if eh_resgate(txt):
        return "passagem"
    if eh_clube(txt):
        return "clube"
    return "promocao"


def score_promocao(texto: str, valor_milheiro: float = 0.0, fontes: int = 1) -> float:
    txt = normalizar(texto)
    bonus = extrair_bonus(txt)

    if valor_milheiro > 0:
        if valor_milheiro <= 15.0:
            base = 9.8
        elif valor_milheiro <= 16.0:
            base = 9.2
        elif valor_milheiro <= 17.0:
            base = 8.4
        elif valor_milheiro <= 18.0:
            base = 7.5
        else:
            base = 6.0
    else:
        if bonus >= 100:
            base = 9.9
        elif bonus >= 95:
            base = 9.5
        elif bonus >= 90:
            base = 9.0
        elif bonus >= 85:
            base = 8.6
        elif bonus >= 80:
            base = 8.2
        elif bonus >= 70:
            base = 7.4
        elif bonus >= 60:
            base = 6.8
        elif bonus >= 50:
            base = 6.2
        elif eh_transferencia(txt):
            base = 6.4
        elif eh_resgate(txt):
            base = 6.1
        elif eh_clube(txt):
            base = 5.8
        else:
            base = 5.0

    if fontes >= 2:
        base += 0.4

    if eh_clube(txt):
        base -= 0.2

    return round(min(base, 10.0), 1)


def classificacao(score: float) -> str:
    if score >= 9.0:
        return "🔴 PROMOÇÃO IMPERDÍVEL"
    if score >= 7.5:
        return "🟡 Promoção muito boa"
    return "🟢 Promoção boa"


def chave_evento(programa: str, titulo: str, bonus: int = 0, valor_milheiro: float = 0.0) -> str:
    base = normalizar(f"{programa}|{titulo}|{bonus}|{valor_milheiro}")
    base = re.sub(r"[^a-z0-9| ]", "", base)
    return base[:220]


def registrar_sinal(chave: str, fonte: str, payload: dict):
    agora = time.time()

    if chave not in estado["sinais"]:
        estado["sinais"][chave] = {
            "fontes": [],
            "payload": payload,
            "updated_at": agora,
        }

    if fonte not in estado["sinais"][chave]["fontes"]:
        estado["sinais"][chave]["fontes"].append(fonte)

    estado["sinais"][chave]["payload"] = payload
    estado["sinais"][chave]["updated_at"] = agora
    salvar_estado()


def total_fontes(chave: str) -> int:
    return len(estado["sinais"].get(chave, {}).get("fontes", []))


def registrar_alerta_resumido(item: dict):
    alertas = estado.get("alertas", [])
    alertas.insert(0, item)
    estado["alertas"] = alertas[:30]
    salvar_estado()


def resumo_alertas(tipo=None) -> str:
    itens = estado.get("alertas", [])
    if tipo:
        itens = [i for i in itens if i.get("tipo") == tipo]

    if not itens:
        return "Nenhuma promoção registrada ainda."

    linhas = []
    for item in itens[:10]:
        titulo = item.get("titulo", "Promoção")
        score = item.get("score", 0)
        linhas.append(f"• {titulo} | score {score}")
    return "\n".join(linhas)


def extrair_texto_link(tag) -> str:
    partes = []

    texto = limpar_espacos(tag.get_text(" ", strip=True))
    if texto:
        partes.append(texto)

    title = limpar_espacos(tag.get("title", ""))
    aria = limpar_espacos(tag.get("aria-label", ""))

    if title:
        partes.append(title)
    if aria:
        partes.append(aria)

    return limpar_espacos(" | ".join(partes))


async def enviar_telegram(context, texto: str):
    await context.bot.send_message(chat_id=CHAT_ID, text=texto)

    if CANAL_ID:
        try:
            await context.bot.send_message(chat_id=CANAL_ID, text=texto)
        except Exception:
            pass


async def processar_evento(context, fonte: str, programa: str, titulo: str, link: str = "", valor_milheiro: float = 0.0):
    limpar_sinais_antigos()

    bonus = extrair_bonus(titulo)
    tipo = tipo_evento(titulo, valor_milheiro)
    chave = chave_evento(programa, titulo, bonus, valor_milheiro)

    registrar_sinal(
        chave=chave,
        fonte=fonte,
        payload={
            "programa": programa,
            "titulo": titulo,
            "link": link,
            "bonus": bonus,
            "tipo": tipo,
            "valor_milheiro": valor_milheiro,
        },
    )

    min_fontes = 1 if tipo == "milheiro" else 2

    if total_fontes(chave) < min_fontes:
        return

    envio_key = f"alerta|{chave}"
    if ja_enviado(envio_key):
        return

    fontes = total_fontes(chave)
    score = score_promocao(titulo, valor_milheiro=valor_milheiro, fontes=fontes)
    nivel = classificacao(score)

    if tipo == "transferencia":
        emoji = "🔥"
    elif tipo == "passagem":
        emoji = "✈️"
    elif tipo == "milheiro":
        emoji = "💰"
    elif tipo == "clube":
        emoji = "⭐"
    else:
        emoji = "⚡"

    texto = f"{emoji} PROMOÇÃO CONFIRMADA\n\n"

    if programa:
        texto += f"Programa: {programa}\n"

    texto += f"Título: {titulo}\n"

    if bonus:
        texto += f"Bônus: {bonus}%\n"

    if valor_milheiro > 0:
        texto += f"Milheiro detectado: R$ {valor_milheiro:.2f}\n"

    texto += f"Fontes confirmadas: {fontes}\n"
    texto += f"Score: {score}\n"
    texto += f"{nivel}\n"

    if link:
        texto += f"\nLink:\n{link}"

    await enviar_telegram(context, texto)
    registrar_envio(envio_key)

    registrar_alerta_resumido({
        "titulo": titulo,
        "tipo": tipo,
        "score": score,
    })

    nome_rank = titulo if tipo != "milheiro" else "Milheiro barato"
    atual = estado["ranking"].get(nome_rank, 0)
    if score > atual:
        estado["ranking"][nome_rank] = score
        salvar_estado()

# ==========================================
# COMANDOS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = """
✈️ Radar de Milhas PRO MAX

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
    texto = f"""
🟢 Radar online

Promoções detectadas: {len(estado.get("ranking", {}))}
Fontes monitoradas: {len(RSS_FEEDS) + len(PROGRAMAS) + len(MILHEIRO) + len(SOCIAL)}

Detectores ativos:
✔ blogs
✔ programas
✔ milheiro
✔ redes sociais
✔ confirmação múltipla
✔ score automático
✔ envio no canal
"""
    await update.message.reply_text(texto)


async def ranking_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dados = estado.get("ranking", {})
    if not dados:
        await update.message.reply_text("Nenhuma promoção detectada.")
        return

    texto = "🏆 Ranking promoções\n\n"
    ordenado = sorted(dados.items(), key=lambda x: x[1], reverse=True)

    for i, (nome, score) in enumerate(ordenado[:10], 1):
        texto += f"{i}. {nome} | score {score}\n"

    await update.message.reply_text(texto)


async def promocoes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = "🔥 Últimas promoções\n\n" + resumo_alertas()
    await update.message.reply_text(texto)


async def transferencias_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = "🔁 Últimas transferências\n\n" + resumo_alertas("transferencia")
    await update.message.reply_text(texto)


async def passagens_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = "✈️ Últimos alertas de passagens\n\n" + resumo_alertas("passagem")
    await update.message.reply_text(texto)

# ==========================================
# MONITORES
# ==========================================

async def monitor_blogs(context):
    for feed in RSS_FEEDS:
        try:
            data = feedparser.parse(feed)

            for post in data.entries[:8]:
                titulo = limpar_espacos(getattr(post, "title", ""))
                link = limpar_espacos(getattr(post, "link", ""))

                if not titulo or not link:
                    continue

                if not filtro_ultra(titulo):
                    continue

                if texto_bloqueado(titulo):
                    continue

                programa = nome_programa_no_texto(titulo)

                await processar_evento(
                    context=context,
                    fonte="blog",
                    programa=programa,
                    titulo=titulo,
                    link=link,
                )
        except Exception:
            pass


async def monitor_programas(context):
    for nome, url in PROGRAMAS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            links = soup.find_all("a", href=True)

            for a in links:
                href = a.get("href", "").strip()
                link = url_absoluta(url, href)
                texto = extrair_texto_link(a)

                if not link or link_generico(link):
                    continue

                if not filtro_ultra(texto):
                    continue

                if texto_bloqueado(texto):
                    continue

                await processar_evento(
                    context=context,
                    fonte="programa",
                    programa=nome,
                    titulo=texto,
                    link=link,
                )
        except Exception:
            pass


async def monitor_milheiro(context):
    for site in MILHEIRO:
        try:
            r = requests.get(site, headers=HEADERS, timeout=15)
            txt = normalizar(r.text)

            valor = extrair_valor_milheiro(txt)
            if valor <= 0:
                continue

            if valor > 18:
                continue

            await processar_evento(
                context=context,
                fonte="milheiro",
                programa="Mercado de Milhas",
                titulo=f"Milheiro barato detectado em {site}",
                link=site,
                valor_milheiro=valor,
            )
        except Exception:
            pass


async def monitor_social(context):
    for nome, url in SOCIAL.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            posts = soup.find_all("div", class_="timeline-item")[:4]
            for post in posts:
                txt = limpar_espacos(post.get_text(" ", strip=True))

                if not filtro_ultra(txt):
                    continue

                if texto_bloqueado(txt):
                    continue

                await processar_evento(
                    context=context,
                    fonte="social",
                    programa=nome,
                    titulo=txt[:220],
                    link=url,
                )
        except Exception:
            pass

# ==========================================
# MAIN
# ==========================================

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

    # modo estável: 10 minutos
    job.run_repeating(monitor_blogs, interval=600, first=20)
    job.run_repeating(monitor_programas, interval=600, first=40)
    job.run_repeating(monitor_milheiro, interval=600, first=60)
    job.run_repeating(monitor_social, interval=600, first=80)

    print("Radar de Milhas PRO MAX iniciado")
    app.run_polling()


if __name__ == "__main__":
    main()
