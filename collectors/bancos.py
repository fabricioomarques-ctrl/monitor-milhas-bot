import requests
from bs4 import BeautifulSoup

from config import BANCOS_URLS

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def coletar_bancos() -> tuple[list[dict], list[dict]]:
    resultados = []
    fontes = []

    for nome, url in BANCOS_URLS.items():
        meta = {
            "fonte": nome,
            "tipo": "banco",
            "status": "ok",
            "erro": "",
            "coletados": 0,
        }

        try:
            r = requests.get(url, headers=HEADERS, timeout=20)

            if r.status_code != 200:
                raise RuntimeError(f"status_code={r.status_code}")

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
            meta["coletados"] = 1

        except Exception as e:
            meta["status"] = "erro"
            meta["erro"] = str(e)

        fontes.append(meta)

    return resultados, fontes
