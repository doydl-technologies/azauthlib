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

"""Test cross-process activation with temporary locks and no startup splash."""

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QMetaObject, QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest

from azauthlib.gui import config_app
from azauthlib.gui.gui_utils import enforce_single_instance, on_exit
from azauthlib.gui.single_instance import SingleInstance

PEER = """
import json, os, sys
from PySide6.QtCore import QCoreApplication
from azauthlib.gui.single_instance import SingleInstance
from azauthlib.gui import platform_integration
platform_integration.allow_foreground_activation = lambda pid: None
app = QCoreApplication([])
guard = SingleInstance(sys.argv[1])
primary = guard.start(timeout_ms=3000)
print(json.dumps(dict(primary=primary, forwarded=guard.forwarded)), flush=True)
if len(sys.argv) > 2 and sys.argv[2] == 'crash':
    os._exit(0)
guard.close()
"""


@pytest.mark.parametrize(
    "reply,delay,expected",
    [
        (b"ok\n", False, True),
        (b"ok\n", True, True),
        (b"x" * 65 + b"\n", False, False),
        (b"ok", False, False),
    ],
)
def test_forward_reads_buffered_reply_even_when_wait_reports_disconnect(
    monkeypatch, reply, delay, expected
):
    from time import monotonic

    from azauthlib.gui import single_instance

    states = single_instance.QLocalSocket.LocalSocketState

    class BufferedSocket:
        LocalSocketState = states

        def __init__(self):
            self.buffer = b""
            self.pending = b""
            self.closed = False
            self.delayed = delay

        def connectToServer(self, _name):
            pass

        def waitForConnected(self, _timeout):
            return True

        def write(self, value):
            self.pending = b"123\n" if value == b"hello\n" else reply

        def flush(self):
            pass

        def canReadLine(self):
            return b"\n" in self.buffer

        def waitForReadyRead(self, _timeout):
            if self.delayed:
                self.delayed = False
                return False
            self.buffer += self.pending
            self.closed = self.pending == reply
            self.pending = b""
            return False

        def state(self):
            return states.UnconnectedState if self.closed else states.ConnectedState

        def bytesAvailable(self):
            return len(self.buffer)

        def readLine(self):
            value, self.buffer = self.buffer, b""
            return value

        def abort(self):
            self.closed = True

    monkeypatch.setattr(single_instance, "QLocalSocket", BufferedSocket)
    monkeypatch.setattr(
        single_instance.platform_integration, "allow_foreground_activation", lambda _pid: None
    )
    assert (
        SingleInstance._forward(SimpleNamespace(server_name="test-only"), monotonic() + 1)
        is expected
    )


@pytest.fixture
def qt_app():
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app


