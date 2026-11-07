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

"""Real MSI transactions using a unique test product, private files and test-only menu paths."""

import argparse
import ctypes
import json
import os
import subprocess
import uuid
from pathlib import Path

from build_windows_installer import build


def require(value, message):
    if not value:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wix-bin", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    destination = output / "private-installation"
    destination.mkdir()
    sentinel = destination / "user-data.txt"
    sentinel.write_text("User data must survive install, rollback and uninstall.")
    payload = output / "payload"
    payload.mkdir()
    (payload / "azauthlib.exe").write_bytes(b"Inert test file; never execute")
    (payload / "data.txt").write_text("version one")
    for index in range(8):
        (payload / f"chunk-{index}.dat").write_bytes(bytes([index]) * (512 * 1024))
    upgrade_code = "{" + str(uuid.uuid4()) + "}"
    products = []
    report = {
        "status": "failed",
        "scope": "Unique per-user test MSI registration; no production app or profile access",
        "checks": [],
    }
    api = ctypes.WinDLL("msi")
    api.MsiSetInternalUI(2, None)
    uninstall = api.MsiConfigureProductExW
    uninstall.argtypes = [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p]
    state = api.MsiQueryProductStateW
    state.argtypes = [ctypes.c_wchar_p]
    state.restype = ctypes.c_int

    def launch(exe, *flags):
        env = dict(
            os.environ,
            AZAUTHLIB_TEST_CACHE=str(output / "source-cache"),
            AZAUTHLIB_TEST_DEST=str(destination),
            AZAUTHLIB_TEST_TRACE=str(output / "trace.txt"),
            AZAUTHLIB_TEST_LOG=str(output / f"step-{len(report.get('steps', []))}.log"),
        )
        code = subprocess.run([str(exe), *flags], timeout=120, env=env).returncode
        report.setdefault("steps", []).append(
            {"command": [str(exe), *flags], "exit": code, "states": {p: state(p) for p in products}}
        )
        return code

    def package(version):
        exe, _, product = build(
            payload,
            output / version,
            version,
            wix_bin=args.wix_bin,
            test_root=destination,
            upgrade_code=upgrade_code,
        )
        products.append(product)
        return exe

    try:
        first = package("1.0.0")
        require(
            launch(first, "--cancel-during-copy") == 1602,
            "Active cancellation was not acknowledged",
        )
        require(
            not (destination / "app/data.txt").exists(), "Cancelled installation left app files"
        )
        report["checks"].append("cancel during InstallFiles rolls back a fresh installation")
        require(launch(first) == 0, "Immediate setup failed")
        require(state(products[0]) == 5, "First version was not registered as installed")
        require(
            (destination / "app/data.txt").read_text() == "version one",
            "Missing first-version files",
        )
        require(
            list((destination / "menu").glob("*.lnk")), "Start Menu-style shortcut was not authored"
        )
        report["checks"].append("normal EXE installs immediately without choices or app launch")
        (payload / "data.txt").write_text("version two")
        second = package("1.1.0")
        require(
            launch(second, "--fail-after-copy") != 0, "Injected transaction failure did not fail"
        )
        require(
            "after copy: version two" in (output / "trace.txt").read_text(),
            "Failure did not happen after new files were installed",
        )
        require(
            (destination / "app/data.txt").read_text() == "version one",
            "Failed upgrade did not restore previous files",
        )
        require(
            state(products[0]) == 5 and state(products[1]) == -1,
            "Failed upgrade did not preserve the previous product registration",
        )
        report["checks"].append("failure after files are copied restores the previous version")
        require(launch(second, "--cancel-during-copy") == 1602, "Upgrade cancellation failed")
        require(
            (destination / "app/data.txt").read_text() == "version one",
            "Cancelled upgrade lost previous files",
        )
        require(
            state(products[0]) == 5 and state(products[1]) == -1,
            "Cancelled upgrade changed product registration",
        )
        report["checks"].append("cancelled upgrade preserves previous installation")
        require(launch(second) == 0, "Successful upgrade failed")
        require(
            (destination / "app/data.txt").read_text() == "version two",
            "Upgrade did not replace app files",
        )
        require(
            state(products[0]) == -1 and state(products[1]) == 5,
            "Upgrade left an obsolete product registered",
        )
        require(
            uninstall(products[-1], 0, 2, "REMOVE=ALL REBOOT=ReallySuppress") == 0,
            "Test uninstall failed",
        )
        require(not (destination / "app/data.txt").exists(), "Uninstall left managed files")
        require(sentinel.read_text().startswith("User data"), "User data was modified")
        report["checks"].append("upgrade and uninstall preserve adjacent user data")
        trace = (output / "trace.txt").read_text()
        require("MSI progress initialized: 1; rollback: 0" in trace, "Missing forward progress")
        require("MSI progress initialized: 1; rollback: 1" in trace, "Missing rollback progress")
        report["checks"].append("native MSI callbacks report forward and rollback progress")
        report["status"] = "passed"
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        report["cleanup"] = {
            product: uninstall(product, 0, 2, "REMOVE=ALL REBOOT=ReallySuppress")
            for product in reversed(products)
        }
        (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
