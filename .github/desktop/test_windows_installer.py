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

"""MSI authoring invariants; these tests never register or install a product."""

# ruff: noqa: S101 -- Assertions are intentional in this test module.
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import build_windows_installer as native
import pytest


@pytest.fixture
def payload(tmp_path):
    folder = tmp_path / "payload"
    folder.mkdir()
    (folder / "azauthlib.exe").write_bytes(b"test file, never executed")
    assets = folder / "_internal/assets"
    assets.mkdir(parents=True)
    (assets / "logo.svg").write_text("<svg/>")
    return folder


def test_per_user_msi_has_transactional_upgrade_and_no_launch(payload, tmp_path):
    output = tmp_path / "desktop.wxs"
    native.author(payload, "5.0.0", output)
    root = ET.parse(output)  # noqa: S314 -- XML authored by this test, not external input.

    def find(tag):
        return root.find(".//{" + native.NS + "}" + tag)

    assert find("Package").get("InstallScope") == "perUser"
    assert find("Package").get("InstallPrivileges") != "elevated"
    assert find("MajorUpgrade").get("Schedule") == "afterInstallExecute"
    shortcuts = root.findall(".//{" + native.NS + "}Shortcut")
    assert len(shortcuts) == 1
    assert "DesktopFolder" not in output.read_text()
    assert find("CustomAction") is None
    assert find("Directory").get("Id") == "TARGETDIR"
    assert 'Name="azauthlib"' in output.read_text()
    assert 'Name="app"' in output.read_text()


@pytest.mark.parametrize("version", ["5.0", "../5.0.0", "5.0.0b1", "256.0.0", "5.0.65536"])
def test_invalid_msi_versions_rejected(payload, tmp_path, version):
    with pytest.raises(ValueError):
        native.author(payload, version, tmp_path / "invalid.wxs")


def test_native_progress_forward_rollback_and_action_records(tmp_path):
    compiler_folder = Path(os.environ.get("MSYS2_UCRT64_BIN", "C:/msys64/ucrt64/bin"))
    compiler = compiler_folder / "g++.exe" if sys.platform == "win32" else shutil.which("g++")
    if not compiler or not Path(compiler).is_file():
        pytest.skip("Native C++ compiler is not available")
    env = dict(os.environ)
    env["PATH"] = str(Path(compiler).parent) + os.pathsep + env.get("PATH", "")
    executable = tmp_path / ("progress-test.exe" if sys.platform == "win32" else "progress-test")
    command = [str(compiler), "-std=c++17"]
    if sys.platform == "win32":
        command.append("-static")
    command += [
        str(native.ROOT / ".github/desktop/native/test_windows_progress.cpp"),
        "-o",
        str(executable),
    ]
    subprocess.run(command, env=env, check=True, timeout=60)
    subprocess.run([str(executable)], check=True, timeout=10)
