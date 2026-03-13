import os

# =========================
# TELEGRAM
# =========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# =========================
# RADAR
# =========================

# 3600 segundos = 1 hora
INTERVALO = int(os.getenv("INTERVALO", "3600"))

# polling de comandos
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "3"))

# quantos resultados mostrar nos comandos
LIMITE_COMANDO = int(os.getenv("LIMITE_COMANDO", "5"))

# =========================
# REGRAS DE DETECÇÃO
# =========================

BONUS_MINIMO = int(os.getenv("BONUS_MINIMO", "80"))
MILHEIRO_MAXIMO = float(os.getenv("MILHEIRO_MAXIMO", "18"))
PASSAGEM_MILHAS_MAX = int(os.getenv("PASSAGEM_MILHAS_MAX", "5000"))

# =========================
# RSS DE BLOGS
# =========================

BLOG_FEEDS = [
    "https://pontospravoar.com/feed",
    "https://passageirodeprimeira.com/feed",
    "https://www.melhoresdestinos.com.br/feed",
]

# =========================
# PROGRAMAS DE MILHAS
# =========================

PROGRAMAS_URLS = {
    "smiles": "https://www.smiles.com.br/promocoes",
    "latam_pass": "https://www.latampass.com/promocoes",
    "tudoazul": "https://www.tudoazul.com/promocoes",
}

# =========================
# BANCOS / PROGRAMAS DE PONTOS
# =========================

BANCOS_URLS = {
    "livelo": "https://www.livelo.com.br/promocoes",
    "esfera": "https://www.esfera.com.vc/promocoes",
}

# =========================
# PALAVRAS DE RUÍDO
# =========================

NOISE_WORDS = [
    "seguro",
    "assist card",
    "grupo de promoções",
    "grupo de promocoes",
    "grupo whatsapp",
    "cashback",
    "cupom",
    "cartão",
    "cartao",
    "oferta de hotel",
    "hotel",
    "resumo das promoções",
    "resumo das promocoes",
    "resumo do dia",
    "grupo de descontos",
    "black friday genérica",
]

# =========================
# CONTEXTO DE MILHEIRO
# =========================

CONTEXTO_MILHEIRO = [
    "milheiro",
    "milheiros",
    "milha",
    "milhas",
    "1.000 milhas",
    "1000 milhas",
    "compra de milhas",
    "venda de milhas",
    "preço do milheiro",
    "preco do milheiro",
    "lote de milhas",
]

# =========================
# CONTEXTO DE TRANSFERÊNCIA
# =========================

KEYWORDS_TRANSFERENCIA = [
    "transferência bonificada",
    "transferencia bonificada",
    "bônus de transferência",
    "bonus de transferencia",
    "transferir pontos",
    "transfira seus pontos",
    "envie seus pontos",
]

# =========================
# CONTEXTO DE PASSAGENS
# =========================

KEYWORDS_PASSAGEM = [
    "passagem",
    "passagens",
    "trechos",
    "voos",
    "voo",
    "a partir de",
    "milhas latam pass",
    "milhas smiles",
    "milhas azul",
]
