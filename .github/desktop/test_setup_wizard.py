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

"""Widget setup checks run separately from the QGuiApplication-based QML tests."""

# ruff: noqa: S101 -- Assertions are intentional in this test module.

import hashlib
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest


@pytest.fixture(scope="session")
def app():
    import os

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def wizard(app, tmp_path):
    from azauthlib.gui import desktop_install as installer
    from azauthlib.gui.desktop_setup import SetupWizard

    downloads = tmp_path / "download"
    downloads.mkdir()
    archive = downloads / "test.zip"
    target = installer.DesktopTarget("windows", "x86_64")
    with ZipFile(archive, "w") as data:
        data.writestr("azauthlib/azauthlib.exe", b"MZ test only")
    release = installer.DesktopRelease(
        "5.0.0",
        target,
        "",
        hashlib.sha256(archive.read_bytes()).hexdigest(),
        archive.stat().st_size,
    )
    result = SetupWizard(archive, release, tmp_path / "installation")
    result.show()
    app.processEvents()
    yield result
    if result.worker is not None:
        result.worker.wait()
    result.close()
    app.processEvents()


def finish_install(wizard, app):
    from PySide6.QtTest import QTest

    wizard.next()
    deadline = time.monotonic() + 10
    while wizard.currentId() != 2 and time.monotonic() < deadline:
        QTest.qWait(10)
    assert wizard.currentId() == 2


def test_cancel_does_not_install_or_create_shortcuts(wizard, tmp_path):
    wizard.reject()
    assert wizard.exit_code == 2
    assert not (tmp_path / "installation").exists()


