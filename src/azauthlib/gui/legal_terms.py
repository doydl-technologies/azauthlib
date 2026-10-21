# -*- coding: utf-8 -*-

#
# DOYDL's Microsoft Identity Authentication Library — azauthlib
#
# Copyright 2024 DOYDL Technologies.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Read bundled desktop policies; no HTTP or import-time I/O.

Bundled HTML stays unchanged; only the narrow native drawer presentation is
normalized. All loading uses package-relative resource paths.
"""

import logging
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit

POLICY_FILES = {
    "terms": "DESKTOP_APP_TERMS_OF_USE.html",
    "privacy": "DESKTOP_APP_PRIVACY_POLICY.html",
}
POLICY_TITLES = {"terms": "Terms of Use", "privacy": "Privacy Policy"}
MAX_BYTES = 2 * 1024 * 1024
_VOID = frozenset(
    (
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    )
)
_BLOCKED = frozenset(("script", "style", "iframe", "object", "svg", "math", "noscript", "template"))
_ALLOWED = frozenset(
    (
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "ul",
        "ol",
        "li",
        "br",
        "hr",
        "blockquote",
        "pre",
        "code",
        "a",
        "span",
    )
)


@dataclass
class _Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)


class _PolicyParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if len(self.stack) < 2 or self.stack[-1].tag != tag:
            raise ValueError("Malformed policy HTML")
        self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _nodes(node):
    yield node
    if node.tag not in _BLOCKED:
        for child in node.children:
            if isinstance(child, _Node):
                yield from _nodes(child)


def _plain(node):
    if isinstance(node, str):
        return node
    if node.tag in _BLOCKED:
        return ""
    return " ".join(_plain(child) for child in node.children)


def _safe_href(href):
    for topic, filename in POLICY_FILES.items():
        if href == filename:
            return "policy:" + topic
    parts = urlsplit(href)
    if parts.scheme == "https" and parts.hostname and not parts.username and not parts.password:
        return href
    if (
        parts.scheme == "mailto"
        and parts.path in ("privacy@doydl.studio", "legal@doydl.studio")
        and not parts.query
        and not parts.fragment
    ):
        return href
    return ""


def _children(node):
    return "".join(_render(child) for child in node.children)


def _table(node):
    """Stack labelled cells so no policy wording is clipped in a narrow shelf."""
    rows = [child for child in _nodes(node) if child.tag == "tr"]
    headers, output = [], []
    for caption in (child for child in _nodes(node) if child.tag == "caption"):
        output.append("<p><i>" + _children(caption) + "</i></p>")
    for row in rows:
        cells = [
            child
            for child in row.children
            if isinstance(child, _Node) and child.tag in ("th", "td")
        ]
        if not cells:
            continue
        if all(cell.attrs.get("scope") == "col" for cell in cells):
            headers = [_plain(cell).strip() for cell in cells]
            continue
        output.append("<h3>" + _children(cells[0]) + "</h3>")
        for index, cell in enumerate(cells[1:], 1):
            label = "<b>" + escape(headers[index]) + ":</b> " if index < len(headers) else ""
            output.append("<p>" + label + _children(cell) + "</p>")
    return "".join(output)


def _render(node):
    if isinstance(node, str):
        return escape(node)
    if node.tag in _BLOCKED:
        return ""
    if node.tag == "img":
        return escape(node.attrs.get("alt", ""))
    if node.tag == "table":
        return _table(node)
    if node.tag in ("article", "section", "div"):
        return "<div>" + _children(node) + "</div>"
    if node.tag not in _ALLOWED:
        return _children(node)
    attrs = ""
    if node.tag == "a":
        href = _safe_href(node.attrs.get("href", ""))
        if href:
            attrs = ' href="' + escape(href, quote=True) + '"'
    start = "<" + node.tag + attrs + ">"
    return start if node.tag in _VOID else start + _children(node) + "</" + node.tag + ">"


def prepare_document(source, topic):
    """Complete policy plus version/date, without the standalone page's TOC."""
    if topic not in POLICY_FILES:
        raise ValueError("Unknown policy")
    parser = _PolicyParser()
    parser.feed(source)
    parser.close()
    if len(parser.stack) != 1:
        raise ValueError("Incomplete policy HTML")
    nodes = list(_nodes(parser.root))
    articles = [node for node in nodes if node.tag == "article" and node.attrs.get("id") == topic]
    if len(articles) != 1 or len(" ".join(_plain(articles[0]).split())) < 80:
        raise ValueError("Missing or empty policy article")
    metadata = [node for node in nodes if node.attrs.get("id") == "policy-metadata"]
    if len(metadata) > 1:
        raise ValueError("Duplicate policy metadata")
    return (
        "<h1>"
        + POLICY_TITLES[topic]
        + "</h1>"
        + "".join(_render(node) for node in metadata)
        + _render(articles[0])
    )


def prepare_articles(source):
    """Prepare valid articles independently, also for local interface previews."""
    documents = {}
    for topic in POLICY_FILES:
        try:
            documents[topic] = prepare_document(source, topic)
        except ValueError:
            continue
    return documents


def unavailable_document(topic):
    return (
        "<h1>" + POLICY_TITLES[topic] + " unavailable</h1><p>The bundled desktop policy "
        "could not be loaded or displayed. Reinstall azauthlib to restore its legal "
        'documents, or contact <a href="mailto:legal@doydl.studio">legal@doydl.studio</a>. '
        "No website policy has been substituted.</p>"
    )


def load_legal_documents(resources):
    """Local reads only; a failed policy gets an independent offline notice."""
    documents, urls = {}, {}
    for topic, filename in POLICY_FILES.items():
        try:
            path = resources.path("assets", "docs", "legal", filename)
            with path.open("rb") as stream:
                data = stream.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("Oversized policy HTML")
            documents[topic] = prepare_document(data.decode("utf-8"), topic)
            urls[topic] = path.resolve().as_uri()
        except (OSError, ValueError, UnicodeError, RecursionError):
            logging.getLogger(__name__).warning("Bundled %s policy unavailable", topic)
            documents[topic] = unavailable_document(topic)
    return {"documents": documents, "urls": urls}
