import re

import feedparser
import requests
import urllib3

from config import REQUEST_TIMEOUT
from utils.text_utils import normalize_text, split_sentences, strip_html_tags

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def fetch_url(url: str, verify_ssl=True) -> str:
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
        verify=verify_ssl,
    )
    response.raise_for_status()
    return response.text


def fetch_with_fallbacks(source: dict) -> str:
    candidates = [source["url"]] + source.get("fallback_urls", [])

    last_error = None
    for url in candidates:
        try:
            return fetch_url(url, verify_ssl=True)
        except requests.exceptions.SSLError:
            try:
                return fetch_url(url, verify_ssl=False)
            except Exception as e2:
                last_error = e2
        except Exception as e:
            last_error = e

    if last_error:
        raise last_error
    raise RuntimeError("Falha sem detalhe ao carregar fonte.")


def collect_rss(source: dict) -> list[dict]:
    items = []
    feed = feedparser.parse(source["url"])

    for entry in feed.entries[:25]:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")

        if not title or not link:
            continue

        items.append(
            {
                "source_name": source["name"],
                "source_group": source["group"],
                "title": title,
                "content": strip_html_tags(summary),
                "link": link,
            }
        )
    return items


def _extract_candidate_sentences(text_norm: str) -> list[str]:
    raw_sentences = split_sentences(text_norm)
    candidates = []

    patterns = [
        r"milheiro",
        r"b[oô]nus",
        r"transfer[êe]ncia",
        r"transfira pontos",
        r"alerta de passagens",
        r"passagens",
        r"resgate",
        r"trechos",
        r"latam pass",
        r"smiles",
        r"esfera",
        r"azul fidelidade",
        r"livelo",
        r"clube",
        r"maxmilhas",
        r"pontos",
        r"milhas",
    ]

    for sentence in raw_sentences:
        s = normalize_text(sentence)
        if any(re.search(p, s, flags=re.I) for p in patterns):
            candidates.append(sentence[:220].strip())

    unique = []
    seen = set()
    for c in candidates:
        key = normalize_text(c)
        if len(key) < 20:
            continue
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    return unique[:12]


def collect_html(source: dict) -> list[dict]:
    text = fetch_with_fallbacks(source)
    clean_text = strip_html_tags(text)
    text_norm = normalize_text(clean_text)

    snippets = _extract_candidate_sentences(text_norm)

    items = []
    for snippet in snippets:
        title = snippet[:180].strip()
        items.append(
            {
                "source_name": source["name"],
                "source_group": source["group"],
                "title": title,
                "content": snippet,
                "link": source["url"],
            }
        )

    return items
