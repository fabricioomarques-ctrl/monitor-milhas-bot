import requests
from bs4 import BeautifulSoup

from config import PROGRAMAS_URLS

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def coletar_programas():
    resultados = []

    for nome, url in PROGRAMAS_URLS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)

            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            texto = soup.get_text(" ", strip=True)

            resultados.append({
                "origem": "programa",
                "fonte": nome,
                "titulo": f"Promoções {nome}",
                "link": url,
                "texto": texto,
                "publicado": "",
            })

        except Exception:
            continue

    return resultados
