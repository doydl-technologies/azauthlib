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

"""Opt-in per-user app launchers; importing this module never creates files."""

from __future__ import annotations

import hashlib
import os
import plistlib
import shlex
import struct
import sys
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path

from ..appdata import get_config_dir

APP_ID = "doydl-technologies.azauthlib"


class ShortcutError(RuntimeError):
    """Raised when a shortcut cannot be created safely."""


@dataclass(frozen=True)
class ShortcutResult:
    paths: tuple[Path, ...]
    message: str


def _safe_path(value) -> Path:
    text = os.fspath(value)
    if not isinstance(text, str) or any(ord(char) < 32 or ord(char) == 127 for char in text):
        raise ShortcutError("Shortcut paths must not contain control characters.")
    return Path(text).expanduser().absolute()


def _command(executable, launcher, system):
    executable = _safe_path(executable or sys.executable)
    if system == "win32" and executable.name.lower() == "python.exe":
        windowless = executable.with_name("pythonw.exe")
        if windowless.is_file():
            executable = windowless
    if not executable.is_file():
        raise ShortcutError("The current Python executable could not be found.")
    if getattr(sys, "frozen", False):
        return (str(executable),)
    launcher = _safe_path(launcher or Path(__file__).with_name("launch.py"))
    if not launcher.is_file():
        raise ShortcutError("The app launcher is unavailable. Use a regular installed package.")
    return str(executable), str(launcher)


def _check_destination(path):
    if path.exists() or path.is_symlink():
        raise ShortcutError(
            f"{path.name} already exists at the shortcut location. "
            "Nothing was overwritten. Rename or remove that item before trying again."
        )


def _write_new(path, contents, created, mode=0o644):
    with path.open("xb") as stream:
        created.append(path)
        stream.write(contents)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(mode)


def _icon_file(path, contents, created):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise ShortcutError("The shortcut icon destination is a symbolic link.")
    if path.exists():
        if not path.is_file() or path.read_bytes() != contents:
            raise ShortcutError("An unrelated file occupies the shortcut icon destination.")
    else:
        _write_new(path, contents, created)
    return path


def _png_icons(data):
    if len(data) < 6:
        raise ShortcutError("The bundled application icon is invalid.")
    reserved, kind, count = struct.unpack_from("<HHH", data)
    if reserved or kind != 1 or not 0 < count <= 256 or len(data) < 6 + 16 * count:
        raise ShortcutError("The bundled application icon is invalid.")
    icons = {}
    for index in range(count):
        width, height, _, _, _, _, length, offset = struct.unpack_from(
            "<BBBBHHII", data, 6 + 16 * index
        )
        width, height = width or 256, height or 256
        if offset < 6 + 16 * count or offset + length > len(data):
            raise ShortcutError("The bundled application icon is truncated.")
        png = data[offset : offset + length]
        if (
            width == height
            and len(png) >= 24
            and png[:8] == b"\x89PNG\r\n\x1a\n"
            and png[12:16] == b"IHDR"
            and struct.unpack_from(">II", png, 16) == (width, height)
        ):
            icons[width] = png
    if not icons:
        raise ShortcutError("The application icon contains no supported PNG images.")
    return icons


def _icns(icons):
    tags = {16: b"icp4", 32: b"icp5", 64: b"icp6", 128: b"ic07", 256: b"ic08"}
    chunks = [
        tags[size] + struct.pack(">I", len(png) + 8) + png
        for size, png in sorted(icons.items())
        if size in tags
    ]
    if not chunks:
        raise ShortcutError("The application icon has no supported macOS sizes.")
    contents = b"".join(chunks)
    return b"icns" + struct.pack(">I", len(contents) + 8) + contents


def _desktop_value(value):
    return value.replace("\\", "\\\\")


def _desktop_argument(value):
    # Exec quoting and desktop-entry string escaping are separate parsing layers.
    escaped = "".join("\\" + char if char in ('"', "\\", "$", chr(96)) else char for char in value)
    return _desktop_value('"' + escaped.replace("%", "%%") + '"')


def _desktop_entry(command, icon):
    if "=" in command[0]:
        raise ShortcutError("Linux launchers cannot use a Python executable path containing '='.")
    text = (
        "[Desktop Entry]\nVersion=1.0\nType=Application\nName=azauthlib\n"
        "Comment=Manage Microsoft Graph connection profiles\n"
        f"Exec={' '.join(_desktop_argument(value) for value in command)}\n"
        f"Icon={_desktop_value(str(icon))}\n"
        "Terminal=false\nCategories=Development;Utility;\nStartupNotify=false\n"
    )
    return text.encode("utf-8")


