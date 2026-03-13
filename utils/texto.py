import re
import unicodedata


def normalizar_texto(texto):
    texto = str(texto or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"\s+", " ", texto)
    return texto


def limpar_espacos(texto):
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def extrair_numeros_percentuais(texto):
    texto = normalizar_texto(texto)
    return [int(x) for x in re.findall(r"(\d{2,3})\s?%", texto)]


def extrair_precos_reais(texto):
    texto = str(texto or "")
    encontrados = re.findall(r"R\$\s*(\d{1,3}(?:[.,]\d{1,2})?)", texto, flags=re.IGNORECASE)
    valores = []

    for item in encontrados:
        try:
            valores.append(float(item.replace(",", ".")))
        except Exception:
            continue

    return valores


def extrair_valores_milhas(texto):
    texto = normalizar_texto(texto)

    encontrados = re.findall(r"(\d{1,3}(?:\.\d{3})+|\d{3,5})\s+milhas", texto)
    valores = []

    for item in encontrados:
        try:
            valores.append(int(item.replace(".", "")))
        except Exception:
            continue

    return valores
