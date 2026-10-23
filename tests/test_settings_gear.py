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

"""Single-image settings state changes and footer placement, without app mutations."""

import os
from pathlib import Path

from PySide6.QtCore import QMetaObject, QObject, QPoint, QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlEngine, QQmlExpression
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QSignalSpy, QTest

from azauthlib import credentials, profiles
from azauthlib.gui import config_app


def wait_for(predicate):
    for _ in range(200):
        if predicate():
            return
        QTest.qWait(25)
    raise AssertionError("Settings interaction did not settle")


def test_footer_settings_switches_one_original_image_instantly(monkeypatch):
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication([])
    app.setQuitOnLastWindowClosed(False)
    profile = profiles.create_profile("Profile2")
    credentials.save_configuration(
        profile=profile,
        client_id="11111111-1111-1111-1111-111111111111",
        tenant_id="22222222-2222-2222-2222-222222222222",
        auth_method="interactive",
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Do not launch a splash during this UI test")

    monkeypatch.setattr(config_app, "create_startup_splash", forbidden)
    resources = config_app.PackageResources()
    controller = config_app.ConfigurationController(resources, defer_connections=False)
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda values: warnings.extend(v.toString() for v in values))
    main = config_app.load_configuration_qml(engine, resources, controller, show_splash=False)
    try:
        for _ in range(400):
            if main.isVisible() and main.property("startupRevealed"):
                break
            QTest.qWait(25)
        assert main.isVisible()
        button = main.findChild(QObject, "appSettingsButton")
        image = button.property("contentItem")
        assert image.objectName() == "settingsGearImage"
        QTest.mouseMove(main, QPoint(600, 50))
        QTest.qWait(250)
        assert button.isVisible() and button.isEnabled()
        assert button.property("hoverInDuration") == 450
        assert button.property("hoverOutDuration") == 550
        assert button.property("pressDuration") == 450
        assert button.property("releaseDuration") == 550
        assert button.property("pressHoldDuration") == 120
        assert image.opacity() == 1
        images = [
            child
            for child in button.childItems()
            if child.metaObject().className().startswith("QQuickImage")
        ]
        assert len(images) == 1
        position = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
        assert position.x() < 35
        assert position.y() > main.height() - 40
        spy = QSignalSpy(main.settingsRequested)
        for page in ("providers", "connections"):
            if page == "connections":
                QMetaObject.invokeMethod(main, "openConnections")
                QTest.qWait(350)
            assert main.property("currentPage") == page
            assert image.property("source").toString().endswith("settings-gear-raised.svg")
            original_y = image.mapToScene(QPointF(0, 0)).y()
            QTest.mouseMove(main, position)
            assert image.property("source").toString().endswith("settings-gear-hover.svg")
            assert image.opacity() == 1
            QTest.qWait(100)
            assert 0 < button.property("hoverProgress") < 1
            QTest.qWait(450)
            assert image.mapToScene(QPointF(0, 0)).y() < original_y
            QTest.mousePress(main, Qt.LeftButton, Qt.NoModifier, position)
            assert image.property("source").toString().endswith("settings-gear-sunken.svg")
            assert image.opacity() == 1
            QTest.qWait(100)
            assert 0 < button.property("pressProgress") < 1
            QTest.qWait(250)
            assert image.mapToScene(QPointF(0, 0)).y() > original_y
            if os.environ.get("AZAUTHLIB_CAPTURE_SETTINGS") and page == "connections":
                directory = Path(__file__).resolve().parents[1] / ".artifacts" / "settings-gear"
                directory.mkdir(parents=True, exist_ok=True)
                assert main.grabWindow().save(str(directory / "connections-pressed.png"))
            QTest.mouseRelease(main, Qt.LeftButton, Qt.NoModifier, position)
            dialog = main.findChild(QObject, "appSettingsDialog")
            assert not dialog.property("visible")
            assert image.property("source").toString().endswith("settings-gear-sunken.svg")
            wait_for(lambda dialog=dialog: dialog.property("visible"))
            assert dialog.property("openFadeDuration") == 400
            assert dialog.property("openScaleDuration") == 500
            QTest.qWait(180)
            # First-frame shader uploads can outlast the animation sample on a
            # busy GPU. Check eventual visibility, not a wall-clock midpoint.
            wait_for(lambda dialog=dialog: dialog.property("opacity") > 0)
            wait_for(lambda dialog=dialog: dialog.property("opened"))
            QMetaObject.invokeMethod(dialog, "close")
            QTest.qWait(250)
            QTest.mouseMove(main, QPoint(600, 50))
            assert image.property("source").toString().endswith("settings-gear-raised.svg")
            QTest.qWait(650)
            expression = QQmlExpression(
                QQmlEngine.contextForObject(image), image, "status === Image.Ready"
            )
            assert expression.evaluate()[0]
            if os.environ.get("AZAUTHLIB_CAPTURE_SETTINGS") and page == "connections":
                assert main.grabWindow().save(str(directory / "connections-raised.png"))
        assert spy.count() == 2
        # Even a very quick double tap shows the complete press once. The
        # original SVG swaps instantly, but the popup waits for the feedback.
        QTest.mouseClick(main, Qt.LeftButton, Qt.NoModifier, position)
        QTest.mouseClick(main, Qt.LeftButton, Qt.NoModifier, position)
        assert button.property("activationPending")
        assert spy.count() == 2 and not dialog.property("visible")
        assert image.property("source").toString().endswith("settings-gear-sunken.svg")
        QTest.qWait(100)
        assert 0 < button.property("pressProgress") < 1
        assert not dialog.property("visible")
        wait_for(lambda: dialog.property("opened"))
        assert spy.count() == 3
        QMetaObject.invokeMethod(dialog, "close")
        QTest.qWait(650)
        button.forceActiveFocus()
        QTest.keyClick(main, Qt.Key_Space)
        assert spy.count() == 3
        wait_for(lambda: dialog.property("opened"))
        assert spy.count() == 4
        QMetaObject.invokeMethod(dialog, "close")
        QTest.qWait(250)
        # Reduced motion bypasses the click hold and popup animation.
        motion = QQmlExpression(
            QQmlEngine.contextForObject(button),
            button,
            "ConnectionTheme.reduceMotionOverride = true",
        )
        motion.evaluate()
        assert not motion.hasError()
        button.forceActiveFocus()
        QTest.keyClick(main, Qt.Key_Return)
        assert spy.count() == 5
        wait_for(lambda: dialog.property("opened"))
        QMetaObject.invokeMethod(dialog, "close")
        wait_for(lambda: not dialog.property("visible"))
        motion.setExpression("ConnectionTheme.reduceMotionOverride = false")
        motion.evaluate()
        # A queued activation must be discarded if editing disables Settings.
        QTest.mouseClick(main, Qt.LeftButton, Qt.NoModifier, position)
        assert button.property("activationPending")
        controller.connectionManager.beginEdit()
        QTest.qWait(700)
        assert not button.isEnabled()
        assert not button.property("activationPending")
        assert not dialog.property("visible")
        QTest.mouseClick(main, Qt.LeftButton, Qt.NoModifier, position)
        assert spy.count() == 5
        controller.connectionManager.cancelEdit()
        QTest.qWait(100)
        assert button.isEnabled()
        controller.connectionManager.beginAdd()
        QTest.qWait(100)
        save_button = main.findChild(QObject, "managerSaveButton")
        assert save_button.property("text") == "Save connection"
        assert save_button.property("symbol") == "save"
        assert save_button.property("iconSource").toString().endswith("/actions/save.svg")
        assert not save_button.isEnabled()  # Empty drafts still fail validation.
        controller.connectionManager.cancelEdit()
    finally:
        controller.connectionManager.cancelEdit()
        main.setProperty("closingAllowed", True)
        main.close()
        engine.deleteLater()
        controller.deleteLater()
        QTest.qWait(100)
        resources.close()
    assert not warnings, warnings
