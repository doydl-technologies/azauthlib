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

"""Inspect the connection animation from an editable source checkout without signing in."""

from __future__ import annotations

import argparse
import sys


def create_preview(
    *,
    color: str | None = None,
    loop: bool = False,
    simulate_gui: bool = False,
    gui_only: bool = False,
):
    """Load only the animation/provider, never a connection or application controller."""
    # Keep older white-only launcher commands compatible, but reject removed art
    # before loading QML or attempting any resource access.
    if color not in (None, "white"):
        raise ValueError("Only the white circular connection animation is available")
    from PySide6.QtQml import QQmlApplicationEngine

    from azauthlib.gui.config_app import PackageResources
    from azauthlib.gui.svg_images import ensure_image_providers

    resources = PackageResources()
    engine = QQmlApplicationEngine()
    ensure_image_providers(engine, resources, include_avatars=False)
    properties = {"loopPlayback": loop}
    if gui_only:
        properties["autoPlay"] = True
        document = "ConnectionAnimationSimulation.qml"
    else:
        properties["initialGuiSimulation"] = simulate_gui
        document = "AddConnectionAnimationPreview.qml"
    engine.setInitialProperties(properties)
    engine.load(str(resources.path("gui", "qml", document)))
    if not engine.rootObjects():
        engine.deleteLater()
        resources.close()
        raise RuntimeError("Unable to load the add-connection animation preview")
    return resources, engine, engine.rootObjects()[0]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--color",
        choices=("white",),
        help="White circular artwork (the only supported variant)",
    )
    parser.add_argument("--loop", action="store_true", help="Enable continuous playback on startup")
    views = parser.add_mutually_exclusive_group()
    views.add_argument(
        "--simulate-gui",
        action="store_true",
        help="Also open a sample Connections screen using the real success overlay (no saved data)",
    )
    views.add_argument(
        "--gui-only",
        action="store_true",
        help="Open only the simulated Connections screen, with its own playback controls",
    )
    options = parser.parse_args(argv)

    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuickControls2 import QQuickStyle

    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([sys.argv[0]])
    app.setApplicationName("azauthlib - Add connection animation preview")
    resources, engine, window = create_preview(
        color=options.color,
        loop=options.loop,
        simulate_gui=options.simulate_gui,
        gui_only=options.gui_only,
    )
    try:
        window.show()
        return app.exec()
    finally:
        window.close()
        engine.deleteLater()
        app.processEvents()
        resources.close()


if __name__ == "__main__":
    raise SystemExit(main())
