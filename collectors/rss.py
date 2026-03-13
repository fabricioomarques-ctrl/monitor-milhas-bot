import feedparser

from config import RSS_FEEDS


def coletar_rss():

    resultados = []

    for url in RSS_FEEDS:

        try:

            feed = feedparser.parse(url)

            for entry in feed.entries[:10]:

                resultados.append({

                    "fonte": url,
                    "titulo": getattr(entry, "title", ""),
                    "link": getattr(entry, "link", ""),
                    "texto": getattr(entry, "title", ""),
                    "origem": "rss"

                })

        except Exception:
            continue

    return resultados
