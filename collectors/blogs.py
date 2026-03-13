import feedparser

from config import BLOG_FEEDS


def coletar_blogs():
    resultados = []

    for feed_url in BLOG_FEEDS:
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:10]:
                titulo = getattr(entry, "title", "") or ""
                link = getattr(entry, "link", "") or ""
                resumo = getattr(entry, "summary", "") or ""
                publicado = getattr(entry, "published", "") or ""

                texto = f"{titulo} {resumo}"

                resultados.append({
                    "origem": "blog",
                    "fonte": feed_url,
                    "titulo": titulo,
                    "link": link,
                    "texto": texto,
                    "publicado": publicado,
                })

        except Exception:
            continue

    return resultados
