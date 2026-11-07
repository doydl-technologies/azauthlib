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

"""Exercise graphical setup only in the caller's temporary validation directory."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import socket
import sys
import time
from pathlib import Path
from unittest.mock import patch


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check(archive, checksum, artifacts, report):
    from PySide6.QtCore import QEventLoop, Qt, QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QWizard

    from azauthlib.gui import desktop_install as installer
    from azauthlib.gui.desktop_setup import SetupWizard
    from azauthlib.gui.shortcuts import create_app_shortcut

    target, version = installer.detect_target(), installer.current_version()
    downloads = artifacts / "download"
    downloads.mkdir()
    archive = Path(shutil.copy2(archive, downloads / archive.name))
    release = installer.DesktopRelease(version, target, "", checksum, archive.stat().st_size)
    installer.verify_archive(archive, release)
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(
        QIcon(str(Path(installer.__file__).parents[1] / "assets/azauthlib-taskbar.ico"))
    )
    destination = artifacts / "installation"
    desktop = artifacts / "shortcut-desktop"
    desktop.mkdir()
    shortcut_calls = []

    def shortcut(executable):
        shortcut_calls.append(executable)
        return create_app_shortcut(
            desktop_dir=desktop,
            icon_path=Path(installer.__file__).parents[1] / "assets/azauthlib-taskbar.ico",
            executable=executable,
            standalone=True,
            data_dir=artifacts / "shortcut-data",
            applications_dir=artifacts / "shortcut-applications",
        )

    def prohibited(*_args, **_kwargs):
        raise AssertionError("Setup checks must not contact the network or launch the real app")

    with (
        patch.object(socket.socket, "connect", prohibited),
        patch.object(installer, "create_shortcut", shortcut),
        patch.object(SetupWizard, "_launch_installed", prohibited),
    ):
        cancel = SetupWizard(archive, release, destination)
        cancel.show()
        QTest.qWait(100)
        QTest.mouseClick(cancel.button(QWizard.CancelButton), Qt.LeftButton)
        require(not destination.exists(), "Cancelling setup created an installation")
        require(not shortcut_calls, "Cancelling setup created a shortcut")
        report["checks"].append("cancel before installation has no install/shortcut side effects")

        wizard = SetupWizard(archive, release, artifacts)
        wizard.show()
        QTest.qWait(100)
        require(not wizard.shortcut.isChecked(), "Shortcut must be opt-in")
        require(not wizard.launch.isChecked(), "App launch must be opt-in")
        QTest.mouseClick(wizard.button(QWizard.CommitButton), Qt.LeftButton)
        require(wizard.currentId() == 0, "Existing folder was accepted")
        require(bool(wizard.options_error.text()), "No existing-folder explanation was shown")
        report["checks"].append("existing-folder refusal and opt-in defaults")
        wizard.location.setText(str(destination))
        wizard.shortcut.setChecked(True)
        wizard.grab().save(str(artifacts / "setup-options.png"))
        ticks = []
        timer = QTimer()
        timer.timeout.connect(lambda: ticks.append(True))
        timer.start(10)
        QTest.mouseClick(wizard.button(QWizard.CommitButton), Qt.LeftButton)
        require(wizard.currentId() == 1, "Install did not open the progress page")
        require(not wizard.button(QWizard.NextButton).isEnabled(), "Progress can be skipped")
        wizard.reject()
        require(wizard.isVisible(), "Running setup can be closed while files are being written")
        wizard.grab().save(str(artifacts / "setup-installing.png"))
        # A native event loop releases the GIL while waiting. Repeated qWait()
        # calls can starve Python file-copy workers during a large extraction.
        loop = QEventLoop()
        wizard.worker.finished.connect(loop.quit)
        deadline = QTimer()
        deadline.setSingleShot(True)
        deadline.timeout.connect(loop.quit)
        deadline.start(300_000)
        if not wizard.worker.isFinished():
            loop.exec()
        deadline.stop()
        app.processEvents()
        timer.stop()
        if wizard.worker.isRunning():
            wizard.worker.wait()
        require(wizard.currentId() == 2, "Installation did not reach its result page")
        require(wizard.exit_code == 0, wizard.result_text.text())
        require(bool(ticks), "Setup did not process GUI events during installation")
        executable = destination / target.root_name / target.executable
        require(executable.is_file(), "Setup did not install the executable")
        require(shortcut_calls == [executable], "Shortcut did not target the installed executable")
        require(bool(list(desktop.iterdir())), "Native temporary shortcut was not created")
        require(not list(destination.parent.glob(".azauthlib-desktop-*")), "Staging files remain")
        wizard.grab().save(str(artifacts / "setup-complete.png"))
        QTest.mouseClick(wizard.button(QWizard.FinishButton), Qt.LeftButton)
        require(not wizard.isVisible(), "Finish did not close setup")
        report["checks"].extend(
            [
                "verified archive installed through graphical wizard",
                "responsive worker-thread installation and protected progress page",
                "native shortcut in temporary folders only",
                "Finish does not launch the app unless explicitly selected",
            ]
        )
    app.processEvents()
    # Exercise the real Finish handoff from this runtime to the installed one.
    # The explicit child self-check uses isolated stores, never real sign-in.
    launch_probe = SetupWizard(archive, release, destination)
    launch_probe.setStartId(2)
    launch_probe.restart()
    launch_probe.executable = executable
    launch_probe.exit_code = 0
    launch_probe._launch_arguments = ("--desktop-self-check", str(artifacts / "launch-check"))
    launch_probe.launch.setChecked(True)
    launch_probe.show()
    QTest.qWait(100)
    QTest.mouseClick(launch_probe.button(QWizard.FinishButton), Qt.LeftButton)
    require(not launch_probe.isVisible(), "Finish with launch selected did not close the installer")
    child_report = artifacts / "launch-check/smoke-report.json"
    deadline = time.monotonic() + 180
    while not child_report.exists() and time.monotonic() < deadline:
        QTest.qWait(50)
    require(child_report.is_file(), "The installed app did not complete its isolated launch check")
    require(
        json.loads(child_report.read_text())["status"] == "passed", "Installed child startup failed"
    )
    launch_probe._launched_process.wait(timeout=30)
    report["checks"].append(
        "real Finish click closes setup and starts installed child independently"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args(argv)
    args.artifacts.mkdir(parents=True, exist_ok=True)
    report = {"status": "failed", "system": platform.platform(), "checks": []}
    try:
        check(args.archive.resolve(), args.sha256, args.artifacts.resolve(), report)
        report["status"] = "passed"
        return 0
    except Exception as error:
        report["error"] = str(error)
        if sys.stderr is not None:
            import traceback

            traceback.print_exc()
        return 1
    finally:
        (args.artifacts / "setup-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    raise SystemExit(main())
