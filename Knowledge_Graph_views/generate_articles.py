"""
Generate structured .txt files from articles_en-us.json.
Output is written to Knowledge_Graph_views/data/ matching the existing format.
"""

import json
import os
import re
import textwrap
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    """Strip HTML tags and decode entities to plain text."""

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str):
        self._parts.append(data)

    def handle_entityref(self, name: str):
        from html import unescape
        self._parts.append(unescape(f"&{name};"))

    def handle_charref(self, name: str):
        from html import unescape
        self._parts.append(unescape(f"&#{name};"))

    def get_text(self) -> str:
        return "".join(self._parts)


def html_to_text(html: str) -> str:
    """Convert HTML string to clean plain text."""
    if not html:
        return ""
    extractor = HTMLTextExtractor()
    extractor.feed(html)
    text = extractor.get_text()
    # Normalize whitespace: collapse runs of spaces/tabs but keep newlines
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def sanitize_filename(title: str, max_len: int = 80) -> str:
    """Create a safe, readable filename from an article title."""
    # Remove common suffixes
    title = re.sub(r"\s*-\s*Microsoft Support\s*$", "", title, flags=re.IGNORECASE)
    # Replace non-alphanumeric chars (except spaces/hyphens) with nothing
    name = re.sub(r"[^\w\s-]", "", title)
    # Collapse whitespace and convert to underscores
    name = re.sub(r"[\s]+", "_", name.strip())
    # Truncate
    if len(name) > max_len:
        name = name[:max_len].rstrip("_")
    return name


def format_article(article: dict) -> str:
    """Format one JSON article into structured plain text."""
    title = article.get("title", "Untitled Article")
    article_id = article.get("articlepublicnumber", "N/A")
    created = article.get("createdon", "")[:10]  # date only
    modified = article.get("modifiedon", "")[:10]
    keywords = article.get("keywords", "")
    description = article.get("description", "")
    language = article.get("msdyn_languagecode", "en-us")
    url = article.get("msdyn_ingestedarticleurl", "")
    views = article.get("knowledgearticleviews", 0)

    content_html = article.get("content", "")
    content_text = html_to_text(content_html)

    sep = "=" * 80
    dash = "-" * 40

    lines = [
        sep,
        f"KNOWLEDGE BASE ARTICLE — {article_id}",
        title,
        sep,
        "",
        f"Article ID       : {article_id}",
        f"Language          : {language}",
        f"Created           : {created}",
        f"Last Modified     : {modified}",
        f"Views             : {views}",
    ]

    if keywords:
        lines.append(f"Keywords          : {keywords}")
    if url:
        lines.append(f"Source URL         : {url}")
    if description:
        lines.append(f"Description       : {description}")

    lines += [
        "",
        sep,
        "CONTENT:",
        sep,
        "",
    ]

    # Wrap long lines for readability
    for paragraph in content_text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
        elif len(paragraph) > 100:
            lines.extend(textwrap.wrap(paragraph, width=80))
        else:
            lines.append(paragraph)

    lines += [
        "",
        sep,
    ]

    return "\n".join(lines) + "\n"


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "raw_data", "articles_en-us.json")
    output_dir = os.path.join(script_dir, "data")

    os.makedirs(output_dir, exist_ok=True)

    with open(json_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    generated = 0
    skipped = 0
    seen_filenames: dict[str, int] = {}

    for article in articles:
        title = article.get("title", "")
        content = article.get("content", "")
        if not title or not content:
            skipped += 1
            continue

        article_id = article.get("articlepublicnumber", "UNKNOWN")
        base_name = sanitize_filename(title)
        filename = f"KB_{article_id}_{base_name}.txt"

        # Handle duplicates
        if filename in seen_filenames:
            seen_filenames[filename] += 1
            filename = f"KB_{article_id}_{base_name}_{seen_filenames[filename]}.txt"
        else:
            seen_filenames[filename] = 1

        out_path = os.path.join(output_dir, filename)
        formatted = format_article(article)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(formatted)

        generated += 1

    print(f"Done. Generated {generated} files, skipped {skipped}.")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
