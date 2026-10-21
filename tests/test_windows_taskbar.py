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

"""Windows taskbar relaunch-command regressions without shell or window mutations."""

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows shell integration")


@pytest.fixture
def taskbar():
    from azauthlib.gui import windows_taskbar

    return windows_taskbar


@pytest.mark.parametrize("windowless", [False, True])
def test_short_commands_preserve_direct_launcher(taskbar, monkeypatch, tmp_path, windowless):
    executable = tmp_path / "python.exe"
    monkeypatch.setattr(taskbar.sys, "executable", str(executable))
    monkeypatch.setattr(taskbar, "__file__", str(tmp_path / "windows_taskbar.py"))
    if windowless:
        (tmp_path / "pythonw.exe").touch()
    command = taskbar.relaunch_command()
    assert str(tmp_path / "launch.py") in command
    assert ("pythonw.exe" in command) == windowless


def test_long_commands_use_existing_short_paths(taskbar, monkeypatch, tmp_path):
    monkeypatch.setattr(taskbar.sys, "executable", str(tmp_path / "python.exe"))
    monkeypatch.setattr(taskbar, "__file__", str(tmp_path / ("x" * 180) / "windows_taskbar.py"))
    monkeypatch.setattr(
        taskbar,
        "_short_shell_path",
        lambda path: "C:/python.exe" if "python" in path else "C:/launch.py",
    )
    command = taskbar.relaunch_command()
    assert command == "C:/python.exe C:/launch.py"
    assert len(command.encode("utf-16-le")) // 2 <= 255


def test_long_commands_fall_back_to_installed_module(taskbar, monkeypatch, tmp_path):
    monkeypatch.setattr(taskbar.sys, "executable", str(tmp_path / "python.exe"))
    monkeypatch.setattr(taskbar, "__file__", str(tmp_path / ("x" * 180) / "windows_taskbar.py"))
    monkeypatch.setattr(taskbar, "_short_shell_path", str)
    command = taskbar.relaunch_command()
    assert command.endswith("-m azauthlib.gui.launch")
    assert len(command.encode("utf-16-le")) // 2 <= 255


def test_frozen_command_does_not_use_python_launcher(taskbar, monkeypatch, tmp_path):
    monkeypatch.setattr(taskbar.sys, "frozen", True, raising=False)
    monkeypatch.setattr(taskbar.sys, "executable", str(tmp_path / "app.exe"))
    assert taskbar.relaunch_command() == taskbar.list2cmdline([str(tmp_path / "app.exe")])


def test_unrepresentable_frozen_path_fails_clearly(taskbar, monkeypatch, tmp_path):
    monkeypatch.setattr(taskbar.sys, "frozen", True, raising=False)
    monkeypatch.setattr(taskbar.sys, "executable", str(tmp_path / ("x" * 260) / "app.exe"))
    monkeypatch.setattr(taskbar, "_short_shell_path", str)
    with pytest.raises(OSError, match="shell property limit"):
        taskbar.relaunch_command()


def test_short_path_failure_preserves_requested_path(taskbar, tmp_path):
    missing = tmp_path / "missing.exe"
    assert taskbar._short_shell_path(missing) == str(missing)
