"""HTML reducer.

Strips scripts/styles and flattens hierarchical specs (tables, definition
lists, nested divs) into compact, bounded ``name: value`` text. This both shrinks
token usage and mitigates prompt-injection by discarding executable/markup noise
before anything reaches the LLM.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

# Tags whose content is never useful to the LLM and may carry injection payloads.
_DROP_TAGS = ("script", "style", "noscript", "template", "svg", "iframe")

MAX_CHARS = 6000


def reduce_html(html: str, *, max_chars: int = MAX_CHARS) -> str:
    """Return a compact textual reduction of ``html`` suitable for the LLM."""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(_DROP_TAGS):
        tag.decompose()

    lines: list[str] = []

    title = _first_text(soup, ("h1", "h2", "title"))
    if title:
        lines.append(f"Title: {title}")

    lines.extend(_extract_labeled(soup))
    lines.extend(_extract_tables(soup))
    lines.extend(_extract_definition_lists(soup))
    lines.extend(_extract_spec_divs(soup))

    if not lines:
        # Fall back to a flattened text dump.
        lines.append(_collapse(soup.get_text(" ")))

    # De-duplicate while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for line in lines:
        line = _collapse(line)
        if line and line not in seen:
            seen.add(line)
            deduped.append(line)

    text = "\n".join(deduped)
    return text[:max_chars]


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _first_text(soup: BeautifulSoup, names: tuple[str, ...]) -> str:
    for name in names:
        el = soup.find(name)
        if el and el.get_text(strip=True):
            return _collapse(el.get_text(" "))
    return ""


def _extract_labeled(soup: BeautifulSoup) -> list[str]:
    """Pull elements that carry explicit data labels via class or itemprop."""
    out: list[str] = []
    label_map = {
        "price": "Price",
        "sku": "SKU",
        "availability": "Availability",
        "stock": "Availability",
    }
    for el in soup.find_all(True):
        if not isinstance(el, Tag):
            continue
        tokens: set[str] = set()
        cls = el.get("class")
        if cls:
            tokens.update(c.lower() for c in cls)
        itemprop = el.get("itemprop")
        if itemprop:
            tokens.add(str(itemprop).lower())
        for token, label in label_map.items():
            if token in tokens:
                value = _collapse(el.get_text(" "))
                if value:
                    out.append(f"{label}: {value}")
                break
    return out


def _extract_tables(soup: BeautifulSoup) -> list[str]:
    out: list[str] = []
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [c for c in row.find_all(["th", "td"])]
            if len(cells) >= 2:
                key = _collapse(cells[0].get_text(" "))
                val = _collapse(cells[1].get_text(" "))
                if key and val:
                    out.append(f"{key}: {val}")
    return out


def _extract_definition_lists(soup: BeautifulSoup) -> list[str]:
    out: list[str] = []
    for dl in soup.find_all("dl"):
        terms = dl.find_all("dt")
        defs = dl.find_all("dd")
        for dt, dd in zip(terms, defs, strict=False):
            key = _collapse(dt.get_text(" "))
            val = _collapse(dd.get_text(" "))
            if key and val:
                out.append(f"{key}: {val}")
    return out


def _extract_spec_divs(soup: BeautifulSoup) -> list[str]:
    """Flatten nested spec containers like <div class="spec"><span>k</span><span>v</span>."""
    out: list[str] = []
    for spec in soup.select('[class*="spec"], [class*="attribute"], [class*="feature"]'):
        children = [c for c in spec.find_all(["span", "div", "li"], recursive=False)]
        if len(children) >= 2:
            key = _collapse(children[0].get_text(" "))
            val = _collapse(children[1].get_text(" "))
            if key and val:
                out.append(f"{key}: {val}")
    return out
