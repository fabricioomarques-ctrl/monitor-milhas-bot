import feedparser


from config import BLOG_FEEDS


def coletar_blogs() -> tuple[list[dict], list[dict]]:
    resultados = []
    fontes = []

    for feed_url in BLOG_FEEDS:
        meta = {
            "fonte": feed_url,
            "tipo": "blog",
            "status": "ok",
            "erro": "",
            "coletados": 0,
        }

        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:10]:
                titulo = getattr(entry, "title", "") or ""
                link = getattr(entry, "link", "") or ""
                resumo = getattr(entry, "summary", "") or ""
                publicado = getattr(entry, "published", "")
