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

"""Persist non-sensitive display preferences separately from connection credentials."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Literal

from ..appdata import ensure_private_directory, get_config_dir

ThemeMode = Literal["light", "dark"]

_PREFERENCES_FILENAME = "ui_preferences.json"
_THEMES: tuple[ThemeMode, ...] = ("light", "dark")


def _read_preferences(directory: Path | None = None) -> dict:
    try:
        folder = directory if directory is not None else get_config_dir(create=False)
        path = folder / _PREFERENCES_FILENAME
        if path.stat().st_size > 65_536:
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, UnicodeError, ValueError, RecursionError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_theme_preference() -> ThemeMode:
    """Load the saved theme, defaulting safely when the preference is unavailable."""
    mode = _read_preferences().get("theme")
    return mode if mode in _THEMES else "light"


def save_theme_preference(mode: ThemeMode) -> None:
    """Persist only the non-sensitive visual theme preference."""

    if mode not in _THEMES:
        return
    _save_preference("theme", mode)


def _save_preference(key: str, value, directory: Path | None = None) -> None:
    """Merge visual settings, then atomically replace just the preference file."""
    temporary_path = None
    try:
        folder = directory if directory is not None else get_config_dir(create=True)
        folder = ensure_private_directory(folder)
        target = folder / _PREFERENCES_FILENAME
        payload = _read_preferences(folder)
        payload[key] = value
        descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=folder)
        temporary_path = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
    except OSError:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)


def load_zoom_preference(*, directory: Path | None = None) -> int:
    """Default to 100% for missing, corrupt or unsupported saved zoom values."""
    value = _read_preferences(directory).get("connections_zoom_percent")
    return value if type(value) is int and 70 <= value <= 125 else 100


def save_zoom_preference(value: int, *, directory: Path | None = None) -> None:
    if type(value) is int and 70 <= value <= 125:
        _save_preference("connections_zoom_percent", value, directory)


__all__ = [
    "ThemeMode",
    "load_theme_preference",
    "save_theme_preference",
    "load_zoom_preference",
    "save_zoom_preference",
]
