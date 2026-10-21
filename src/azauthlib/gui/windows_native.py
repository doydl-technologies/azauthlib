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

"""Windows-only native chrome and process identity.

Imported lazily by platform_integration; no native libraries load at import time.
"""

from __future__ import annotations

import sys
from pathlib import Path


def apply_title_bar(window, *, dark: bool) -> None:
    """Best-effort dark/light Windows caption while preserving native chrome."""

    if sys.platform != "win32" or window is None:
        return
    try:
        from ctypes import byref, c_int, sizeof, windll

        hwnd = int(window.winId())
        enabled = c_int(1 if dark else 0)
        for attribute in (20, 19):
            result = windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                attribute,
                byref(enabled),
                sizeof(enabled),
            )
            if result == 0:
                break
    except (AttributeError, OSError, TypeError, ValueError):
        return


def disable_maximizing(window) -> None:
    """Disable Maximize in the native system menu (Alt+Space)."""
    if sys.platform != "win32" or window is None:
        return
    from ctypes import WinDLL, c_int, c_uint, c_void_p

    user32 = WinDLL("user32")
    user32.GetSystemMenu.argtypes = [c_void_p, c_int]
    user32.GetSystemMenu.restype = c_void_p
    user32.EnableMenuItem.argtypes = [c_void_p, c_uint, c_uint]
    user32.EnableMenuItem.restype = c_uint
    menu = user32.GetSystemMenu(int(window.winId()), False)
    if menu:
        user32.EnableMenuItem(menu, 0xF030, 0x0001)  # SC_MAXIMIZE, MF_BYCOMMAND | MF_GRAYED


def apply_titlebar_icon(window, icon_path: Path) -> int | None:
    """Override the small title-bar icon while retaining Qt's taskbar icon."""
    if sys.platform != "win32":
        return None

    from ctypes import WinDLL, c_int, c_ssize_t, c_void_p, c_wchar_p, get_last_error
    from ctypes.wintypes import UINT, WPARAM

    user32 = WinDLL("user32", use_last_error=True)
    user32.LoadImageW.argtypes = [c_void_p, c_wchar_p, UINT, c_int, c_int, UINT]
    user32.LoadImageW.restype = c_void_p
    user32.SendMessageW.argtypes = [c_void_p, UINT, WPARAM, c_ssize_t]
    user32.SendMessageW.restype = c_ssize_t
    user32.DestroyIcon.argtypes = [c_void_p]
    user32.DestroyIcon.restype = c_int
    user32.GetSystemMetrics.argtypes = [c_int]
    user32.GetSystemMetrics.restype = c_int

    # IMAGE_ICON, SM_CXSMICON / SM_CYSMICON, and LR_LOADFROMFILE.
    icon_handle = user32.LoadImageW(
        None,
        str(icon_path),
        1,
        user32.GetSystemMetrics(49),
        user32.GetSystemMetrics(50),
        0x0010,
    )
    if not icon_handle:
        raise OSError(get_last_error(), f"Unable to load title-bar icon: {icon_path}")

    # WM_SETICON with ICON_SMALL leaves ICON_BIG (the taskbar icon) untouched.
    user32.SendMessageW(int(window.winId()), 0x0080, 0, icon_handle)
    window.destroyed.connect(lambda *_args: user32.DestroyIcon(icon_handle))
    return icon_handle


def set_app_id(app_id: str) -> None:
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except (AttributeError, OSError):
        return


def allow_foreground_activation(process_id: int) -> None:
    """Allow the existing process to bring its window to the foreground."""
    if sys.platform != "win32":
        return
    try:
        from ctypes import WinDLL, c_int, c_uint32

        user32 = WinDLL("user32")
        user32.AllowSetForegroundWindow.argtypes = [c_uint32]
        user32.AllowSetForegroundWindow.restype = c_int
        user32.AllowSetForegroundWindow(process_id)
    except (AttributeError, OSError, TypeError, ValueError):
        return


def activate_window(window) -> None:
    """Request native foreground activation after Qt restores and raises the window."""
    if sys.platform != "win32" or window is None:
        return
    try:
        from ctypes import WinDLL, c_int, c_void_p

        user32 = WinDLL("user32")
        user32.SetForegroundWindow.argtypes = [c_void_p]
        user32.SetForegroundWindow.restype = c_int
        user32.SetForegroundWindow(int(window.winId()))
    except (AttributeError, OSError, TypeError, ValueError):
        return
