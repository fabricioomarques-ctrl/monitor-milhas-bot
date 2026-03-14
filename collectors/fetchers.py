import feedparser

from .sources import FONTES_RSS


def coletar_todas_fontes():
    itens = []
    falhas = {}

    for url in FONTES_RSS:
        try:
            feed = feedparser.parse(url)

            for entry in getattr(feed, "entries", []):
                itens.append(
                    {
                        "title": entry.get("title", "") or "",
                        "link": entry.get("link", "") or "",
                        "summary": entry.get("summary", "") or "",
                        "source_url": url,
                    }
                )
        except Exception as e:
            falhas[url] = str(e)

    return itens, falhas
