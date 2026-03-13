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

# 20 minutos para não massificar
INTERVALO_RADAR = int(os.getenv("INTERVALO_RADAR", "1200"))

# polling dos comandos do Telegram
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "3"))

# quantos itens mostrar por comando
LIMITE_COMANDO = int(os.getenv("LIMITE_COMANDO", "5"))

# alerta automático apenas para score forte
SCORE_MINIMO_ALERTA = float(os.getenv("SCORE_MINIMO_ALERTA", "7.0"))

# máximo de itens por alerta consolidado
MAX_ALERTAS_CONSOLIDADOS = int(os.getenv("MAX_ALERTAS_CONSOLIDADOS", "5"))

# não repetir a mesma oportunidade por 24h
JANELA_REPETICAO_HORAS = int(os.getenv("JANELA_REPETICAO_HORAS", "24"))

# dashboard web
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = int(os.getenv("PORT", "8000"))

# =========================
# FONTES - BLOGS
# =========================

BLOG_FEEDS = [
    "https://www.melhoresdestinos.com.br/feed",
    "https://passageirodeprimeira.com/feed",
    "https://pontospravoar.com/feed",
    "https://estevaopelomundo.com.br/feed",
    "https://www.melhorescartoes.com.br/feed",
    "https://www.falandodeviagem.com.br/feed",
    "https://viajenaviagem.com/feed",
    "https://aeroworld.com.br/feed",
]

TRUSTED_BLOG_SOURCES = set(BLOG_FEEDS)

# =========================
# FONTES - PROGRAMAS
# =========================

PROGRAMAS_URLS = {
    "smiles": "https://www.smiles.com.br/promocoes",
    "latam_pass": "https://www.latampass.com/promocoes",
    "tudoazul": "https://www.tudoazul.com/promocoes",
    "tap_milesgo": "https://www.flytap.com/pt-br/miles-and-go/promocoes",
}

# =========================
# FONTES - BANCOS / PONTOS
# =========================

BANCOS_URLS = {
    "livelo": "https://www.livelo.com.br/promocoes",
    "esfera": "https://www.esfera.com.vc/promocoes",
    "iupp": "https://www.iupp.com.br",
    "atomos": "https://www.programaatomos.com.br",
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
    "esfera": "https://nitter.net/esfera_",
}

# =========================
# DETECÇÃO
# =========================

# detectar qualquer bônus percentual; score decide qualidade
BONUS_MINIMO = int(os.getenv("BONUS_MINIMO", "1"))

MILHEIRO_MAXIMO = float(os.getenv("MILHEIRO_MAXIMO", "30"))
PASSAGEM_MILHAS_MAX = int(os.getenv("PASSAGEM_MILHAS_MAX", "25000"))

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
    "bonus livelo",
    "bonus esfera",
    "bonus smiles",
    "bonus latam pass",
    "bonus tudoazul",
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
