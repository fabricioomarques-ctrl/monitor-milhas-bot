import requests

from bs4 import BeautifulSoup

from config import MILHEIRO_URLS


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def coletar_milheiro():

    resultados = []

    for nome, url in MILHEIRO_URLS.items():

        try:

            r = requests.get(
                url,
                headers=HEADERS,
                timeout=20
            )

            if r.status_code != 200:
                continue

            soup = BeautifulSoup(
                r.text,
                "html.parser"
            )

            texto = soup.get_text(
                " ",
                strip=True
            )

            resultados.append({

                "fonte": nome,
                "titulo": f"Milheiro {nome}",
                "link": url,
                "texto": texto,
                "origem": "milheiro"

            })

        except Exception:
            continue

    return resultados
