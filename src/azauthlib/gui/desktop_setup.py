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

"""Opt-in graphical setup, executed by the downloaded standalone runtime only."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThread, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from . import desktop_install as installer


class InstallWorker(QThread):
    """Keep archive hashing and extraction off the GUI thread."""

    def __init__(self, archive, release, destination, parent):
        super().__init__(parent)
        self.archive, self.release, self.destination = archive, release, destination
        self.executable = self.error = None

    def run(self):
        try:
            self.executable = installer.install_archive(
                self.archive, self.release, self.destination
            )
        except Exception as error:
            self.error = str(error)


def _label(text):
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextFormat(Qt.PlainText)
    label.setTextInteractionFlags(Qt.NoTextInteraction)
    label.setFocusPolicy(Qt.NoFocus)
    return label


class InstallPage(QWizardPage):
    def isComplete(self):
        worker = self.wizard().worker
        return worker is not None and worker.isFinished()


class SetupWizard(QWizard):
    """Choose a fresh per-user folder and optional launcher; never load app profiles."""

    def __init__(self, archive, release, destination, *, shortcut=False):
        super().__init__()
        self.archive, self.release = Path(archive).resolve(), release
        self.worker = self.executable = None
        self.exit_code = 2
        self.setObjectName("desktopSetupWizard")
        self.setWindowTitle("azauthlib Desktop Setup")
        self.setWizardStyle(QWizard.ClassicStyle)
        self.setOption(QWizard.NoBackButtonOnLastPage)
        self.setOption(QWizard.NoBackButtonOnStartPage)
        self.setFixedSize(940, 640)
        self.setSizeGripEnabled(False)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setButtonText(QWizard.CommitButton, "Install")
        self.setFont(QFont("Segoe UI", 10))
        palette = self.palette()
        for role, color in (
            (QPalette.Window, "#0e263e"),
            (QPalette.WindowText, "#edf5ff"),
            (QPalette.Base, "#091e33"),
            (QPalette.Text, "#edf5ff"),
            (QPalette.Button, "#173b56"),
            (QPalette.ButtonText, "#edf5ff"),
            (QPalette.Highlight, "#167d9a"),
            (QPalette.HighlightedText, "#ffffff"),
        ):
            palette.setColor(role, QColor(color))
        self.setPalette(palette)
        self.setStyleSheet(
            "QWizard, QWizardPage { background: #0e263e; color: #edf5ff; }"
            "QWizardPage { border: none; }"
            "QLabel, QCheckBox { color: #b4c9dd; font-size: 13px; background: transparent; }"
            "QLabel#heading { color: #f4f8ff; font-size: 27px; font-weight: 700; }"
            "QLabel#eyebrow { color: #56d7ef; font-size: 10px; font-weight: 700; }"
            "QFrame#setupRail { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #123854, stop:1 #071725); border-right: 1px solid #254b65; }"
            "QFrame#setupPanel { background: #0a2035; border: 1px solid #2c4e68;"
            "border-radius: 12px; }"
            "QLineEdit { background: #071a2b; color: #edf5ff; padding: 12px;"
            "border: 1px solid #3c6683; border-radius: 7px; selection-background-color: #167d9a; }"
            "QLineEdit:focus { border-color: #56d7ef; }"
            "QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #258fac,stop:1 #126780); color: white; padding: 10px 22px;"
            "border: 1px solid #56d7ef; border-radius: 7px; min-width: 74px; font-weight: 600; }"
            "QPushButton:hover { background: #248da8; }"
            "QPushButton:pressed { background: #0d536a; }"
            "QPushButton:disabled { background: #17334a; color: #728da4; border-color: #29495f; }"
            "QPushButton#qt_wizard_cancel, QPushButton#browseFolder { background: #142f47;"
            "border-color: #3c617b; }"
            "QCheckBox { spacing: 10px; padding: 5px 0; color: #edf5ff; }"
            "QProgressBar { background: #071a2b; border: 1px solid #315671;"
            "border-radius: 5px; min-height: 10px; max-height: 10px; }"
            "QProgressBar::chunk { background: #36c3e3; border-radius: 4px; }"
        )
        check = (
            Path(__file__).parents[1]
            / "assets/icons/svg/actions/Monocolor-Filled-Ice-Blue-check.svg"
        ).as_posix()
        self.setStyleSheet(
            self.styleSheet()
            + "QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #60869e;"
            "border-radius: 4px; background: #091e33; }"
            "QCheckBox::indicator:hover { border-color: #56d7ef; }"
            "QCheckBox::indicator:checked { background: #126780; border-color: #56d7ef;"
            f'image: url("{check}"); }}'
        )
        rail = QFrame(self)
        self._rail = rail
        rail.setObjectName("setupRail")
        rail.setFixedWidth(220)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(26, 34, 22, 28)
        rail_layout.setSpacing(22)
        logo = QLabel()
        logo.setPixmap(
            QIcon(
                str(Path(__file__).parents[1] / "assets/logo/svg/azauthlib-wordmark-qt.svg")
            ).pixmap(QSize(172, 56))
        )
        rail_layout.addWidget(logo)
        rail_layout.addWidget(_label(f"DESKTOP COMPANION\nVersion {release.version}"))
        self.steps = []
        for number, title in enumerate(("Set up", "Install", "Ready"), 1):
            label = _label(f"0{number}   {title}")
            label.setMinimumHeight(46)
            self.steps.append(label)
            rail_layout.addWidget(label)
        rail_layout.addStretch()
        rail_layout.addWidget(_label("Your connections.\nYour device.\nYour control."))
        publisher = _label("DOYDL Technologies\ndoydl.studio")
        publisher.setStyleSheet("font-size: 11px; color: #789ab4;")
        rail_layout.addWidget(publisher)
        self.setSideWidget(rail)
        self.currentIdChanged.connect(self._update_steps)

        self.options = QWizardPage()
        self.options.setCommitPage(True)
        layout = QVBoxLayout(self.options)
        layout.setContentsMargins(24, 28, 24, 24)
        layout.setSpacing(18)
        self._heading(
            layout,
            "WELCOME",
            "Install azauthlib Desktop",
            "Set up the optional desktop companion for your Microsoft connections.",
        )
        panel = QFrame()
        panel.setObjectName("setupPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 18, 18, 18)
        panel_layout.setSpacing(12)
        location_label = _label("INSTALLATION FOLDER")
        location_label.setStyleSheet("color: #dbeaf7; font-weight: 600; font-size: 11px;")
        panel_layout.addWidget(location_label)
        row = QHBoxLayout()
        self.location = QLineEdit(str(destination))
        self.location.setObjectName("installationFolder")
        self.location.setToolTip(str(destination))
        self.location.textChanged.connect(self.location.setToolTip)
        location_label.setBuddy(self.location)
        row.addWidget(self.location)
        browse = QPushButton("Browse…")
        browse.setObjectName("browseFolder")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        panel_layout.addLayout(row)
        panel_layout.addWidget(
            _label(
                "Installed for your account only. Choose a new folder; "
                "existing files stay untouched."
            )
        )
        layout.addWidget(panel)
        shortcut_text = (
            "Add to the applications menu and create a Desktop shortcut if available"
            if release.target.system == "linux"
            else "Create a Desktop launcher (can also be added to the Dock)"
            if release.target.system == "macos"
            else "Create a Desktop shortcut"
        )
        self.shortcut = QCheckBox(shortcut_text)
        self.shortcut.setObjectName("createShortcut")
        self.shortcut.setChecked(shortcut)
        layout.addWidget(self.shortcut)
        layout.addWidget(
            _label(
                "Includes everything needed to run—no separate Python installation required. "
                "Your saved profiles and credentials remain unchanged."
            )
        )
        self.options_error = _label("")
        self.options_error.setStyleSheet("color: #ffbe76")
        self.location.textChanged.connect(self.options_error.clear)
        layout.addWidget(self.options_error)
        layout.addStretch()
        legal = _label(
            "Apache-2.0 · Third-party notices included · OS security approval may be required"
        )
        legal.setStyleSheet("font-size: 10px; color: #789ab4;")
        layout.addWidget(legal)
        self.addPage(self.options)

        self.progress_page = InstallPage()
        layout = QVBoxLayout(self.progress_page)
        layout.setContentsMargins(24, 28, 24, 24)
        layout.setSpacing(20)
        self._heading(
            layout,
            "INSTALLING",
            "Getting things ready.",
            "Please keep setup open while we prepare your desktop app.",
        )
        layout.addStretch()
        layout.addWidget(_label("Verifying the bundle and installing application files…"))
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)
        layout.addStretch()
        self.addPage(self.progress_page)

        self.complete = QWizardPage()
        layout = QVBoxLayout(self.complete)
        layout.setContentsMargins(24, 28, 24, 24)
        layout.setSpacing(20)
        self.complete_heading = self._heading(
            layout,
            "READY",
            "You're all set.",
            "azauthlib Desktop is installed and ready when you are.",
        )
        self.result_text = _label("")
        self.result_text.setObjectName("setupResult")
        layout.addWidget(self.result_text)
        self.launch = QCheckBox("Launch azauthlib when I click Finish")
        self.launch.setObjectName("launchAfterSetup")
        self.launch.setChecked(False)
        layout.addWidget(self.launch)
        layout.addStretch()
        self.addPage(self.complete)

    @staticmethod
    def _heading(layout, eyebrow, title, subtitle):
        kicker = _label(eyebrow)
        kicker.setObjectName("eyebrow")
        layout.addWidget(kicker)
        heading = _label(title)
        heading.setObjectName("heading")
        layout.addWidget(heading)
        layout.addWidget(_label(subtitle))
        return heading

    @Slot(int)
    def _update_steps(self, index):
        for number, step in enumerate(self.steps):
            step.setStyleSheet(
                "color: #65def0; font-weight: 700; border-bottom: 1px solid #2d6b83;"
                if number == index
                else "color: #87a7bf;"
            )

    @Slot()
    def _browse(self):
        parent = QFileDialog.getExistingDirectory(self, "Choose the parent installation folder")
        if parent:
            self.location.setText(str(Path(parent) / f"azauthlib-desktop-{self.release.version}"))

    def validateCurrentPage(self):
        if self.currentId() != 0:
            return super().validateCurrentPage()
        try:
            text = self.location.text().strip()
            if not text:
                raise installer.DesktopInstallError("Choose a new installation folder.")
            destination = installer.validate_destination(text)
            if destination.resolve().is_relative_to(self.archive.parent):
                raise installer.DesktopInstallError(
                    "Choose a permanent folder outside the temporary download location."
                )
            if getattr(sys, "frozen", False):
                executable = Path(sys.executable).resolve()
                runtime = (
                    executable.parents[3]
                    if self.release.target.system == "macos"
                    else executable.parent.parent
                )
                if destination.resolve().is_relative_to(runtime):
                    raise installer.DesktopInstallError(
                        "Choose a permanent folder outside the temporary setup runtime."
                    )
            self.destination = destination
        except (OSError, RuntimeError, ValueError) as error:
            self.options_error.setText(str(error))
            return False
        self.options_error.clear()
        return True

    def initializePage(self, page_id):
        super().initializePage(page_id)
        if page_id == 1:
            self.button(QWizard.CancelButton).setEnabled(False)
            self.button(QWizard.NextButton).setEnabled(False)
            self.worker = InstallWorker(self.archive, self.release, self.destination, self)
            self.worker.finished.connect(self._installed)
            self.worker.start()

    @Slot()
    def _installed(self):
        self.executable = self.worker.executable
        if self.worker.error:
            self.exit_code = 1
            self.complete_heading.setText("Setup couldn't finish.")
            self.result_text.setText(self.worker.error)
            self.launch.hide()
        else:
            self.exit_code = 0
            note = (
                f"Installed in:\n{self.destination}\n\n"
                "This app runs without the Python environment used to download it. "
                "Keep its installation folder in place."
            )
            if self.shortcut.isChecked():
                try:
                    note += "\n\n" + installer.create_shortcut(self.executable).message
                except (OSError, RuntimeError) as error:
                    note += f"\n\nThe app was installed, but its shortcut was not created: {error}"
            self.result_text.setText(note)
        self.progress_page.completeChanged.emit()
        self.next()
        self.button(QWizard.CancelButton).setVisible(False)

    def reject(self):
        if self.currentId() == 1:
            return
        if self.worker is not None:
            if self.worker.isRunning():
                return
            # Cancelling after installation must not report that nothing was installed.
            super().accept()
            return
        super().reject()

    def accept(self):
        if self.currentId() == 1 or (self.worker is not None and self.worker.isRunning()):
            return
        if self.executable is not None and self.launch.isChecked() and not self._launch_installed():
            self.result_text.setText(
                f"The app was installed, but could not be started. Open it manually:\n"
                f"{self.executable}"
            )
            self.launch.setChecked(False)
            return
        super().accept()

    def _launch_installed(self):
        try:
            self._launched_process = installer.launch_application(
                self.executable, getattr(self, "_launch_arguments", ())
            )
        except OSError:
            return False
        return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--install-dir", type=Path)
    parser.add_argument("--shortcut", action="store_true")
    args = parser.parse_args(argv)
    target, version = installer.detect_target(), installer.release_version(args.release)
    if version != installer.current_version() or not re.fullmatch(r"[0-9a-f]{64}", args.sha256):
        raise installer.DesktopInstallError("The setup version or checksum is invalid.")
    release = installer.DesktopRelease(
        version, target, "", args.sha256, args.archive.stat().st_size
    )
    from .platform_integration import set_app_id

    set_app_id("doydl-technologies.azauthlib.setup")
    app = QApplication([])
    app.setApplicationName("azauthlib Desktop Setup")
    app.setOrganizationName("DOYDL Technologies")
    app.setOrganizationDomain("doydl.studio")
    app.setWindowIcon(QIcon(str(Path(__file__).parents[1] / "assets/azauthlib-taskbar.ico")))
    wizard = SetupWizard(
        args.archive,
        release,
        args.install_dir or installer.default_destination(version, target),
        shortcut=args.shortcut,
    )
    wizard.show()
    app.exec()
    return wizard.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
