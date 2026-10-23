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
ACCENT_PRESETS = ("blue", "gold", "orange", "pink", "purple", "teal")
SERVICE_ANIMATIONS = ("group", "badge", "mark")
STARTUP_DEFAULTS = {"warm_start": False, "adaptive_splash": False, "launch_at_login": False}
PREPARABLE_SERVICES = ("graph",)  # Only services with a working Connections interface.


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
    _save_preferences({key: value}, directory)


def _save_preferences(updates: dict, directory: Path | None = None) -> bool:
    """Commit related preferences together and report persistence failures."""
    temporary_path = None
    try:
        folder = directory if directory is not None else get_config_dir(create=True)
        folder = ensure_private_directory(folder)
        target = folder / _PREFERENCES_FILENAME
        payload = _read_preferences(folder)
        payload.update(updates)
        descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=folder)
        temporary_path = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
        return True
    except OSError:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)
        return False


def load_appearance_preferences(*, directory: Path | None = None) -> dict:
    values = _read_preferences(directory).get("appearance", {})
    if not isinstance(values, dict):
        values = {}
    accent = values.get("accent")
    show_info = values.get("show_info_buttons")
    animation = values.get("service_animation")
    return {
        "accent": accent if accent in ACCENT_PRESETS else "blue",
        "show_info_buttons": show_info if type(show_info) is bool else True,
        "service_animation": animation if animation in SERVICE_ANIMATIONS else "group",
    }


def save_appearance_preferences(
    accent: str, show_info: bool, service_animation: str | None = None, *, directory=None
) -> bool:
    if accent not in ACCENT_PRESETS or type(show_info) is not bool:
        return False
    if service_animation is None:
        service_animation = load_appearance_preferences(directory=directory)["service_animation"]
    if service_animation not in SERVICE_ANIMATIONS:
        return False
    return _save_preferences(
        {
            "appearance": {
                "accent": accent,
                "show_info_buttons": show_info,
                "service_animation": service_animation,
            }
        },
        directory,
    )


def load_zoom_preference(*, directory: Path | None = None) -> int:
    """Default to 100% for missing, corrupt or unsupported saved zoom values."""
    value = _read_preferences(directory).get("connections_zoom_percent")
    return value if type(value) is int and 70 <= value <= 125 else 100


def save_zoom_preference(value: int, *, directory: Path | None = None) -> None:
    if type(value) is int and 70 <= value <= 125:
        _save_preference("connections_zoom_percent", value, directory)


def load_startup_preferences(*, directory: Path | None = None) -> dict:
    values = _read_preferences(directory).get("startup", {})
    if not isinstance(values, dict):
        values = {}
    return {
        key: values[key] if type(values.get(key)) is bool else default
        for key, default in STARTUP_DEFAULTS.items()
    }


def load_visited_services(*, directory=None):
    values = _read_preferences(directory).get("visited_services", [])
    if not isinstance(values, list):
        return []
    return [service for service in PREPARABLE_SERVICES if service in values]


def record_service_visit(service, *, directory=None):
    if service not in PREPARABLE_SERVICES:
        return False
    visited = load_visited_services(directory=directory)
    if service in visited:
        return True
    return _save_preferences({"visited_services": [*visited, service]}, directory)


def save_settings_preferences(accent, show_info, service_animation, startup, *, directory=None):
    """Save both settings tabs in one atomic preference-file replacement."""
    if (
        accent not in ACCENT_PRESETS
        or type(show_info) is not bool
        or service_animation not in SERVICE_ANIMATIONS
        or not isinstance(startup, dict)
        or set(startup) != set(STARTUP_DEFAULTS)
        or any(type(value) is not bool for value in startup.values())
    ):
        return False
    return _save_preferences(
        {
            "appearance": {
                "accent": accent,
                "show_info_buttons": show_info,
                "service_animation": service_animation,
            },
            "startup": dict(startup),
        },
        directory,
    )


__all__ = [
    "ThemeMode",
    "load_theme_preference",
    "save_theme_preference",
    "load_zoom_preference",
    "save_zoom_preference",
    "ACCENT_PRESETS",
    "SERVICE_ANIMATIONS",
    "load_appearance_preferences",
    "save_appearance_preferences",
    "STARTUP_DEFAULTS",
    "load_startup_preferences",
    "save_settings_preferences",
    "load_visited_services",
    "record_service_visit",
    "PREPARABLE_SERVICES",
]
