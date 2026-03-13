import requests


PROGRAMAS = [
    "https://www.smiles.com.br/promocoes",
    "https://www.latampass.com/promocoes",
    "https://www.tudoazul.com/promocoes"
]


def coletar_programas():

    resultados = []

    for url in PROGRAMAS:

        try:

            r = requests.get(url, timeout=20)

            if "bônus" in r.text.lower() or "bonus" in r.text.lower():

                resultados.append({
                    "tipo": "transferencia_bonificada",
                    "titulo": "Possível bônus detectado",
                    "link": url,
                    "fonte": url,
                    "detalhe": "Página contém menção a bônus"
                })

        except Exception:
            continue

    return resultados
