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


"""Opt-in launcher generation with all writes confined to temporary directories."""

import ctypes as ct
import os
import plistlib
import shlex
import struct
import sys
from pathlib import Path
from subprocess import list2cmdline

import pytest

from azauthlib.gui import shortcuts

ICON = Path(__file__).resolve().parents[1] / "src/azauthlib/assets/azauthlib-taskbar.ico"


@pytest.fixture
def launcher_paths(tmp_path):
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    runtime = tmp_path / "Python environment"
    runtime.mkdir()
    executable = runtime / ("python.exe" if sys.platform == "win32" else "python")
    executable.touch()
    launcher = runtime / "app launcher.py"
    launcher.touch()
    return dict(
        desktop_dir=desktop,
        icon_path=ICON,
        executable=executable,
        launcher=launcher,
        data_dir=tmp_path / "launcher-data",
        applications_dir=tmp_path / "applications",
    )


def test_linux_menu_and_desktop_keep_original_icon_and_exact_command(launcher_paths):
    result = shortcuts.create_app_shortcut(system="linux", **launcher_paths)
    assert len(result.paths) == 2
    content = result.paths[0].read_text(encoding="utf-8")
    assert content == result.paths[1].read_text(encoding="utf-8")
    assert "Terminal=false" in content
    assert 'Exec="' in content and "app launcher.py" in content
    assert not any("secret" in line.lower() for line in content.splitlines())
    icons = list(launcher_paths["data_dir"].rglob("*.png"))
    assert len(icons) == 1
    assert icons[0].read_bytes() == shortcuts._png_icons(ICON.read_bytes())[256]
    if os.name != "nt":
        assert result.paths[0].stat().st_mode & 0o111 == 0o111


def test_linux_without_desktop_still_installs_app_menu(launcher_paths):
    launcher_paths["desktop_dir"] = None
    result = shortcuts.create_app_shortcut(system="linux", **launcher_paths)
    assert result.paths == (launcher_paths["applications_dir"] / "doydl-azauthlib.desktop",)


@pytest.mark.parametrize("system", ["linux", "darwin", "win32"])
def test_existing_launchers_are_never_overwritten(launcher_paths, system):
    names = {"linux": "azauthlib.desktop", "darwin": "azauthlib.app", "win32": "azauthlib.lnk"}
    existing = launcher_paths["desktop_dir"] / names[system]
    existing.write_bytes(b"unrelated user data")
    with pytest.raises(shortcuts.ShortcutError, match="Nothing was overwritten"):
        shortcuts.create_app_shortcut(system=system, **launcher_paths)
    assert existing.read_bytes() == b"unrelated user data"
    assert not launcher_paths["data_dir"].exists()
    assert not launcher_paths["applications_dir"].exists()


def test_linux_second_write_failure_rolls_back_only_own_files(monkeypatch, launcher_paths):
    write = shortcuts._write_new

    def fail_on_desktop(path, *args, **kwargs):
        if path.parent == launcher_paths["desktop_dir"]:
            raise PermissionError("Test-only denied Desktop")
        return write(path, *args, **kwargs)

    unrelated = launcher_paths["data_dir"] / "keep.txt"
    unrelated.parent.mkdir()
    unrelated.write_text("keep", encoding="utf-8")
    monkeypatch.setattr(shortcuts, "_write_new", fail_on_desktop)
    with pytest.raises(PermissionError):
        shortcuts.create_app_shortcut(system="linux", **launcher_paths)
    assert not list(launcher_paths["applications_dir"].glob("*.desktop"))
    assert not list(launcher_paths["data_dir"].rglob("*.png"))
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_macos_bundle_uses_existing_environment_and_original_icon(launcher_paths):
    result = shortcuts.create_app_shortcut(system="darwin", **launcher_paths)
    bundle = result.paths[0]
    info = plistlib.loads((bundle / "Contents/Info.plist").read_bytes())
    assert info["CFBundlePackageType"] == "APPL"
    assert info["CFBundleExecutable"] == "azauthlib-launcher"
    script = (bundle / "Contents/MacOS/azauthlib-launcher").read_text(encoding="utf-8")
    assert shlex.split(script.splitlines()[1]) == [
        "exec",
        str(launcher_paths["executable"]),
        str(launcher_paths["launcher"]),
    ]
    icns = (bundle / "Contents/Resources/azauthlib.icns").read_bytes()
    assert icns[:4] == b"icns" and struct.unpack_from(">I", icns, 4)[0] == len(icns)
    offset, payloads = 8, []
    while offset < len(icns):
        length = struct.unpack_from(">I", icns, offset + 4)[0]
        payloads.append(icns[offset + 8 : offset + length])
        offset += length
    originals = shortcuts._png_icons(ICON.read_bytes())
    assert payloads == [originals[size] for size in (16, 32, 64, 128, 256)]
    from PySide6.QtGui import QImageReader

    image = QImageReader(str(bundle / "Contents/Resources/azauthlib.icns")).read()
    assert not image.isNull()