def test_installer_is_fixed_size_and_labels_cannot_be_selected(wizard, app):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel

    assert wizard.minimumSize() == wizard.maximumSize()
    assert not wizard.isSizeGripEnabled()
    assert not wizard.windowFlags() & Qt.WindowMaximizeButtonHint
    original = wizard.size()
    wizard.resize(1200, 800)
    app.processEvents()
    assert wizard.size() == original
    for label in wizard.findChildren(QLabel):
        assert not label.textInteractionFlags() & (
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
    assert not wizard.location.isReadOnly()


def test_completion_keeps_fixed_size_and_nonselectable_result(wizard, app):
    from PySide6.QtCore import Qt

    finish_install(wizard, app)
    assert wizard.minimumSize() == wizard.maximumSize()
    assert wizard.result_text.textInteractionFlags() == Qt.NoTextInteraction


def test_checked_indicator_has_a_visible_checkmark(wizard, app):
    wizard.shortcut.setChecked(True)
    app.processEvents()
    image = wizard.shortcut.grab().toImage()
    scale = image.devicePixelRatio()
    light_pixels = sum(
        image.pixelColor(x, y).red() > 100
        for x in range(int(4 * scale), int(16 * scale))
        for y in range(image.height() // 2 - int(6 * scale), image.height() // 2 + int(6 * scale))
    )
    assert light_pixels > 5


def test_existing_destination_is_preserved(wizard, tmp_path):
    wizard.location.setText(str(tmp_path))
    assert not wizard.validateCurrentPage()
    assert "already exists" in wizard.options_error.text()
    assert wizard.currentId() == 0


def test_cannot_install_in_temporary_download_folder(wizard):
    wizard.location.setText(str(wizard.archive.parent / "will-disappear"))
    assert not wizard.validateCurrentPage()
    assert "permanent folder" in wizard.options_error.text()


def test_install_has_opt_in_defaults_and_no_implicit_shortcut_or_launch(wizard, app, monkeypatch):
    from azauthlib.gui import desktop_install as installer

    def prohibited(*_, **__):
        pytest.fail("Shortcut and launch must both be opt-in")

    monkeypatch.setattr(installer, "create_shortcut", prohibited)
    monkeypatch.setattr(wizard, "_launch_installed", prohibited)
    assert not wizard.shortcut.isChecked()
    assert not wizard.launch.isChecked()
    finish_install(wizard, app)
    assert wizard.exit_code == 0
    assert wizard.executable.is_file()
    wizard.accept()


def test_shortcut_failure_does_not_undo_valid_installation(wizard, app, monkeypatch):
    from azauthlib.gui import desktop_install as installer

    def fail(_):
        raise installer.DesktopInstallError("Existing shortcut was preserved")

    monkeypatch.setattr(installer, "create_shortcut", fail)
    wizard.shortcut.setChecked(True)
    finish_install(wizard, app)
    assert wizard.exit_code == 0
    assert wizard.executable.is_file()
    assert "Existing shortcut was preserved" in wizard.result_text.text()


def test_checksum_error_is_displayed_as_failure_not_success(wizard, app):
    wizard.release = replace(wizard.release, checksum="0" * 64)
    finish_install(wizard, app)
    assert wizard.exit_code == 1
    assert "checksum" in wizard.result_text.text()
    assert wizard.launch.isHidden()
    assert not wizard.destination.exists()


def test_launch_requires_explicit_selection_and_uses_installed_executable(wizard, app, monkeypatch):
    calls = []
    monkeypatch.setattr(
        wizard, "_launch_installed", lambda: calls.append(wizard.executable) or True
    )
    finish_install(wizard, app)
    wizard.launch.setChecked(True)
    wizard.accept()
    assert calls == [wizard.executable]
    assert calls[0].is_relative_to(wizard.destination)


def test_finish_button_launches_and_closes_window(wizard, app, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QWizard

    calls = []
    monkeypatch.setattr(wizard, "_launch_installed", lambda: calls.append(True) or True)
    finish_install(wizard, app)
    wizard.launch.setChecked(True)
    QTest.mouseClick(wizard.button(QWizard.FinishButton), Qt.LeftButton)
    app.processEvents()
    assert calls == [True]
    assert not wizard.isVisible()


def test_launch_failure_keeps_setup_open_with_manual_location(wizard, app, monkeypatch):
    monkeypatch.setattr(wizard, "_launch_installed", lambda: False)
    finish_install(wizard, app)
    wizard.launch.setChecked(True)
    wizard.accept()
    assert wizard.isVisible()
    assert not wizard.launch.isChecked()
    assert str(wizard.executable) in wizard.result_text.text()


def test_closing_finished_wizard_does_not_launch_app(wizard, app, monkeypatch):
    def prohibited():
        pytest.fail("Window close is not consent to launch the app")

    monkeypatch.setattr(wizard, "_launch_installed", prohibited)
    finish_install(wizard, app)
    wizard.launch.setChecked(True)
    wizard.reject()
    assert wizard.exit_code == 0


def test_progress_cannot_be_skipped_or_closed(wizard, app, monkeypatch):
    import threading

    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QWizard

    from azauthlib.gui import desktop_install as installer

    blocked = threading.Event()
    install = installer.install_archive

    def delayed(*args):
        if not blocked.wait(5):
            raise RuntimeError("Test did not release the worker")
        return install(*args)

    monkeypatch.setattr(installer, "install_archive", delayed)
    wizard.next()
    try:
        QTest.qWait(20)
        assert wizard.currentId() == 1
        assert not wizard.progress_page.isComplete()
        assert not wizard.button(QWizard.NextButton).isEnabled()
        assert not wizard.button(QWizard.CancelButton).isEnabled()
        wizard.reject()
        wizard.accept()
        assert wizard.isVisible()
        assert wizard.worker.isRunning()
    finally:
        blocked.set()
        deadline = time.monotonic() + 10
        while wizard.currentId() != 2 and time.monotonic() < deadline:
            QTest.qWait(10)
    assert wizard.exit_code == 0


def test_detached_launch_resets_frozen_runtime_environment(wizard, app, monkeypatch):
    from azauthlib.gui import desktop_setup

    calls = {}

    def launch(executable, arguments):
        calls["program"] = executable
        calls["arguments"] = arguments
        return object()

    monkeypatch.setattr(desktop_setup.installer, "launch_application", launch)
    wizard.executable = Path("C:/installed/azauthlib.exe")
    assert wizard._launch_installed()
    assert calls["program"] == wizard.executable
    assert calls["arguments"] == ()


def test_setup_rejects_wrong_version_before_opening_gui(monkeypatch):
    from azauthlib.gui import desktop_setup

    monkeypatch.setattr(desktop_setup.installer, "detect_target", lambda: SimpleNamespace())
    with pytest.raises(RuntimeError, match="version or checksum"):
        desktop_setup.main(["--archive", "test.zip", "--sha256", "0" * 64, "--release", "9.9.9"])
