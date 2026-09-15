#!/usr/bin/env python3
"""Generate publications/index.html from data/henkler_all.bib.

The BibTeX file is the canonical source. Each rendered publication contains a
native HTML <details> control that reveals the original, unmodified BibTeX
entry for that publication. No client-side JavaScript is required.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIB_PATH = ROOT / "data" / "henkler_all.bib"
TEMPLATE_PATH = ROOT / "publications" / "template.html"
OUTPUT_PATH = ROOT / "publications" / "index.html"

START = "<!-- PUBLICATIONS:START -->"
END = "<!-- PUBLICATIONS:END -->"


def split_bibtex_entries(text: str) -> list[str]:
    """Split BibTeX while preserving every entry exactly as written."""
    entries: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        at = text.find("@", i)
        if at < 0:
            break
        brace = text.find("{", at)
        paren = text.find("(", at)
        candidates = [p for p in (brace, paren) if p >= 0]
        if not candidates:
            break
        opening = min(candidates)
        closing = "}" if text[opening] == "{" else ")"
        depth = 0
        escaped = False
        j = opening
        while j < n:
            ch = text[j]
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == text[opening]:
                depth += 1
            elif ch == closing:
                depth -= 1
                if depth == 0:
                    entries.append(text[at : j + 1].strip())
                    i = j + 1
                    break
            j += 1
        else:
            raise ValueError(f"Unterminated BibTeX entry beginning at character {at}")
    return entries


def entry_header(raw: str) -> tuple[str, str, str]:
    m = re.match(r"@\s*([^\s{(]+)\s*[{(]\s*([^,\s]+)\s*,", raw, re.S)
    if not m:
        raise ValueError(f"Cannot parse BibTeX entry header: {raw[:80]!r}")
    entry_type, key = m.group(1).lower(), m.group(2)
    body_start = m.end()
    body = raw[body_start:-1]
    return entry_type, key, body


def parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    i = 0
    n = len(body)
    while i < n:
        while i < n and (body[i].isspace() or body[i] == ","):
            i += 1
        m = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", body[i:])
        if not m:
            break
        name = m.group(1).lower()
        i += m.end()
        if i >= n:
            break
        if body[i] == "{":
            start = i + 1
            depth = 1
            i += 1
            escaped = False
            while i < n and depth:
                ch = body[i]
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                i += 1
            value = body[start : i - 1]
        elif body[i] == '"':
            i += 1
            start = i
            escaped = False
            while i < n:
                ch = body[i]
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    break
                i += 1
            value = body[start:i]
            i += 1
        else:
            start = i
            while i < n and body[i] not in ",\n\r":
                i += 1
            value = body[start:i].strip()
        fields[name] = value.strip()
    return fields


LATEX_REPLACEMENTS = {
    r'\\"a': "ä", r'\\"o': "ö", r'\\"u': "ü", r'\\"A': "Ä", r'\\"O': "Ö", r'\\"U': "Ü",
    r"\\'a": "á", r"\\'e": "é", r"\\'i": "í", r"\\'o": "ó", r"\\'u": "ú",
    r"\\ss": "ß", r"\\&": "&", r"\\%": "%", r"\\_": "_", "~": " ",
}


def plain(value: str) -> str:
    s = value
    for old, new in LATEX_REPLACEMENTS.items():
        s = s.replace(old, new)
    s = re.sub(r"\\[a-zA-Z]+\s*", "", s)
    s = s.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", s).strip()


def authors(value: str) -> str:
    people = re.split(r"\s+and\s+", plain(value))
    rendered = []
    for person in people:
        person = person.strip()
        if "," in person:
            last, first = [p.strip() for p in person.split(",", 1)]
            rendered.append(f"{first} {last}".strip())
        else:
            rendered.append(person)
    if len(rendered) <= 2:
        return " and ".join(rendered)
    return ", ".join(rendered[:-1]) + ", and " + rendered[-1]


def venue(fields: dict[str, str]) -> str:
    for name in ("journal", "booktitle", "school", "institution", "publisher"):
        if fields.get(name):
            return plain(fields[name])
    return ""


def publication_html(raw: str) -> tuple[int, str, str]:
    entry_type, key, body = entry_header(raw)
    f = parse_fields(body)
    year_text = plain(f.get("year", ""))
    try:
        year_sort = int(re.search(r"\d{4}", year_text).group())
    except (AttributeError, ValueError):
        year_sort = 0

    author_text = authors(f.get("author") or f.get("editor", ""))
    title_text = plain(f.get("title", key))
    venue_text = venue(f)

    parts = []
    if author_text:
        parts.append(html.escape(author_text))
    parts.append(f'<span class="publication-title">{html.escape(title_text)}</span>')
    if venue_text:
        parts.append(f'<span class="publication-venue">{html.escape(venue_text)}</span>')
    if year_text:
        parts.append(html.escape(year_text))

    links = []
    doi = plain(f.get("doi", ""))
    url = plain(f.get("url", ""))
    if doi:
        doi_url = doi if doi.startswith("http://") or doi.startswith("https://") else "https://doi.org/" + doi
        links.append(f'<a href="{html.escape(doi_url, quote=True)}">DOI</a>')
    if url and (not doi or url.rstrip("/") != ("https://doi.org/" + doi).rstrip("/")):
        links.append(f'<a href="{html.escape(url, quote=True)}">Link</a>')

    citation = ". ".join(parts) + "."
    if links:
        citation += " " + " · ".join(links)

    raw_escaped = html.escape(raw)
    block = f'''<article class="publication" id="pub-{html.escape(key, quote=True)}">
  <p class="publication-entry">{citation}</p>
  <details class="bibtex-entry">
    <summary>BibTeX</summary>
    <pre><code>{raw_escaped}</code></pre>
  </details>
</article>'''
    sort_author = plain(f.get("author") or f.get("editor", "")).lower()
    return year_sort, sort_author + "\0" + title_text.lower(), block


def main() -> None:
    bib_text = BIB_PATH.read_text(encoding="utf-8")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if START not in template or END not in template:
        raise ValueError("Publication template is missing generation markers")

    rendered = [publication_html(raw) for raw in split_bibtex_entries(bib_text)]
    rendered.sort(key=lambda item: (-item[0], item[1]))
    generated = "\n\n".join(item[2] for item in rendered)

    before, rest = template.split(START, 1)
    _, after = rest.split(END, 1)
    output = before + START + "\n" + generated + "\n  " + END + after
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"Generated {OUTPUT_PATH.relative_to(ROOT)} with {len(rendered)} entries.")


if __name__ == "__main__":
    main()