def test_macos_failed_bundle_does_not_leave_broken_launcher(monkeypatch, launcher_paths):
    def broken(_icons):
        raise shortcuts.ShortcutError("Test-only icon failure")

    monkeypatch.setattr(shortcuts, "_icns", broken)
    with pytest.raises(shortcuts.ShortcutError):
        shortcuts.create_app_shortcut(system="darwin", **launcher_paths)
    assert not (launcher_paths["desktop_dir"] / "azauthlib.app").exists()


def test_windows_uses_pythonw_and_persistent_icon(monkeypatch, launcher_paths):
    from azauthlib.gui import windows_shortcuts

    exe = launcher_paths["executable"].with_name("python.exe")
    exe.touch()
    windowless = exe.with_name("pythonw.exe")
    windowless.touch()
    launcher_paths["executable"] = exe
    calls = []

    def writer(path, command, icon, app_id):
        calls.append((command, icon, app_id))
        path.write_bytes(b"test shell link")

    monkeypatch.setattr(windows_shortcuts, "write_shell_link", writer)
    result = shortcuts.create_app_shortcut(system="win32", **launcher_paths)
    assert result.paths[0].read_bytes() == b"test shell link"
    command, icon, app_id = calls[0]
    assert command == (str(windowless), str(launcher_paths["launcher"]))
    assert icon.read_bytes() == ICON.read_bytes()
    assert icon.is_relative_to(launcher_paths["data_dir"])
    assert app_id == shortcuts.APP_ID


def test_windows_creation_failure_removes_only_new_icon(monkeypatch, launcher_paths):
    from azauthlib.gui import windows_shortcuts

    def fail(*_args):
        raise OSError("Test-only shell failure")

    monkeypatch.setattr(windows_shortcuts, "write_shell_link", fail)
    with pytest.raises(OSError):
        shortcuts.create_app_shortcut(system="win32", **launcher_paths)
    assert not list(launcher_paths["data_dir"].rglob("*.ico"))
    assert not list(launcher_paths["desktop_dir"].iterdir())


@pytest.mark.parametrize(
    "value", ["", " ", "a b", 'a"b', "a\\b", "a$b", "a%b", "a" + chr(96) + "b"]
)
def test_desktop_exec_escaping_round_trips(value):
    encoded = shortcuts._desktop_argument(value)
    # Undo the string layer, then Exec quoting; these are not shell commands.
    string_layer = encoded.replace("\\\\", "\\")
    tokens = shlex.split(string_layer.replace("\\$", "$").replace("\\" + chr(96), chr(96)))
    assert len(tokens) == 1
    assert tokens[0].replace("%%", "%") == value


@pytest.mark.parametrize("system", ["darwin", "win32"])
def test_no_desktop_is_reported_without_writes(launcher_paths, system):
    launcher_paths["desktop_dir"] = None
    with pytest.raises(shortcuts.ShortcutError, match="Desktop folder is unavailable"):
        shortcuts.create_app_shortcut(system=system, **launcher_paths)
    assert not launcher_paths["data_dir"].exists()


def test_invalid_platform_and_paths_do_not_write(launcher_paths):
    with pytest.raises(shortcuts.ShortcutError, match="operating system"):
        shortcuts.create_app_shortcut(system="unsupported", **launcher_paths)
    launcher_paths["launcher"] = "bad\npath"
    with pytest.raises(shortcuts.ShortcutError, match="control characters"):
        shortcuts.create_app_shortcut(system="linux", **launcher_paths)
    assert not launcher_paths["data_dir"].exists()


