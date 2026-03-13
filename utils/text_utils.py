import hashlib
import html
import re


def strip_html_tags(text: str) -> str:
    text = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def normalize_text(text: str) -> str:
    text = strip_html_tags(text or "")
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def build_hash_id(*parts: str) -> str:
    raw = "|".join([normalize_text(p) for p in parts if p is not None])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def title_signature(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^a-z0-9à-úç\s]", " ", text)
    tokens = [t for t in text.split() if len(t) > 2]
    return " ".join(tokens[:12])


def has_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def detect_price_brl(text: str):
    normalized = text.replace(".", "").replace(",", ".")
    matches = re.findall(r"r\$\s*(\d+(?:\.\d{1,2})?)", normalized, flags=re.I)
    if matches:
        try:
            return float(matches[0])
        except Exception:
            return None
    return None


def detect_percent(text: str):
    match = re.search(r"(\d{2,3})\s*%", text)
    if match:
        try:
            return int(match.group(1))
        except Exception:
            return None
    return None


def detect_miles_amount(text: str):
    text = normalize_text(text)
    match = re.search(r"(\d{3,6})\s*(milhas|pontos)", text)
    if match:
        try:
            return int(match.group(1))
        except Exception:
            return None
    return None


def split_sentences(text: str) -> list[str]:
    text = strip_html_tags(text or "")
    parts = re.split(r"(?<=[\.\!\?])\s+", text)
    cleaned = []
    for part in parts:
        part = re.sub(r"\s+", " ", part).strip()
        if len(part) >= 20:
            cleaned.append(part)
    return cleaned