def peer(lockfile, *args):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    return subprocess.Popen(
        [sys.executable, "-c", PEER, str(lockfile), *args],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def collect(process):
    for _ in range(400):
        if process.poll() is not None:
            break
        QTest.qWait(25)  # Owner keeps servicing local messages on its GUI thread.
    if process.poll() is None:
        process.kill()
        process.communicate()
        pytest.fail("Local activation peer timed out")
    output, error = process.communicate()
    assert process.returncode == 0 and not error, (output, error)
    return json.loads(output)


def test_rapid_relaunches_activate_owner_and_never_acquire_another_lock(qt_app, tmp_path):
    lockfile = tmp_path / "app.lock"
    owner = SingleInstance(lockfile)
    activations = []
    owner.activationRequested.connect(lambda: activations.append(True))
    assert owner.start()
    peers = []
    try:
        peers = [peer(lockfile) for _ in range(5)]
        assert [collect(p) for p in peers] == [dict(primary=False, forwarded=True)] * 5
        assert len(activations) == 5
        assert enforce_single_instance(lockfile) is None
    finally:
        for process in peers:
            if process.poll() is None:
                process.kill()
                process.communicate()
        owner.close()
    replacement = SingleInstance(lockfile)
    try:
        assert replacement.start()
    finally:
        replacement.close()


def test_crashed_owner_does_not_block_next_launch(qt_app, tmp_path):
    lockfile = tmp_path / "crashed.lock"
    assert collect(peer(lockfile, "crash")) == dict(primary=True, forwarded=False)
    replacement = SingleInstance(lockfile)
    try:
        assert replacement.start()
    finally:
        replacement.close()


def test_busy_or_legacy_owner_never_spawns_another_ui(qt_app, tmp_path):
    lockfile = tmp_path / "legacy.lock"
    held = enforce_single_instance(lockfile)
    secondary = SingleInstance(lockfile)
    try:
        assert not secondary.start(timeout_ms=100)
        assert not secondary.forwarded
        assert not secondary._server.isListening()
        secondary.close()
        assert enforce_single_instance(lockfile) is None
    finally:
        secondary.close()
        on_exit(held)


@pytest.mark.parametrize("forwarded", [False, True])
def test_secondary_exits_before_assets_splash_or_controllers(monkeypatch, tmp_path, forwarded):
    calls = []
    guard = SimpleNamespace(
        start=lambda: False, forwarded=forwarded, close=lambda: calls.append("closed")
    )
    monkeypatch.setattr(config_app, "_set_windows_app_id", lambda: None)
    monkeypatch.setattr(config_app.QQuickStyle, "setStyle", lambda _: None)
    monkeypatch.setattr(config_app, "QGuiApplication", lambda _: object())
    monkeypatch.setattr(config_app, "get_config_dir", lambda **_: tmp_path)
    monkeypatch.setattr(config_app, "SingleInstance", lambda *_: guard)

    def forbidden(*_args, **_kwargs):
        pytest.fail("A secondary launch must not prepare assets, splash or startup state")

    for name in ("PackageResources", "create_startup_splash", "StartupBootstrap"):
        monkeypatch.setattr(config_app, name, forbidden)
    assert config_app.main() == (0 if forwarded else 1)
    assert calls == ["closed"]


def test_primary_claims_before_splash_and_keeps_lock_until_shutdown(monkeypatch, tmp_path):
    calls = []
    signal = SimpleNamespace(connect=lambda *_: None)
    app = SimpleNamespace(aboutToQuit=signal, exec=lambda: calls.append("exec") or 0)
    guard = SimpleNamespace(
        start=lambda: calls.append("claim") or True,
        forwarded=False,
        activationRequested=signal,
        close=lambda: calls.append("release"),
    )
    resources = SimpleNamespace(close=lambda: calls.append("resources-close"))
    bootstrap = SimpleNamespace(
        start_after_first_frame=lambda: calls.append("schedule"),
        shutdown=lambda: calls.append("shutdown"),
        activate=lambda: None,
    )
    monkeypatch.setattr(config_app, "_set_windows_app_id", lambda: None)
    monkeypatch.setattr(config_app.QQuickStyle, "setStyle", lambda _: None)
    monkeypatch.setattr(config_app, "QGuiApplication", lambda _: app)
    monkeypatch.setattr(config_app, "get_config_dir", lambda **_: tmp_path)
    monkeypatch.setattr(config_app, "SingleInstance", lambda *_: guard)
    monkeypatch.setattr(
        config_app, "PackageResources", lambda: calls.append("resources") or resources
    )
    monkeypatch.setattr(config_app, "configure_application_identity", lambda *_: None)
    monkeypatch.setattr(
        config_app, "QQmlApplicationEngine", lambda: SimpleNamespace(warnings=signal)
    )
    monkeypatch.setattr(
        config_app, "create_startup_splash", lambda *_: calls.append("splash") or object()
    )
    monkeypatch.setattr(config_app, "StartupBootstrap", lambda *_: bootstrap)
    assert config_app.main() == 0
    assert calls == [
        "claim",
        "resources",
        "splash",
        "schedule",
        "exec",
        "shutdown",
        "release",
        "resources-close",
    ]


def test_relaunch_restores_real_minimized_window_and_preserves_unsaved_form(
    qt_app,
    monkeypatch,
    tmp_path,
):
    def forbidden(*_args, **_kwargs):
        pytest.fail("Native activation validation must not open the production splash")

    monkeypatch.setattr(config_app, "create_startup_splash", forbidden)
    resources = config_app.PackageResources()
    controller = config_app.ConfigurationController(resources)
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(v.toString() for v in items))
    main = config_app.load_configuration_qml(engine, resources, controller, show_splash=False)
    owner = SingleInstance(tmp_path / "native.lock")
    bootstrap = SimpleNamespace(window=main, splash=None)
    owner.activationRequested.connect(lambda: config_app.StartupBootstrap.activate(bootstrap))
    try:
        for _ in range(400):
            if main.isVisible() and main.findChild(QObject, "managerNameField"):
                break
            QTest.qWait(25)
        assert main.isVisible()
        QMetaObject.invokeMethod(main, "openConnections")
        QTest.qWait(300)
        assert main.property("currentPage") == "connections"
        controller.connectionManager.beginAdd()
        field = main.findChild(QObject, "managerNameField")
        assert field is not None
        field.setProperty("text", "Unfinished local draft")
        assert owner.start()
        original_roots = list(engine.rootObjects())
        main.showMinimized()
        QTest.qWait(100)
        assert main.windowState() == Qt.WindowMinimized
        assert collect(peer(tmp_path / "native.lock")) == dict(primary=False, forwarded=True)
        QTest.qWait(100)
        assert main.windowState() == Qt.WindowNoState and main.isVisible()
        assert list(engine.rootObjects()) == original_roots
        assert controller.connectionManager.creatingConnection
        assert field.property("text") == "Unfinished local draft"
        assert main.property("currentPage") == "connections"
    finally:
        owner.close()
        owner.activationRequested.disconnect()
        owner.deleteLater()
        main.setProperty("closingAllowed", True)
        main.close()
        engine.deleteLater()
        controller.deleteLater()
        QTest.qWait(100)
        resources.close()
    assert not warnings, warnings


@pytest.mark.parametrize(
    "loading,minimized,modal",
    [
        (False, False, False),
        (False, True, False),
        (True, False, False),
        (False, False, True),
    ],
)
def test_activation_restores_existing_window_without_resetting_state(
    monkeypatch,
    loading,
    minimized,
    modal,
):
    calls = []

    def window(name, visible, state=Qt.WindowNoState):
        return SimpleNamespace(
            isVisible=lambda: visible,
            windowState=lambda: state,
            showNormal=lambda: calls.append((name, "restore")),
            raise_=lambda: calls.append((name, "raise")),
            requestActivate=lambda: calls.append((name, "activate")),
        )

    main = window("main", not loading, Qt.WindowMinimized if minimized else Qt.WindowNoState)
    splash = window("splash", loading)
    dialog = window("dialog", True) if modal else None
    monkeypatch.setattr(config_app, "QGuiApplication", SimpleNamespace(modalWindow=lambda: dialog))
    monkeypatch.setattr(config_app.platform_integration, "activate_window", lambda _: None)
    bootstrap = SimpleNamespace(window=main, splash=splash)
    config_app.StartupBootstrap.activate(bootstrap)
    target = "dialog" if modal else "splash" if loading else "main"
    expected = [(target, "restore")] if minimized else []
    assert calls == expected + [(target, "raise"), (target, "activate")]