@pytest.mark.parametrize("data", [b"", b"bad", b"\0\0\1\0\1\0", ICON.read_bytes()[:200]])
def test_corrupt_icons_are_rejected(data):
    with pytest.raises(shortcuts.ShortcutError):
        shortcuts._png_icons(data)


def test_frozen_launcher_has_no_python_script(monkeypatch, launcher_paths):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    command = shortcuts._command(launcher_paths["executable"], None, "linux")
    assert command == (str(launcher_paths["executable"]),)


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows COM verification")
def test_native_windows_link_properties_round_trip(launcher_paths):
    from azauthlib.gui.windows_shortcuts import _call
    from azauthlib.gui.windows_taskbar import _check, _Guid, _guid, _key, _PropVariant

    launcher_paths["executable"] = Path(sys.executable)
    launcher_paths["launcher"] = Path(shortcuts.__file__).with_name("launch.py")
    expected_executable = Path(sys.executable).with_name("pythonw.exe")
    if not expected_executable.is_file():
        expected_executable = Path(sys.executable)
    result = shortcuts.create_app_shortcut(system="win32", **launcher_paths)
    ole32 = ct.WinDLL("ole32")
    ole32.CoInitializeEx.argtypes = [ct.c_void_p, ct.c_uint32]
    ole32.CoInitializeEx.restype = ct.c_int32
    ole32.CoCreateInstance.argtypes = [
        ct.POINTER(_Guid),
        ct.c_void_p,
        ct.c_uint32,
        ct.POINTER(_Guid),
        ct.POINTER(ct.c_void_p),
    ]
    ole32.CoCreateInstance.restype = ct.c_int32
    _check(ole32.CoInitializeEx(None, 2))
    link, persist, store = ct.c_void_p(), ct.c_void_p(), ct.c_void_p()
    try:
        clsid, iid = (
            _guid("00021401-0000-0000-c000-000000000046"),
            _guid("000214f9-0000-0000-c000-000000000046"),
        )
        _check(ole32.CoCreateInstance(ct.byref(clsid), None, 1, ct.byref(iid), ct.byref(link)))
        for target, guid in [
            (persist, "0000010b-0000-0000-c000-000000000046"),
            (store, "886d8eeb-8cf2-4446-8d02-cdba1dbdcf99"),
        ]:
            interface = _guid(guid)
            _check(
                _call(
                    link,
                    0,
                    [ct.POINTER(_Guid), ct.POINTER(ct.c_void_p)],
                    ct.byref(interface),
                    ct.byref(target),
                )
            )
        _check(_call(persist, 5, [ct.c_wchar_p, ct.c_uint32], str(result.paths[0]), 0))
        target = ct.create_unicode_buffer(32768)
        _check(
            _call(
                link,
                3,
                [ct.c_wchar_p, ct.c_int, ct.c_void_p, ct.c_uint32],
                target,
                len(target),
                None,
                4,
            )
        )
        assert Path(target.value) == expected_executable
        args = ct.create_unicode_buffer(32768)
        _check(_call(link, 10, [ct.c_wchar_p, ct.c_int], args, len(args)))
        assert args.value == list2cmdline([str(launcher_paths["launcher"])])
        icon, index = ct.create_unicode_buffer(32768), ct.c_int()
        _check(
            _call(
                link,
                16,
                [ct.c_wchar_p, ct.c_int, ct.POINTER(ct.c_int)],
                icon,
                len(icon),
                ct.byref(index),
            )
        )
        assert Path(icon.value).read_bytes() == ICON.read_bytes() and index.value == 0
        key, value = _key(5), _PropVariant()
        clear = ole32.PropVariantClear
        clear.argtypes = [ct.POINTER(_PropVariant)]
        try:
            _check(
                _call(
                    store,
                    5,
                    [ct.POINTER(type(key)), ct.POINTER(_PropVariant)],
                    ct.byref(key),
                    ct.byref(value),
                )
            )
            assert value.vt == 31 and ct.wstring_at(value.value.pointer) == shortcuts.APP_ID
        finally:
            clear(ct.byref(value))
    finally:
        for pointer in (store, persist, link):
            if pointer:
                _call(pointer, 2, [])
        ole32.CoUninitialize()
