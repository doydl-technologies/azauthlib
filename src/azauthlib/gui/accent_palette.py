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

"""Color-family translation for decorative UI colors, never brand/status artwork.

OKLCH keeps the reference lightness and relative chroma, so a pale reflection,
dark bevel and saturated glow remain different shades. Gamut mapping reduces
chroma instead of clipping RGB channels. Alpha, geometry and timing are untouched.
"""

from __future__ import annotations

import colorsys
import math
import re
from functools import lru_cache

from PySide6.QtCore import Property, QObject, Signal, Slot

FAMILY_ACCENTS = {
    "blue": "#38a8ff",
    "gold": "#f4c542",
    "orange": "#ff963f",
    "pink": "#ec65ad",
    "purple": "#ad78f5",
    "teal": "#2dd4bf",
}
_HEX = re.compile(r"#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")


def _linear(value):
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _oklch(rgb):
    r, g, b = map(_linear, rgb)
    l_root = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    lightness = 0.2104542553 * l_root + 0.7936177850 * m - 0.0040720468 * s
    a = 1.9779984951 * l_root - 2.4285922050 * m + 0.4505937099 * s
    b = 0.0259040371 * l_root + 0.7827717662 * m - 0.8086757660 * s
    return lightness, math.hypot(a, b), math.atan2(b, a)


def _rgb(lightness, chroma, hue):
    a, b = chroma * math.cos(hue), chroma * math.sin(hue)
    l_linear = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        4.0767416621 * l_linear - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l_linear + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l_linear - 0.7034186147 * m + 1.7076147010 * s,
    )


def _parse(value):
    value = value.lower()
    if not _HEX.fullmatch(value):
        return None
    if len(value) == 4:
        value = "#" + "".join(c * 2 for c in value[1:])
    alpha = value[1:3] if len(value) == 9 else ""
    rgb = value[-6:]
    return alpha, tuple(int(rgb[i : i + 2], 16) / 255 for i in (0, 2, 4))


@lru_cache(maxsize=8192)
def family_color(reference: str, family: str) -> str:
    """Map an explicitly themeable blue reference, preserving Qt #AARRGGBB."""
    parsed = _parse(reference)
    if family not in FAMILY_ACCENTS or family == "blue" or parsed is None:
        return reference
    alpha, rgb = parsed
    hue, saturation, _ = colorsys.rgb_to_hsv(*rgb)
    # Leave neutrals, black shadows, red/green/amber statuses and non-blue art.
    if not 178 <= hue * 360 <= 270 or saturation < 0.035:
        return reference
    lightness, chroma, old_hue = _oklch(rgb)
    if lightness < 0.24:
        return reference
    _, base_chroma, base_hue = _oklch(_parse(FAMILY_ACCENTS["blue"])[1])
    _, target_chroma, target_hue = _oklch(_parse(FAMILY_ACCENTS[family])[1])
    hue_offset = math.atan2(math.sin(old_hue - base_hue), math.cos(old_hue - base_hue))
    # Related blue/cyan variants become related shades inside the new family,
    # not a rainbow spanning neighboring families.
    target_hue += max(-0.22, min(0.22, hue_offset * 0.22))
    chroma *= target_chroma / base_chroma
    low, high = 0.0, chroma
    for _ in range(18):
        candidate = (low + high) / 2
        values = _rgb(lightness, candidate, target_hue)
        if min(values) >= 0 and max(values) <= 1:
            low = candidate
        else:
            high = candidate
    values = _rgb(lightness, low, target_hue)
    encoded = [12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055 for v in values]
    return "#" + alpha + "".join(f"{max(0, min(255, round(v * 255))):02x}" for v in encoded)


def theme_svg(source: str, family: str, *, shield=False) -> str:
    """Change colors in memory only; preserve every SVG filter/gradient/opacity.

    The splash brand mark exposes three decorative glow/rim elements. Its
    inner logo, Python colors and token keep their original brand colors.
    """
    if family == "blue":
        return source

    def replace_color(match):
        value = match[0]
        if len(value) == 9:
            # CSS SVG colors are #RRGGBBAA; Qt colors are #AARRGGBB.
            translated = family_color("#" + value[-2:] + value[1:7], family)
            return "#" + translated[3:] + translated[1:3]
        return family_color(value, family)

    if shield:
        return re.sub(
            r'<use\b[^>]*\bid="(?:wide-blue-glow|near-cyan-glow|bright-shield-rim)"[^>]*/>',
            lambda element: _HEX.sub(replace_color, element[0]),
            source,
        )
    return _HEX.sub(replace_color, source)


class AccentPalette(QObject):
    """Available before the first splash frame; no profile, keyring, or network I/O."""

    initialAccentChanged = Signal()

    def __init__(self, family="blue", parent=None):
        super().__init__(parent)
        self._initial = family if family in FAMILY_ACCENTS else "blue"

    @Property(str, notify=initialAccentChanged)
    def initialAccent(self):
        return self._initial

    def set_initial(self, family):
        family = family if family in FAMILY_ACCENTS else "blue"
        if family != self._initial:
            self._initial = family
            self.initialAccentChanged.emit()

    @Slot(str, str, result=str)
    def colorFor(self, reference, family):
        return family_color(reference, family)
