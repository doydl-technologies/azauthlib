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

"""Window-local Windows shell identity for a Python-hosted application.

No shortcuts, registry keys, Explorer caches, or other applications are changed.
"""

from __future__ import annotations

import ctypes as ct
import sys
from contextlib import suppress
from pathlib import Path
from subprocess import list2cmdline  # nosec B404 # Quotes only; never launches a process.
from uuid import UUID

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QPlatformSurfaceEvent


class _Guid(ct.Structure):
    _fields_ = [
        ("data1", ct.c_uint32),
        ("data2", ct.c_uint16),
        ("data3", ct.c_uint16),
        ("data4", ct.c_ubyte * 8),
    ]


class _PropertyKey(ct.Structure):
    _fields_ = [("fmtid", _Guid), ("pid", ct.c_uint32)]


class _Value(ct.Union):
    # PROPVARIANT's union is 16 bytes on Win64 and 8 bytes on Win32.
    _fields_ = [
        ("pointer", ct.c_void_p),
        ("storage", ct.c_ubyte * (16 if ct.sizeof(ct.c_void_p) == 8 else 8)),
    ]


class _PropVariant(ct.Structure):
    _fields_ = [
        ("vt", ct.c_uint16),
        ("reserved1", ct.c_uint16),
        ("reserved2", ct.c_uint16),
        ("reserved3", ct.c_uint16),
        ("value", _Value),
    ]


def _guid(value):
    return _Guid.from_buffer_copy(UUID(value).bytes_le)


def _key(pid):
    return _PropertyKey(_guid("9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3"), pid)


def _check(result):
    if result < 0:
        raise OSError(f"Windows taskbar identity failed (HRESULT 0x{result & 0xFFFFFFFF:08x})")


class _WindowPropertyStore:
    """Own an IPropertyStore supporting VT_LPWSTR and VT_EMPTY values."""

    def __init__(self, hwnd):
        shell32 = ct.WinDLL("shell32")
        get_store = shell32.SHGetPropertyStoreForWindow
        get_store.argtypes = [ct.c_void_p, ct.POINTER(_Guid), ct.POINTER(ct.c_void_p)]
        get_store.restype = ct.c_int32
        self.pointer = ct.c_void_p()
        iid = _guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99")
        _check(get_store(hwnd, ct.byref(iid), ct.byref(self.pointer)))

    def _call(self, index, types, *args):
        table = ct.cast(self.pointer, ct.POINTER(ct.POINTER(ct.c_void_p))).contents
        method = ct.WINFUNCTYPE(ct.c_int32, ct.c_void_p, *types)(table[index])
        return method(self.pointer, *args)

    def set_string(self, pid, value):
        key, variant = _key(pid), _PropVariant()
        if value is not None:
            # SetValue copies the string; this buffer is borrowed, not COM-owned.
            buffer = ct.create_unicode_buffer(value)
            variant.vt = 31  # VT_LPWSTR
            variant.value.pointer = ct.cast(buffer, ct.c_void_p)
        _check(
            self._call(
                6,
                [ct.POINTER(_PropertyKey), ct.POINTER(_PropVariant)],
                ct.byref(key),
                ct.byref(variant),
            )
        )

    def get_string(self, pid):
        key, variant = _key(pid), _PropVariant()
        clear = ct.WinDLL("ole32").PropVariantClear
        clear.argtypes = [ct.POINTER(_PropVariant)]
        clear.restype = ct.c_int32
        try:
            _check(
                self._call(
                    5,
                    [ct.POINTER(_PropertyKey), ct.POINTER(_PropVariant)],
                    ct.byref(key),
                    ct.byref(variant),
                )
            )
            if variant.vt == 0:
                return None
            if variant.vt != 31:
                raise ValueError("Expected a Windows taskbar string property")
            return ct.wstring_at(variant.value.pointer)
        finally:
            clear(ct.byref(variant))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self._call(2, [])  # IUnknown::Release
        self.pointer = None


def _short_shell_path(path):
    """Use an existing Windows short path without creating aliases or files."""
    get_short = ct.WinDLL("kernel32").GetShortPathNameW
    get_short.argtypes = [ct.c_wchar_p, ct.c_wchar_p, ct.c_uint32]
    get_short.restype = ct.c_uint32
    size = get_short(str(path), None, 0)
    if not size:
        return str(path)
    buffer = ct.create_unicode_buffer(size)
    written = get_short(str(path), buffer, size)
    return buffer.value if 0 < written < size else str(path)


def relaunch_command():
    """Relaunch this package within the shell's 255 UTF-16-unit property limit."""
    executable = Path(sys.executable)
    frozen = getattr(sys, "frozen", False)
    if frozen:
        arguments = [str(executable)]
    else:
        pythonw = executable.with_name("pythonw.exe")
        launcher = Path(__file__).resolve().with_name("launch.py")
        arguments = [str(pythonw if pythonw.is_file() else executable), str(launcher)]
    command = list2cmdline(arguments)
    if len(command.encode("utf-16-le")) // 2 <= 255:
        return command
    arguments = [_short_shell_path(path) for path in arguments]
    command = list2cmdline(arguments)
    if len(command.encode("utf-16-le")) // 2 <= 255:
        return command
    if not frozen:
        # Volumes may disable short names; installed packages can use Python's module entry point.
        command = list2cmdline([arguments[0], "-m", "azauthlib.gui.launch"])
        if len(command.encode("utf-16-le")) // 2 <= 255:
            return command
    raise OSError("The Windows taskbar relaunch command exceeds the shell property limit")


class WindowTaskbarIdentity(QObject):
    """Keep shell metadata attached until the HWND is about to be destroyed."""

    def __init__(self, window, *, app_id, title, icon_path):
        super().__init__(window)
        self.hwnd = int(window.winId())
        with _WindowPropertyStore(self.hwnd) as store:
            try:
                # Set relaunch information before publishing the window's AppID.
                store.set_string(2, relaunch_command())
                store.set_string(3, str(Path(icon_path).resolve()) + ",0")
                store.set_string(4, title)
                store.set_string(5, app_id)
            except OSError:
                for pid in (5, 2, 3, 4):
                    store.set_string(pid, None)
                raise
        window.installEventFilter(self)

    def eventFilter(self, watched, event):
        if (
            event.type() == QEvent.PlatformSurface
            and event.surfaceEventType() == QPlatformSurfaceEvent.SurfaceAboutToBeDestroyed
        ):
            self.clear()
        return super().eventFilter(watched, event)

    def clear(self):
        if self.hwnd:
            # Windows requires VT_EMPTY before the HWND is destroyed.
            with suppress(OSError), _WindowPropertyStore(self.hwnd) as store:
                for pid in (5, 2, 3, 4):
                    store.set_string(pid, None)
            self.hwnd = 0


def apply_window_taskbar_identity(window, *, app_id, title, icon_path):
    if sys.platform == "win32":
        previous = getattr(window, "_taskbar_identity", None)
        if previous is not None:
            window.removeEventFilter(previous)
            previous.clear()
            previous.deleteLater()
        window._taskbar_identity = WindowTaskbarIdentity(
            window, app_id=app_id, title=title, icon_path=icon_path
        )
