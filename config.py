import os

# =========================
# TELEGRAM
# =========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
CANAL_ID = os.getenv("CANAL_ID", "")

# =========================
# OPERAÇÃO
# =========================

# 10 minutos, fiel ao manual v3
INTERVALO_RADAR = int(os.getenv("INTERVALO_RADAR", "600"))

# intervalo de polling dos comandos
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "3"))

# número máximo de itens mostrados por comando
LIMITE_COMANDO = int(os.getenv("LIMITE_COMANDO", "5"))

# score mínimo para alerta automático (opção B escolhida)
SCORE_MINIMO_ALERTA = float(os.getenv("SCORE_MINIMO_ALERTA", "7.0"))

# quantidade máxima de oportunidades por alerta consolidado
MAX_ALERTAS_CONSOLIDADOS = int(os.getenv("MAX_ALERTAS_CONSOLIDADOS", "5"))

# =========================
# FONTES - BLOGS
# =========================

BLOG_FEEDS = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://pontospravoar.com/feed",
    "https://estevaopelomundo.com.br/feed",
]

# blogs confiáveis
TRUSTED_BLOG_SOURCES = set(BLOG_FEEDS)

# =========================
# FONTES - PROGRAMAS
# =========================

PROGRAMAS_URLS = {
    "smiles": "https://www.smiles.com.br/promocoes",
    "latam_pass": "https://www.latampass.com/promocoes",
    "tudoazul": "https://www.tudoazul.com/promocoes",
}

# =========================
# FONTES - BANCOS / PONTOS
# =========================

BANCOS_URLS = {
    "livelo": "https://www.livelo.com.br/promocoes",
    "esfera": "https://www.esfera.com.vc/promocoes",
}

# =========================
# FONTES - MERCADO DE MILHAS
# =========================

MILHEIRO_URLS = {
    "maxmilhas": "https://www.maxmilhas.com.br",
    "hotmilhas": "https://www.hotmilhas.com.br",
}

# =========================
# FONTES - REDES / NITTER
# =========================

SOCIAL_URLS = {
    "livelo": "https://nitter.net/livelooficial",
    "smiles": "https://nitter.net/smilesoficial",
    "latam": "https://nitter.net/latampassbr",
    "azul": "https://nitter.net/azulinhasaereas",
}

# =========================
# DETECÇÃO
# =========================

BONUS_MINIMO = int(os.getenv("BONUS_MINIMO", "80"))
MILHEIRO_MAXIMO = float(os.getenv("MILHEIRO_MAXIMO", "18"))
PASSAGEM_MILHAS_MAX = int(os.getenv("PASSAGEM_MILHAS_MAX", "5000"))

# =========================
# RUÍDO
# =========================

NOISE_WORDS = [
    "seguro",
    "assist card",
    "grupo de promocoes",
    "grupo de promoções",
    "grupo whatsapp",
    "cashback",
    "cupom",
    "cartao",
    "cartão",
    "shopping",
    "varejo",
    "pontos por real",
    "resumo das promocoes",
    "resumo das promoções",
    "resumo do dia",
    "grupo de descontos",
    "hotel",
    "diarias",
    "diárias",
]

# =========================
# CONTEXTOS
# =========================

KEYWORDS_TRANSFERENCIA = [
    "transferencia bonificada",
    "transferência bonificada",
    "bonus de transferencia",
    "bônus de transferência",
    "transferir pontos",
    "transfira seus pontos",
    "envie seus pontos",
]

KEYWORDS_PASSAGEM = [
    "passagem",
    "passagens",
    "trechos",
    "voo",
    "voos",
    "milhas latam pass",
    "milhas smiles",
    "milhas azul",
    "milhas tap",
    "a partir de",
]

CONTEXTO_MILHEIRO = [
    "milheiro",
    "milheiros",
    "milha",
    "milhas",
    "1000 milhas",
    "1.000 milhas",
    "compra de milhas",
    "venda de milhas",
    "preco do milheiro",
    "preço do milheiro",
    "lote de milhas",
]
