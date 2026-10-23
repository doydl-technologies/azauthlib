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

"""Thin rules retain coverage while moving through fractional screen positions."""

import pytest


@pytest.mark.parametrize("zoom", [0.7, 0.9, 1.0, 1.15, 1.25])
def test_divider_blends_fractional_scroll_without_dropping_pixels(monkeypatch, zoom):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QObject, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
    from PySide6.QtTest import QTest

    from azauthlib.gui.config_app import PackageResources

    app = QGuiApplication.instance() or QGuiApplication([])
    resources = PackageResources()
    engine = QQmlApplicationEngine()
    component = QQmlComponent(engine)
    base = resources.path("gui", "qml", "components", "ConnectionDivider.qml").with_name(
        "DividerScrollProbe.qml"
    )
    component.setData(
        b"""
        import QtQuick
        import QtQuick.Window
        Window {
            id: window
            width: 160; height: 70; visible: true; color: "black"
            property real offset: 0
            property real zoom: 1
            Item {
                x: 10; y: 10 - window.offset
                scale: window.zoom; transformOrigin: Item.TopLeft
                ConnectionDivider {
                    objectName: "divider"
                    y: 10; width: 100; color: "white"
                    contentScale: window.zoom
                }
            }
        }
        """,
        QUrl.fromLocalFile(str(base)),
    )
    window = component.createWithInitialProperties({"zoom": zoom})
    assert window is not None, "\n".join(error.toString() for error in component.errors())
    try:
        divider = window.findChild(QObject, "divider")
        stroke = window.findChild(QObject, "dividerStroke")
        assert divider.property("implicitHeight") == 1
        assert stroke.property("height") == divider.property("physicalStroke") + 1
        assert divider.property("strokeHeight") * divider.property("physicalScale") >= 1
        energies, centers = [], []
        for offset in (index / 8 for index in range(9)):
            window.setProperty("offset", offset)
            QTest.qWait(25)
            image = window.grabWindow()
            assert not image.isNull()
            dpr = image.width() / window.width()
            x = round(35 * dpr)
            samples = [image.pixelColor(x, y).redF() for y in range(image.height())]
            energy = sum(samples)
            assert energy > 0
            energies.append(energy)
            centers.append(sum(y * weight for y, weight in enumerate(samples)) / energy / dpr)
        # Constant coverage prevents blinking; smoothly shifting coverage avoids
        # turning subpixel scrolling into repeated whole-pixel position jumps.
        assert max(energies) - min(energies) < 0.08, (
            zoom,
            dpr,
            divider.property("physicalScale"),
            divider.property("strokeHeight"),
            energies,
            centers,
        )
        for previous, current in zip(centers, centers[1:], strict=False):
            assert previous - current == pytest.approx(0.125, abs=0.04), centers
    finally:
        window.close()
        window.deleteLater()
        engine.deleteLater()
        app.processEvents()
        resources.close()
