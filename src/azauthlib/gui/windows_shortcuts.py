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

"""Create Windows shell links through COM without scripts or registry changes."""

from __future__ import annotations

import ctypes as ct
import sys
from pathlib import Path
from subprocess import list2cmdline  # nosec B404 # Quoting only; no process is started.


def _call(pointer, index, types, *arguments):
    table = ct.cast(pointer, ct.POINTER(ct.POINTER(ct.c_void_p))).contents
    method = ct.WINFUNCTYPE(ct.c_int32, ct.c_void_p, *types)(table[index])
    return method(pointer, *arguments)


def write_shell_link(destination: Path, command: tuple[str, ...], icon: Path, app_id: str) -> None:
    """Write a new link at a caller-owned temporary path in this thread's COM apartment."""
    if sys.platform != "win32":
        raise OSError("Windows shortcuts require Windows.")
    from .windows_taskbar import _check, _Guid, _guid, _key, _PropVariant

    ole32 = ct.WinDLL("ole32")
    ole32.CoInitializeEx.argtypes = [ct.c_void_p, ct.c_uint32]
    ole32.CoInitializeEx.restype = ct.c_int32
    ole32.CoUninitialize.argtypes = []
    ole32.CoUninitialize.restype = None
    ole32.CoCreateInstance.argtypes = [
        ct.POINTER(_Guid),
        ct.c_void_p,
        ct.c_uint32,
        ct.POINTER(_Guid),
        ct.POINTER(ct.c_void_p),
    ]
    ole32.CoCreateInstance.restype = ct.c_int32
    _check(ole32.CoInitializeEx(None, 2))
    link, persistence, properties = ct.c_void_p(), ct.c_void_p(), ct.c_void_p()
    try:
        clsid = _guid("00021401-0000-0000-c000-000000000046")
        iid = _guid("000214f9-0000-0000-c000-000000000046")
        _check(ole32.CoCreateInstance(ct.byref(clsid), None, 1, ct.byref(iid), ct.byref(link)))
        _check(_call(link, 20, [ct.c_wchar_p], command[0]))
        _check(_call(link, 11, [ct.c_wchar_p], list2cmdline(command[1:])))
        _check(_call(link, 9, [ct.c_wchar_p], str(Path(command[0]).parent)))
        _check(_call(link, 7, [ct.c_wchar_p], "Open azauthlib"))
        _check(_call(link, 15, [ct.c_int], 1))
        _check(_call(link, 17, [ct.c_wchar_p, ct.c_int], str(icon), 0))
        property_iid = _guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99")
        _check(
            _call(
                link,
                0,
                [ct.POINTER(_Guid), ct.POINTER(ct.c_void_p)],
                ct.byref(property_iid),
                ct.byref(properties),
            )
        )
        key, value = _key(5), _PropVariant()
        buffer = ct.create_unicode_buffer(app_id)
        value.vt = 31
        value.value.pointer = ct.cast(buffer, ct.c_void_p)
        _check(
            _call(
                properties,
                6,
                [ct.POINTER(type(key)), ct.POINTER(_PropVariant)],
                ct.byref(key),
                ct.byref(value),
            )
        )
        _check(_call(properties, 7, []))
        persist_iid = _guid("0000010b-0000-0000-c000-000000000046")
        _check(
            _call(
                link,
                0,
                [ct.POINTER(_Guid), ct.POINTER(ct.c_void_p)],
                ct.byref(persist_iid),
                ct.byref(persistence),
            )
        )
        _check(_call(persistence, 6, [ct.c_wchar_p, ct.c_int], str(destination), 1))
    finally:
        for pointer in (persistence, properties, link):
            if pointer:
                _call(pointer, 2, [])
        ole32.CoUninitialize()
