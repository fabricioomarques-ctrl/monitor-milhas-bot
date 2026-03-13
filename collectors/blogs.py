import feedparser


BLOG_FEEDS = [
    "https://pontospravoar.com/feed",
    "https://passageirodeprimeira.com/feed",
    "https://www.melhoresdestinos.com.br/feed",
]


def coletar_blogs():

    resultados = []

    for feed in BLOG_FEEDS:

        try:

            data = feedparser.parse(feed)

            for entry in data.entries[:5]:

                resultados.append({
                    "tipo": "blog",
                    "titulo": entry.title,
                    "link": entry.link,
                    "fonte": feed,
                    "detalhe": "Promoção detectada em blog"
                })

        except Exception:
            continue

    return resultados
