import feedparser

from .sources import FONTES_RSS


def coletar_todas_fontes():

    itens = []

    for url in FONTES_RSS:

        try:

            feed = feedparser.parse(url)

            for entry in feed.entries:

                titulo = entry.get("title", "")
                link = entry.get("link", "")

                itens.append({
                    "title": titulo,
                    "link": link
                })

        except Exception:
            continue

    return itens
