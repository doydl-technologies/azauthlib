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

"""Restricted, cached SVG layers for the native new-connection animation."""

from __future__ import annotations

import logging
from collections import OrderedDict
from threading import Lock
from urllib.parse import unquote
from xml.etree import ElementTree as ET  # nosec B405 # Bundled UTF-8 SVGs; DTD/entities rejected.

from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider

from .accent_palette import FAMILY_ACCENTS, theme_svg
from .svg_images import ProviderLogoImageProvider

_LOGGER = logging.getLogger(__name__)
_SVG = "{http://www.w3.org/2000/svg}"
ET.register_namespace("", _SVG[1:-1])

# Common framing retains the white disc, shadows, masks and original colors.
CIRCULAR_VIEWBOX = (0, 0, 1254, 1254)
# White circular artwork is grouped by variant, with poses separate from
# rotating-outline frames. Provider URLs remain stable for QML callers.
CIRCULAR_FILES = {
    ("white-circle", pose): f"white-circular/poses/{filename}"
    for pose, filename in {
        "disconnected": "01-disconnected.svg",
        "connected": "02-connected.svg",
        "glow": "03-connected-glow.svg",
        "outer": "04-connected-outer-glow.svg",
    }.items()
}
CIRCULAR_FILES.update(
    {
        ("white-circle", f"spin-{frame:02d}"): f"white-circular/outline-spin/{frame:02d}.svg"
        for frame in range(1, 17)
    }
)
_PARTS = {
    # Use the final artwork's static geometry from the very first frame. Only
    # translate its complete plug assembly; never blend two different shells.
    "socket": ("outer", "wall-outlet"),
    "slots": ("disconnected", "socket-slots"),
    "pins": ("disconnected", "plug-pins"),
    "plug": ("outer", "plug-assembly"),
    "lip": ("outer", "socket-front-lip"),
    "badge-base": ("outer", "add-badge"),
    "badge-plus": ("connected", "plus"),
    "glow-plus": ("glow", "add-badge"),
    "outer-aura": ("outer", "cyan-badge-glow"),
    "outer-edge": ("outer", "badge-cyan-edge"),
    "disconnected": ("disconnected", None),
    "connected": ("connected", None),
    "glow": ("glow", None),
    "outer": ("outer", None),
    "surface": ("outer", "circular-surface"),
    "surface-aura": ("outer", "cyan-disc-glow"),
    "surface-edge": ("outer", "disc-cyan-edge"),
}
_PARTS.update(
    {f"spin-{frame:02d}": (f"spin-{frame:02d}", "rim-rotating-shine") for frame in range(1, 17)}
)


def animation_svg(path, part, viewbox=CIRCULAR_VIEWBOX):
    """Extract a layer in memory; never edit or generate replacement SVG files."""
    _, group_id = _PARTS[part]
    source = path.read_text(encoding="utf-8-sig")
    if "<!DOCTYPE" in source.upper() or "<!ENTITY" in source.upper():
        raise ValueError("Animation artwork cannot contain DTDs/entities")
    root = ET.fromstring(source)  # nosec B314 # noqa: S314 -- bundled UTF-8 SVGs; DTD/entities rejected
    if group_id:
        group = root.find(f".//*[@id='{group_id}']")
        if group is None:
            raise ValueError(f"Missing animation group: {group_id}")
        # A part's own transform is not its complete coordinate system. Keep
        # its ancestor chain (without siblings), including centering transforms
        # and inherited styling/clips, so it matches the final whole SVG.
        parents = {child: parent for parent in root.iter() for child in parent}
        ancestors = []
        parent = parents.get(group)
        while parent is not None and parent is not root:
            ancestors.append(parent)
            parent = parents.get(parent)
        # Keep every definition: extracted shapes still reference the original
        # filter/gradient/mask/clip IDs, including nested user-space transforms.
        for child in list(root):
            if child.tag not in (_SVG + "defs", _SVG + "title", _SVG + "desc"):
                root.remove(child)
        isolated = group
        for ancestor in ancestors:
            wrapper = ET.Element(ancestor.tag, dict(ancestor.attrib))
            wrapper.append(isolated)
            isolated = wrapper
        root.append(isolated)
        excluded = {
            "socket": {"socket-slots"},
            "plug": {"plug-pins"},
            "surface": {"cyan-disc-glow", "disc-cyan-edge", "rim-rotating-shine"},
        }.get(part, set())
        for parent in group.iter():
            for child in list(parent):
                if child.get("id") in excluded:
                    parent.remove(child)
        if part == "badge-base":
            # Keep only the raised disc. Its plus, halos and cyan edge are
            # separate layers so the disc never changes opacity or size.
            for child in list(group):
                if child.get("filter") != "url(#raised-shadow)":
                    group.remove(child)
        elif part == "glow-plus":
            for child in list(group):
                name = child.get("id", "")
                if name != "plus" and not name.startswith("plus-neon-"):
                    group.remove(child)
    x, y, width, height = viewbox
    root.set("viewBox", f"{x} {y} {width} {height}")
    root.set("width", str(width))
    root.set("height", str(height))
    return ET.tostring(root, encoding="unicode")


class ConnectionAnimationImageProvider(QQuickImageProvider):
    """Static layer textures only; all movement/glow timing stays in QML."""

    def __init__(self, resources):
        super().__init__(QQuickImageProvider.Image)
        self._paths = {
            key: resources.path("assets", "animate", "plugs", "connection", *filename.split("/"))
            for key, filename in CIRCULAR_FILES.items()
        }
        self._cache = OrderedDict()
        self._cached_bytes = 0
        self._lock = Lock()

    def requestImage(self, image_id, size, requestedSize):
        parts = unquote(image_id).split("/")
        if len(parts) not in (2, 3) or parts[1] not in _PARTS:
            return QImage()
        color, part = parts[:2]
        family = parts[2] if len(parts) == 3 else "blue"
        if family not in FAMILY_ACCENTS:
            return QImage()
        path = self._paths.get((color, _PARTS[part][0]))
        if path is None:
            return QImage()
        width = max(1, requestedSize.width() if requestedSize.width() > 0 else 540)
        height = max(1, requestedSize.height() if requestedSize.height() > 0 else 384)
        contain = min(1, 1024 / max(width, height))
        width, height = max(1, round(width * contain)), max(1, round(height * contain))
        try:
            stamp = path.stat()
            key = (color, part, family, width, height, stamp.st_mtime_ns, stamp.st_size)
            with self._lock:
                image = self._cache.get(key)
                if image is None:
                    image = ProviderLogoImageProvider._render(
                        path,
                        width,
                        height,
                        svg_string=theme_svg(animation_svg(path, part), family),
                    )
                    self._cache[key] = image
                    self._cached_bytes += image.sizeInBytes()
                    while self._cached_bytes > 24 * 1024 * 1024 and len(self._cache) > 1:
                        _, expired = self._cache.popitem(last=False)
                        self._cached_bytes -= expired.sizeInBytes()
                self._cache.move_to_end(key)
            if size is not None:
                size.setWidth(image.width())
                size.setHeight(image.height())
            return image
        except (OSError, ValueError, RuntimeError, ET.ParseError):
            _LOGGER.warning("Unable to render connection animation %s/%s", color, part)
            return QImage()
