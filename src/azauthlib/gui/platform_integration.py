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

"""Optional native integration behind one platform-neutral GUI boundary.

Qt supplies the shared windows/icons. Windows-only backends are never imported
on macOS or Linux, and no platform-specific API runs just by importing this file.
"""

from __future__ import annotations

import sys

_SYSTEM = sys.platform


def _windows_backend():
    if _SYSTEM != "win32":
        return None
    from . import windows_native

    return windows_native


def set_app_id(app_id: str) -> None:
    backend = _windows_backend()
    if backend is not None:
        backend.set_app_id(app_id)


def allow_foreground_activation(process_id: int) -> None:
    backend = _windows_backend()
    if backend is not None:
        backend.allow_foreground_activation(process_id)


def activate_window(window) -> None:
    backend = _windows_backend()
    if backend is not None:
        backend.activate_window(window)


def apply_title_bar(window, *, dark: bool) -> None:
    backend = _windows_backend()
    if backend is not None:
        backend.apply_title_bar(window, dark=dark)


def disable_maximizing(window) -> None:
    backend = _windows_backend()
    if backend is not None:
        backend.disable_maximizing(window)


def apply_titlebar_icon(window, icon_path) -> int | None:
    backend = _windows_backend()
    if backend is not None:
        return backend.apply_titlebar_icon(window, icon_path)
    return None


def apply_window_identity(window, *, app_id, title, icon_path) -> None:
    if _SYSTEM != "win32":
        return
    from .windows_taskbar import apply_window_taskbar_identity

    apply_window_taskbar_identity(window, app_id=app_id, title=title, icon_path=icon_path)
