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

"""Render bundled logos, avatars, and compatible action SVGs with resvg.

resvg preserves curves, gradients, masks, clipping, and filters that Qt's SVG
decoder does not fully support. Only display textures are rasterized; source
files remain unchanged. Color translation is restricted to allowlisted
application decoration.
"""

from __future__ import annotations

import logging
import re
from collections import OrderedDict
from threading import Lock
from urllib.parse import unquote

import resvg_py
from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtQuick import QQuickImageProvider

from ..profile_avatars import AVATAR_ASSET_PARTS, profile_avatar_names
from .accent_palette import FAMILY_ACCENTS, family_color, theme_svg

PROVIDER_LOGO_PATHS = {
    "logo-microsoft-graph-symbol.svg": ("logo", "svg", "third-party"),
    "subscriptions.svg": ("icons", "svg", "third-party", "profile-avatar"),
    "logo-microsoft-dataverse.svg": ("logo", "svg", "third-party"),
    "storage-accounts.svg": ("icons", "svg", "third-party", "profile-avatar"),
    "sql-database.svg": ("icons", "svg", "third-party", "profile-avatar"),
    "logo-microsoft-exchange.svg": ("logo", "svg", "third-party"),
}
PROVIDER_LOGOS = tuple(PROVIDER_LOGO_PATHS)
ACTION_ICON_PATHS = {
    name: ("icons", "svg", "actions")
    for name in (
        "Monocolor-Filled-Sky-Blue-circle-plus.svg",
        "edit-utensil.svg",
        "Monocolor-Outlined-Pink-Red-trash.svg",
        "Multicolor-Filled-Mint-Green-Transparent-circle-check.svg",
        "Monocolor-Rounded-Filled-Light-Gray-Radio-Button-Checked.svg",
        "accessibility.svg",
        "paint-brush-solid.svg",
        "settings-gear.svg",
        "settings-horizontal.svg",
        "power-reset.svg",
        "save.svg",
    )
}
SETTINGS_ICON_PATHS = {
    f"settings-gear-{state}.svg": ("icons", "svg", "actions", "relief")
    for state in ("raised", "hover", "sunken")
}
ACTION_ICON_PATHS.update(SETTINGS_ICON_PATHS)
ACCENT_ART_PATHS = {
    **SETTINGS_ICON_PATHS,
    "azauthlib-mark-glow-border.svg": ("logo", "svg"),
    "glowing-blue-divider.svg": ("controls",),
    "surface-head-icon--raised-circle.png": ("controls",),
    "surface-head-icon--sunken-circle.png": ("controls",),
    **{
        f"{prefix}-{state}.svg": ("icons", "svg", "actions", "relief", "shortcuts")
        for prefix in (
            "Monocolor-Filled-Blue-shortcuts-win",
            "Monocolor-Filled-Blue-Pink-shortcuts-ios",
            "Monocolor-Filled-Purple-shortcuts-linux",
        )
        for state in ("raised", "raised-Blue-highlight-ring", "sunken")
    },
    **{f"Multicolor-blue-white-podcast-line-{index}.svg": ("animate",) for index in range(4)},
}
# Only application decoration is allowlisted. Vendor logos, custom profile
# avatars, status/result badges and the supplied multicolor test plug are not.
for _directory, _names in {
    "plugs/general": ("Monocolor-Filled-Sky-Blue-Single-Plug.svg",),
    "actions": (
        "Monocolor-Filled-Sky-Blue-circle-plus.svg",
        "Monocolor-Filled-Ice-Blue-check.svg",
        "Monocolor-Filled-Sky-Blue-check.svg",
        "Monocolor-Filled-Ice-Blue-thumbs-up-hand.svg",
        "Monocolor-Filled-Ice-Blue-close.svg",
        "Monocolor-Filled-Ice-Blue-Copy.svg",
    ),
    "navigation": (
        "Monocolor-Filled-Sky-Blue-chevron-right.svg",
        "Monocolor-Filled-Dusty-Blue-chevron-down.svg",
    ),
    "security": ("Monocolor-Filled-Dusty-Blue-padlock.svg",),
    "status/information-alerts": (
        "Monocolor-Filled-Sky-Blue-info.svg",
        "Monocolor-Filled-Sky-Blue-info-borderless.svg",
    ),
    "interaction": (
        "Monocolor-Filled-Dusty-Blue-eye.svg",
        "Monocolor-Filled-Dusty-Blue-eye-off.svg",
        "avatar-loading.svg",
    ),
    "technology": ("Monocolor-Filled-Ice-Blue-internet.svg",),
}.items():
    ACCENT_ART_PATHS.update({name: ("icons", "svg", *_directory.split("/")) for name in _names})
