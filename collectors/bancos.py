import requests
from bs4 import BeautifulSoup

from config import BANCOS_URLS

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def coletar_bancos():
    resultados = []

    for nome, url in BANCOS_URLS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)

            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            texto = soup.get_text(" ", strip=True)

            resultados.append({
                "origem": "banco",
                "fonte": nome,
                "titulo": f"Promoções {nome}",
                "link": url,
                "texto": texto,
                "publicado": "",
            })

        except Exception:
            continue

    return resultados
