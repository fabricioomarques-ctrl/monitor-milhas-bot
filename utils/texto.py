import re
import unicodedata


def normalizar_texto(texto: str) -> str:
    texto = str(texto or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"\s+", " ", texto)
    return texto


def limpar_espacos(texto: str) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def extrair_percentuais(texto: str) -> list[int]:
    texto = normalizar_texto(texto)
    return [int(x) for x in re.findall(r"(\d{1,3})\s?%", texto)]


def extrair_precos_reais(texto: str) -> list[float]:
    texto = str(texto or "")
    encontrados = re.findall(r"R\$\s*(\d{1,3}(?:[.,]\d{1,2})?)", texto, flags=re.IGNORECASE)

    valores = []

    for item in encontrados:
        try:
            valores.append(float(item.replace(",", ".")))
        except Exception:
            continue

    return valores


def extrair_valores_milhas(texto: str) -> list[int]:
    texto = normalizar_texto(texto)
    encontrados = re.findall(r"(\d{1,3}(?:\.\d{3})+|\d{3,6})\s+milhas", texto)

    valores = []

    for item in encontrados:
        try:
            valores.append(int(item.replace(".", "")))
        except Exception:
            continue

    return valores


def slug_texto(texto: str) -> str:
    texto = normalizar_texto(texto)
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    texto = re.sub(r"-+", "-", texto).strip("-")
    return texto[:140]