_LOGGER = logging.getLogger(__name__)
_DEFAULT_EDGE = 384
_MAX_EDGE = 1536
_CACHE_LIMIT = 12
_AVATAR_PREVIEW_EDGE = 128
# At most 48 MiB of RGBA thumbnails, independent of Qt's evictable image cache.
_AVATAR_PREVIEW_LIMIT = 768


class ProviderLogoImageProvider(QQuickImageProvider):
    """Restricted provider SVGs, with an optional disposable warm-start raster cache."""

    def __init__(
        self, resources, *, paths=None, cache_limit=_CACHE_LIMIT, warm_start=False
    ) -> None:
        super().__init__(QQuickImageProvider.Image)
        # Materialize package paths on the loading thread. Requests may arrive
        # on Qt's image-loading worker, so they never manipulate ExitStack.
        self._paths = {
            name: resources.path("assets", *directory, name)
            for name, directory in (PROVIDER_LOGO_PATHS if paths is None else paths).items()
        }
        self._cache_limit = cache_limit
        self._warm_start = warm_start
        self._cache: OrderedDict[tuple, QImage] = OrderedDict()
        self._lock = Lock()

    def configure_warm_start(self, enabled):
        """Snapshot already-rendered logos for background persistence, without re-rendering."""
        with self._lock:
            self._warm_start = enabled
            return [(self._paths[key[0]], key, image) for key, image in self._cache.items()]

    def requestImage(self, image_id: str, size: QSize, requestedSize: QSize) -> QImage:
        name = unquote(image_id)
        if name not in self._paths:
            return QImage()  # Never open arbitrary paths, URLs, or compatibility copies.
        width = min(_MAX_EDGE, max(1, requestedSize.width() or _DEFAULT_EDGE))
        height = min(_MAX_EDGE, max(1, requestedSize.height() or width))
        if requestedSize.width() < 1:
            width = _DEFAULT_EDGE
        if requestedSize.height() < 1:
            height = width
        path = self._paths[name]
        try:
            stamp = path.stat()
            key = (name, width, height, stamp.st_mtime_ns, stamp.st_size)
            with self._lock:
                image = self._cache.get(key)
                if image is None:
                    image = None
                    if self._warm_start:
                        from .startup_cache import load_service_image

                        image = load_service_image(path, key, width, height)
                    if image is None:
                        image = self._render(path, width, height)
                        if self._warm_start:
                            from .startup_cache import save_service_image

                            save_service_image(path, key, image)
                    self._cache[key] = image
                    while len(self._cache) > self._cache_limit:
                        self._cache.popitem(last=False)
                self._cache.move_to_end(key)
            if size is not None:
                size.setWidth(image.width())
                size.setHeight(image.height())
            return image
        except (OSError, ValueError, RuntimeError):
            _LOGGER.exception("Unable to render bundled SVG %s", name)
            return QImage()

    @staticmethod
    def _render(path, width: int, height: int, *, svg_string=None) -> QImage:
        def render(**dimensions):
            return QImage.fromData(
                resvg_py.svg_to_bytes(
                    svg_path=str(path) if svg_string is None else None,
                    svg_string=svg_string,
                    skip_system_fonts=True,
                    shape_rendering="geometric_precision",
                    image_rendering="optimize_quality",
                    **dimensions,
                )
            )

        artwork = render(width=width)
        if artwork.height() > height:
            artwork = render(height=height)
        if artwork.isNull():
            raise ValueError("The SVG renderer returned an empty image")
        # Contain the complete SVG viewport, just like HTML object-fit: contain.
        # Do not stretch non-square viewBoxes or crop masks/filter extents.
        canvas = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        painter.drawImage(
            QPoint((width - artwork.width()) // 2, (height - artwork.height()) // 2), artwork
        )
        painter.end()
        return canvas


class ActionIconImageProvider(ProviderLogoImageProvider):
    """Render toolbar SVGs, including their saved CSS variables/masks."""

    def __init__(self, resources) -> None:
        super().__init__(resources, paths=ACTION_ICON_PATHS, cache_limit=24)
        # The footer swaps a single texture, without crossfading or overlapping
        # images. Warm its exact display resolution before the UI is revealed.
        for name in SETTINGS_ICON_PATHS:
            self.requestImage(name, QSize(), QSize(192, 192))

    @staticmethod
    def _render(path, width: int, height: int) -> QImage:
        source = path.read_text(encoding="utf-8")
        # These allowlisted assets define static variables on their SVG root.
        # Resolve only those declarations in memory: neither Qt nor resvg
        # supports var(), but resvg preserves the remaining CSS and cutout mask.
        variables = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", source))
        source = re.sub(
            r"var\(\s*(--[\w-]+)\s*\)",
            lambda match: variables.get(match[1], match[0]),
            source,
        )
        return ProviderLogoImageProvider._render(path, width, height, svg_string=source)


class AccentArtImageProvider(ProviderLogoImageProvider):
    """Bounded, family-keyed render cache; original SVG files are never edited."""

    def __init__(self, resources):
        super().__init__(resources, paths=ACCENT_ART_PATHS, cache_limit=96)
        self._cached_bytes = 0

    @staticmethod
    def _raster(path, width, height, family):
        # Only the two tiny, allowlisted help-button bezels are raster-themed.
        # The splash photograph/overlay and all logo bitmaps are never touched.
        image = QImage(str(path)).convertToFormat(QImage.Format_ARGB32)
        if image.isNull():
            raise ValueError("Unable to read the help-button bezel")
        if family != "blue":
            for y in range(image.height()):
                for x in range(image.width()):
                    original = image.pixelColor(x, y)
                    if original.alpha():
                        color = QColor(family_color(original.name(), family))
                        color.setAlpha(original.alpha())
                        image.setPixelColor(x, y, color)
        image = image.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        canvas = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        painter.drawImage(
            QPoint((width - image.width()) // 2, (height - image.height()) // 2), image
        )
        painter.end()
        return canvas

    def requestImage(self, image_id, size, requestedSize):
        parts = unquote(image_id).split("/", 1)
        if len(parts) != 2 or parts[0] not in FAMILY_ACCENTS or parts[1] not in self._paths:
            return QImage()
        family, name = parts
        width = min(_MAX_EDGE, max(1, requestedSize.width() or _DEFAULT_EDGE))
        height = min(_MAX_EDGE, max(1, requestedSize.height() or width))
        if requestedSize.width() < 1:
            width = _DEFAULT_EDGE
        if requestedSize.height() < 1:
            height = width
        path = self._paths[name]
        try:
            stamp = path.stat()
            key = (family, name, width, height, stamp.st_mtime_ns, stamp.st_size)
            with self._lock:
                image = self._cache.get(key)
                if image is None:
                    if path.suffix == ".png":
                        image = self._raster(path, width, height, family)
                    else:
                        source = path.read_text(encoding="utf-8")
                        variables = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", source))
                        source = re.sub(
                            r"var\(\s*(--[\w-]+)\s*\)",
                            lambda match: variables.get(match[1], match[0]),
                            source,
                        )
                        source = theme_svg(
                            source, family, shield=name == "azauthlib-mark-glow-border.svg"
                        )
                        image = ProviderLogoImageProvider._render(
                            path, width, height, svg_string=source
                        )
                    self._cache[key] = image
                    self._cached_bytes += image.sizeInBytes()
                    while len(self._cache) > self._cache_limit or (
                        self._cached_bytes > 32 * 1024 * 1024 and len(self._cache) > 1
                    ):
                        _, expired = self._cache.popitem(last=False)
                        self._cached_bytes -= expired.sizeInBytes()
                self._cache.move_to_end(key)
            if size is not None:
                size.setWidth(image.width())
                size.setHeight(image.height())
            return image
        except (OSError, ValueError, RuntimeError):
            _LOGGER.exception("Unable to render themed SVG %s", name)
            return QImage()


def ensure_accent_theme(engine, resources, family=None):
    """Register the small startup-safe palette/art provider before loading QML."""
    from .accent_palette import AccentPalette
    from .theme import load_appearance_preferences

    palette = getattr(engine, "_azauthlib_accent_palette", None)
    if palette is None:
        initial = family if family is not None else load_appearance_preferences()["accent"]
        palette = AccentPalette(initial, engine)
        engine._azauthlib_accent_palette = palette
        engine.rootContext().setContextProperty("accentPalette", palette)
    elif family is not None:
        palette.set_initial(family)
    if engine.imageProvider("accentart") is None:
        engine.addImageProvider("accentart", AccentArtImageProvider(resources))
    return palette


class ProfileAvatarImageProvider(ProviderLogoImageProvider):
    """Reuse the SVG renderer/cache for allowed bundled avatars, in original colors."""

    def __init__(self, resources) -> None:
        super().__init__(
            resources,
            paths={name: AVATAR_ASSET_PARTS for name in profile_avatar_names()},
            cache_limit=96,
        )
        self._previews: OrderedDict[str, QImage] = OrderedDict()

    def preload(self, report=lambda *_: None, cancelled=lambda: False) -> int:
        """Warm thumbnails on the startup worker, with cancellation between SVGs.

        Corrupt optional artwork stays a placeholder, never a startup failure.
        """
        names = tuple(self._paths)[:_AVATAR_PREVIEW_LIMIT]
        loaded = 0
        for index, name in enumerate(names):
            if cancelled():
                break
            image = self.requestImage(
                name, QSize(), QSize(_AVATAR_PREVIEW_EDGE, _AVATAR_PREVIEW_EDGE)
            )
            loaded += not image.isNull()
            if (index + 1) % 24 == 0 or index + 1 == len(names):
                report(index + 1, len(names))
        return loaded

    def requestImage(self, image_id: str, size: QSize, requestedSize: QSize) -> QImage:
        name = unquote(image_id)
        width, height = requestedSize.width(), requestedSize.height()
        if name not in self._paths or not (
            0 < width <= _AVATAR_PREVIEW_EDGE and 0 < height <= _AVATAR_PREVIEW_EDGE
        ):
            return super().requestImage(image_id, size, requestedSize)
        with self._lock:
            preview = self._previews.get(name)
            if preview is None:
                try:
                    preview = self._render(
                        self._paths[name], _AVATAR_PREVIEW_EDGE, _AVATAR_PREVIEW_EDGE
                    )
                except (OSError, ValueError, RuntimeError):
                    _LOGGER.warning("Unable to prepare bundled avatar %s", name)
                    return QImage()
                self._previews[name] = preview
                while len(self._previews) > _AVATAR_PREVIEW_LIMIT:
                    self._previews.popitem(last=False)
            self._previews.move_to_end(name)
        image = (
            preview
            if width == height == _AVATAR_PREVIEW_EDGE
            else preview.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        )
        if size is not None:
            size.setWidth(image.width())
            size.setHeight(image.height())
        return image


def ensure_image_providers(
    engine, resources, *, include_avatars=True
) -> ProfileAvatarImageProvider | None:
    """Register on the GUI thread; startup warms this same provider instance."""
    ensure_accent_theme(engine, resources)
    if engine.imageProvider("providerlogos") is None:
        from .theme import load_startup_preferences

        engine.addImageProvider(
            "providerlogos",
            ProviderLogoImageProvider(
                resources, warm_start=load_startup_preferences()["warm_start"]
            ),
        )
    if include_avatars and engine.imageProvider("profileavatars") is None:
        engine.addImageProvider("profileavatars", ProfileAvatarImageProvider(resources))
    if engine.imageProvider("actionicons") is None:
        engine.addImageProvider("actionicons", ActionIconImageProvider(resources))
    if engine.imageProvider("connectionanimation") is None:
        from .connection_animation import ConnectionAnimationImageProvider

        engine.addImageProvider("connectionanimation", ConnectionAnimationImageProvider(resources))
    return engine.imageProvider("profileavatars")
