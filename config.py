import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
CANAL_ID = os.getenv("CANAL_ID", "").strip()

ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", os.getenv("CHAT_ID", "")).split(",")
    if x.strip().isdigit()
]

RADAR_INTERVAL_SECONDS = 3600

PROMOCOES_FILE = "promocoes_enviadas.json"
METRICS_FILE = "dashboard_metrics.json"

REQUEST_TIMEOUT = 12
MAX_RANKING = 10

if not TELEGRAM_TOKEN:
    raise RuntimeError("Variável TELEGRAM_TOKEN não configurada.")

if not CANAL_ID:
    raise RuntimeError("Variável CANAL_ID não configurada.")