def _mac_bundle(destination, command, icons, identity, created, directories):
    destination.mkdir(mode=0o700)
    directories.append(destination)
    contents = destination / "Contents"
    for path in (contents, contents / "MacOS", contents / "Resources"):
        path.mkdir(mode=0o700)
        directories.append(path)
    metadata = {
        "CFBundleName": "azauthlib",
        "CFBundleDisplayName": "azauthlib",
        "CFBundleIdentifier": f"{APP_ID}.launcher.{identity}",
        "CFBundlePackageType": "APPL",
        "CFBundleExecutable": "azauthlib-launcher",
        "CFBundleIconFile": "azauthlib.icns",
        "CFBundleVersion": "1",
        "NSHighResolutionCapable": True,
    }
    _write_new(contents / "Info.plist", plistlib.dumps(metadata), created)
    script = "#!/bin/sh\nexec " + " ".join(shlex.quote(value) for value in command) + "\n"
    _write_new(contents / "MacOS" / "azauthlib-launcher", script.encode("utf-8"), created, 0o755)
    _write_new(contents / "Resources" / "azauthlib.icns", _icns(icons), created)


def create_app_shortcut(
    *,
    desktop_dir,
    icon_path,
    system=None,
    executable=None,
    launcher=None,
    data_dir=None,
    applications_dir=None,
) -> ShortcutResult:
    """Create launchers only after an explicit request, without replacing existing items.

    The caller supplies the native Desktop location. Linux additionally installs
    a per-user application-menu entry; desktop copies retain the shell's normal
    trust/approval requirements. No credentials or profile files are read.
    """
    system = system or sys.platform
    if system not in {"win32", "darwin"} and not system.startswith("linux"):
        raise ShortcutError("App shortcuts are not supported on this operating system.")
    command = _command(executable, launcher, system)
    desktop = _safe_path(desktop_dir) if desktop_dir else None
    if desktop is not None and (desktop == Path.home().absolute() or not desktop.is_dir()):
        desktop = None
    if system in {"win32", "darwin"} and desktop is None:
        raise ShortcutError("The Desktop folder is unavailable. No shortcut was created.")
    identity = hashlib.sha256("\0".join(command).encode("utf-8")).hexdigest()[:16]
    icon_data = _safe_path(icon_path).read_bytes()
    assets = _safe_path(data_dir or get_config_dir(create=False) / "shortcuts") / identity
    created, directories = [], []
    try:
        if system == "darwin":
            destination = desktop / "azauthlib.app"
            _check_destination(destination)
            _mac_bundle(destination, command, _png_icons(icon_data), identity, created, directories)
            return ShortcutResult(
                (destination,),
                "azauthlib.app was created on your Desktop. Open it in Finder or add it to "
                "the Dock. It requires this Python environment to remain installed.",
            )
        if system == "win32":
            destination = desktop / "azauthlib.lnk"
            _check_destination(destination)
            icon = _icon_file(assets / "azauthlib.ico", icon_data, created)
            from .windows_shortcuts import write_shell_link

            with tempfile.TemporaryDirectory(prefix="azauthlib-shortcut-") as temporary:
                link = Path(temporary) / "azauthlib.lnk"
                write_shell_link(link, command, icon, APP_ID)
                _write_new(destination, link.read_bytes(), created)
            return ShortcutResult(
                (destination,),
                "The azauthlib shortcut was created on your Desktop. It requires this "
                "Python environment to remain installed.",
            )
        applications = _safe_path(applications_dir or user_data_path() / "applications")
        destinations = [applications / "doydl-azauthlib.desktop"]
        if desktop is not None:
            destinations.append(desktop / "azauthlib.desktop")
        for destination in destinations:
            _check_destination(destination)
        icons = _png_icons(icon_data)
        icon = _icon_file(assets / "azauthlib.png", icons[max(icons)], created)
        entry = _desktop_entry(command, icon)
        applications.mkdir(mode=0o700, parents=True, exist_ok=True)
        for destination in destinations:
            _write_new(destination, entry, created, 0o755)
        note = (
            "azauthlib was added to your applications menu. "
            "It requires this Python environment to remain installed."
        )
        if desktop is not None:
            note += " A Desktop copy was also created; your desktop may ask you to allow launching."
        return ShortcutResult(tuple(destinations), note)
    except Exception:
        # Roll back only files and bundle directories created by this request.
        for path in reversed(created):
            with suppress(OSError):
                path.unlink()
        for path in reversed(directories):
            with suppress(OSError):
                path.rmdir()
        raise
