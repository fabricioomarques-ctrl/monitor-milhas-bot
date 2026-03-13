import requests


BANCOS = [
    "https://www.livelo.com.br/promocoes",
    "https://www.esfera.com.vc/promocoes"
]


def coletar_bancos():

    resultados = []

    for url in BANCOS:

        try:

            r = requests.get(url, timeout=20)

            if "transfer" in r.text.lower():

                resultados.append({
                    "tipo": "transferencia_bonificada",
                    "titulo": "Promoção possível detectada",
                    "link": url,
                    "fonte": url,
                    "detalhe": "Página contém transferência"
                })

        except Exception:
            continue

    return resultados
