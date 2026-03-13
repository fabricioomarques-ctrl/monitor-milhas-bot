import requests
from bs4 import BeautifulSoup

from config import SOCIAL_URLS

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def coletar_social():
    resultados = []

    for nome, url in SOCIAL_URLS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)

            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            texto = soup.get_text(" ", strip=True)

            resultados.append({
                "origem": "social",
                "fonte": nome,
                "titulo": f"Rede social {nome}",
                "link": url,
                "texto": texto,
                "publicado": "",
            })

        except Exception:
            continue

    return resultados
