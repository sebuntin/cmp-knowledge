"""
MkDocs hook to convert Obsidian [[wikilinks]] to standard Markdown links.

Usage in mkdocs.yml:
  hooks:
    - hooks/wikilinks.py
"""
import os
import re

WIKILINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')

# Global link map: wikilink_target -> relative URL path (no leading /, no trailing /)
LINK_MAP = {}


def on_nav(nav, config, files):
    """Build the link map after nav is resolved."""
    global LINK_MAP
    LINK_MAP = {}
    for item in nav.items:
        _process_nav_item(item)
    return nav


def _process_nav_item(item):
    """Process a nav item recursively to build the wikilink -> URL map."""
    from mkdocs.structure.nav import Page, Section

    if isinstance(item, Page):
        if item.file:
            src_path = item.file.src_path
            # dest_path is like "wiki/concepts/rendering/融合渲染架构/index.html"
            dest = item.file.dest_path
            # Strip "wiki/" prefix and "/index.html" suffix to get URL path
            if dest.startswith("wiki/"):
                dest = dest[len("wiki/"):]
            if dest.endswith("/index.html"):
                dest = dest[:-len("/index.html")]
            elif dest.endswith(".html"):
                dest = dest[:-5]

            basename = os.path.splitext(os.path.basename(src_path))[0]
            LINK_MAP[basename] = dest

            # Register short name (without src-/analysis- prefix)
            if basename.startswith("src-"):
                LINK_MAP[basename[4:]] = dest
            elif basename.startswith("analysis-"):
                LINK_MAP[basename[9:]] = dest

    elif isinstance(item, Section):
        for child in item.children:
            _process_nav_item(child)


def on_page_markdown(markdown, page, config, files):
    """Convert [[wikilinks]] to [display](url) in markdown content."""
    if not LINK_MAP:
        return markdown

    def replace_wikilink(match):
        target = match.group(1).strip()
        display = match.group(2) or target

        url = LINK_MAP.get(target)

        # Fallback: try with prefixes
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

        # Compute relative path from current page to target
        current_src = page.file.src_path
        if current_src.startswith("wiki/"):
            current_src = current_src[len("wiki/"):]
        current_dir = os.path.dirname(current_src)

        if current_dir:
            parts = [".."] * current_dir.count("/") if current_dir else []
            rel = "/".join(parts) + "/" + url if parts else url
        else:
            rel = url

        return f'[{display}]({rel}/)'

    return WIKILINK_RE.sub(replace_wikilink, markdown)
