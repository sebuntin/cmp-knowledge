"""
MkDocs hook to convert Obsidian [[wikilinks]] to standard Markdown links.

Usage in mkdocs.yml:
  hooks:
    - hooks/wikilinks.py
"""
import os
import re

WIKILINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')

# Global link map: wikilink_target -> URL path (same namespace as dest_path minus suffix)
LINK_MAP = {}


def on_nav(nav, config, files):
    """Build the link map after nav is resolved."""
    global LINK_MAP
    LINK_MAP = {}
    for item in nav.items:
        _process_nav_item(item)
    return nav


def _dest_to_url(dest):
    """Convert MkDocs dest_path to URL path segment.

    dest_path: 'wiki/concepts/rendering/融合渲染架构/index.html'
    returns:   'wiki/concepts/rendering/融合渲染架构'
    """
    if dest.endswith("/index.html"):
        return dest[:-len("/index.html")]
    if dest.endswith(".html"):
        return dest[:-5]
    return dest


def _process_nav_item(item):
    from mkdocs.structure.nav import Page, Section

    if isinstance(item, Page):
        if item.file:
            url = _dest_to_url(item.file.dest_path)
            basename = os.path.splitext(os.path.basename(item.file.src_path))[0]

            LINK_MAP[basename] = url

            if basename.startswith("src-"):
                LINK_MAP[basename[4:]] = url
            elif basename.startswith("analysis-"):
                LINK_MAP[basename[9:]] = url

    elif isinstance(item, Section):
        for child in item.children:
            _process_nav_item(child)


def on_page_markdown(markdown, page, config, files):
    """Convert [[wikilinks]] to [display](url) in markdown content."""
    if not LINK_MAP:
        return markdown

    # Current page's full URL path (including page slug as directory)
    # e.g. 'wiki/concepts/rendering/融合渲染架构'
    current_url = _dest_to_url(page.file.dest_path)

    def replace_wikilink(match):
        target = match.group(1).strip()
        display = match.group(2) or target

        url = LINK_MAP.get(target)

        # Fallback: try with common prefixes
        if url is None:
            for prefix in ["src-", "analysis-",
                           "concepts/rendering/", "concepts/compose-basics/",
                           "concepts/platform/", "concepts/performance/",
                           "entities/", "sources/", "analysis/rendering/",
                           "analysis/platform/"]:
                candidate = prefix + target
                if candidate in LINK_MAP:
                    url = LINK_MAP[candidate]
                    break

        if url is None:
            return f'[{display}](#)'

        # os.path.relpath correctly handles all directory levels
        rel = os.path.relpath(url, current_url)

        return f'[{display}]({rel}/)'

    return WIKILINK_RE.sub(replace_wikilink, markdown)
