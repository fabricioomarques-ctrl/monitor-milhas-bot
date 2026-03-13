import os

# =========================
# TELEGRAM
# =========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# =========================
# CONFIGURAÇÃO DO RADAR
# =========================

# TESTE: rodar a cada 60 segundos
INTERVALO = int(os.getenv("INTERVALO", "60"))

# =========================
# RSS DE SITES DE MILHAS
# =========================

RSS_FEEDS = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://pontospravoar.com/feed",
    "https://estevaopelomundo.com.br/feed",
]

# =========================
# PÁGINAS DOS PROGRAMAS
# =========================

PROGRAMAS_URLS = {
    "livelo": "https://www.livelo.com.br/promocoes",
    "smiles": "https://www.smiles.com.br/promocoes",
    "latam_pass": "https://www.latampass.com/promocoes",
    "tudoazul": "https://tudoazul.voeazul.com.br/promocoes",
}

# =========================
# SITES DE MILHEIRO
# =========================

MILHEIRO_URLS = {
    "maxmilhas": "https://www.maxmilhas.com.br",
    "hotmilhas": "https://www.hotmilhas.com.br",
}

# =========================
# REDES SOCIAIS (via Nitter)
# =========================

SOCIAL_URLS = {
    "livelo": "https://nitter.net/livelooficial",
    "smiles": "https://nitter.net/smilesoficial",
    "latam": "https://nitter.net/latampassbr",
    "azul": "https://nitter.net/azulinhasaereas",
}
