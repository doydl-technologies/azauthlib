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

"""Render bundled provider SVGs with supersampling and resvg.

resvg preserves the logos' curves, gradients, masks, clipping, and filters
that Qt's SVG decoder does not fully support. Only the display texture is
rasterized; the source artwork and its colors remain unchanged.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from threading import Lock
from urllib.parse import unquote

import resvg_py
from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtQuick import QQuickImageProvider

PROVIDER_LOGOS = (
    "logo-microsoft-graph-symbol.svg",
    "icon-azure-key-vault.svg",
    "logo-microsoft-dataverse.svg",
    "icon-azure-storage-account.svg",
    "icon-azure-sql-database.svg",
    "logo-microsoft-exchange.svg",
)
_LOGGER = logging.getLogger(__name__)
_DEFAULT_EDGE = 384
_MAX_EDGE = 1536
_CACHE_LIMIT = 12


class ProviderLogoImageProvider(QQuickImageProvider):
    """Restricted, memory-only image provider for the six bundled provider SVGs."""

    def __init__(self, resources) -> None:
        super().__init__(QQuickImageProvider.Image)
        # Materialize package paths on the loading thread. Requests may arrive
        # on Qt's image-loading worker, so they never manipulate ExitStack.
        self._paths = {
            name: resources.path("assets", "logo", "third-party", name) for name in PROVIDER_LOGOS
        }
        self._cache: OrderedDict[tuple, QImage] = OrderedDict()
        self._lock = Lock()

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
                    image = self._render(path, width, height)
                    self._cache[key] = image
                    while len(self._cache) > _CACHE_LIMIT:
                        self._cache.popitem(last=False)
                self._cache.move_to_end(key)
            if size is not None:
                size.setWidth(image.width())
                size.setHeight(image.height())
            return image
        except (OSError, ValueError, RuntimeError):
            _LOGGER.exception("Unable to render bundled provider logo %s", name)
            return QImage()

    @staticmethod
    def _render(path, width: int, height: int) -> QImage:
        def render(**dimensions):
            return QImage.fromData(
                resvg_py.svg_to_bytes(
                    svg_path=str(path),
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
