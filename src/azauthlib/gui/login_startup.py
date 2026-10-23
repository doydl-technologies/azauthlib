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

"""Opt-in, current-user login launchers. No registration happens on import or launch."""

from __future__ import annotations

import os
import plistlib
import sys
import tempfile
from contextlib import suppress
from pathlib import Path
from subprocess import list2cmdline  # nosec B404 # Quoting only; no process is started.

from .shortcuts import APP_ID, _command, _desktop_argument

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


class LoginStartupError(RuntimeError):
    pass


def supported(system=None):
    system = system or sys.platform
    return system in {"win32", "darwin"} or system.startswith("linux")


def _replace(path, data):
    """Replace only one explicit managed file; never follow an existing symlink."""
    if path.is_symlink():
        raise LoginStartupError("The login-startup location is a symbolic link.")
    if data is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".azauthlib-login-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)


def apply_login_startup(
    enabled,
    *,
    system=None,
    home=None,
    config_home=None,
    executable=None,
    launcher=None,
    registry=None,
):
    """Apply an explicit Settings save and return a rollback for preference-save failure.

    Login opens the normal UI, not a hidden process. Existing single-instance IPC
    handles repeated launches. Only this app's named registration is changed.
    """
    if type(enabled) is not bool:
        raise ValueError("Login preference must be a boolean")
    system = system or sys.platform
    if not supported(system):
        raise LoginStartupError("Launch at login is unavailable on this operating system.")
    # Disabling must work even if the old interpreter/installation was removed.
    command = _command(executable, launcher, system) if enabled else None
    if enabled and system.startswith("linux") and "=" in command[0]:
        raise LoginStartupError("The app executable path cannot contain '=' on Linux.")
    if system == "win32":
        if registry is None:
            import winreg as registry
        value = list2cmdline(command) if enabled else None
        if value is not None and len(value) > 260:
            raise LoginStartupError("The app path is too long for Windows login startup.")

        def read():
            try:
                with registry.OpenKey(registry.HKEY_CURRENT_USER, RUN_KEY) as key:
                    return registry.QueryValueEx(key, APP_ID)
            except FileNotFoundError:
                return None

        def write(entry):
            if entry is None:
                try:
                    with registry.OpenKey(
                        registry.HKEY_CURRENT_USER, RUN_KEY, 0, registry.KEY_SET_VALUE
                    ) as key:
                        registry.DeleteValue(key, APP_ID)
                except FileNotFoundError:
                    pass
            else:
                with registry.CreateKeyEx(
                    registry.HKEY_CURRENT_USER, RUN_KEY, 0, registry.KEY_SET_VALUE
                ) as key:
                    registry.SetValueEx(key, APP_ID, 0, entry[1], entry[0])

        previous = read()
        updated = (value, registry.REG_SZ) if enabled else None
        write(updated)

        def rollback():
            if read() != updated:
                raise LoginStartupError("Login startup changed outside the app; rollback skipped.")
            write(previous)

        return rollback

    home = Path(home) if home is not None else Path.home()
    if system == "darwin":
        path = home / "Library/LaunchAgents" / (APP_ID + ".plist")
        data = (
            plistlib.dumps(
                {
                    "Label": APP_ID,
                    "ProgramArguments": list(command),
                    "RunAtLoad": True,
                    "KeepAlive": False,
                    "ProcessType": "Interactive",
                    "azauthlibManaged": True,
                }
            )
            if enabled
            else None
        )
    else:
        config = Path(config_home or os.environ.get("XDG_CONFIG_HOME") or home / ".config")
        if not config.is_absolute():
            raise LoginStartupError("The login-startup configuration path must be absolute.")
        path = config / "autostart" / (APP_ID + ".desktop")
        data = (
            (
                "[Desktop Entry]\nType=Application\nName=azauthlib\n"
                "Comment=Open azauthlib when signing in\nTerminal=false\n"
                "X-azauthlib-Managed=true\nExec="
                + " ".join(_desktop_argument(part) for part in command)
                + "\n"
            ).encode()
            if enabled
            else None
        )
    if path.is_symlink():
        raise LoginStartupError("The login-startup location is a symbolic link.")
    previous = None
    if path.exists():
        if path.stat().st_size > 65_536:
            raise LoginStartupError("An unrelated item occupies the login-startup location.")
        previous = path.read_bytes()
        try:
            owned = (
                plistlib.loads(previous).get("azauthlibManaged") is True
                if system == "darwin"
                else b"\nX-azauthlib-Managed=true\n" in previous
            )
        except (ValueError, TypeError, AttributeError, plistlib.InvalidFileException):
            owned = False
        if not owned:
            raise LoginStartupError("An unrelated item occupies the login-startup location.")
    _replace(path, data)

    def rollback():
        if path.is_symlink() or (path.read_bytes() if path.exists() else None) != data:
            raise LoginStartupError("Login startup changed outside the app; rollback skipped.")
        _replace(path, previous)

    return rollback
