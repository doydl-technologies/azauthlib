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

"""Validate the installed desktop without live authentication or user storage.

The startup component is inspected without showing a splash. Network and
credential-store access are blocked or replaced with in-memory test doubles.
Linux needs X11 (CI supplies Xvfb). Windows/macOS use their native Qt plugins.
This is not a Wayland, desktop-shell, live-authentication, or signing test.
"""

from __future__ import annotations

import argparse
import faulthandler
import json
import logging
import os
import platform
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
LOG = logging.getLogger("desktop-smoke")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def find_item(parent, name):
    # Qt 6 Repeater delegates sometimes have only visual, not QObject ownership.
    from PySide6.QtCore import QObject

    found = parent.findChild(QObject, name)
    if found is not None:
        return found
    for child in parent.childItems() if hasattr(parent, "childItems") else []:
        if child.objectName() == name:
            return child
        if found := find_item(child, name):
            return found
    return None


def run_checks(installed, artifacts, report):
    sys.path.insert(0, str(installed))
    import PySide6
    from PySide6.QtCore import QObject, QPointF, Qt, QUrl, Slot
    from PySide6.QtGui import QDesktopServices, QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtTest import QTest

    import azauthlib
    from azauthlib import credentials, profiles
    from azauthlib.gui import config_app, connections, shortcuts

    require(
        Path(azauthlib.__file__).resolve().is_relative_to(installed),
        "Smoke test imported source checkout instead of installed wheel",
    )
    expected_qpa = {"win32": "windows", "darwin": "cocoa"}.get(sys.platform, "xcb")
    os.environ.setdefault("QT_QPA_PLATFORM", expected_qpa)
    os.environ.setdefault("QT_SCALE_FACTOR", "0.85")
    screenshots = artifacts / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)

    external_urls = []

    class UrlCapture(QObject):
        @Slot(QUrl)
        def opened(self, url):
            external_urls.append(url.toString())

    def prohibited(*_args, **_kwargs):
        raise AssertionError("Splash/authentication/network access is forbidden in CI smoke checks")

    def wait_for(predicate, description):
        for _ in range(1200):
            if predicate():
                return
            QTest.qWait(25)
        require(predicate(), "Timed out: " + description)

    main = engine = resources = startup = app = None
    previous_cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="azauthlib-desktop-ci-") as temporary:
        temp = Path(temporary)
        runtime = temp / "runtime"
        runtime.mkdir(mode=0o700)
        with (
            patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(runtime)}),
            patch.object(profiles, "get_config_dir", lambda **_: temp / "config"),
            patch.object(profiles, "get_cache_dir", lambda **_: temp / "cache"),
            patch.object(config_app, "get_config_dir", lambda **_: temp / "config"),
            patch.object(config_app, "create_startup_splash", prohibited),
            patch.object(connections, "test_saved_connection", prohibited),
            patch("socket.create_connection", prohibited),
            patch("requests.sessions.Session.request", prohibited),
        ):
            secrets = {}
            with (
                patch.object(
                    credentials.keyring,
                    "get_password",
                    lambda service, client: secrets.get((service, client)),
                ),
                patch.object(
                    credentials.keyring,
                    "set_password",
                    lambda service, client, value: secrets.update({(service, client): value}),
                ),
                patch.object(
                    credentials.keyring,
                    "delete_password",
                    lambda service, client: secrets.pop((service, client), None),
                ),
            ):
                QQuickStyle.setStyle("Basic")
                app = QGuiApplication([])
                app.setQuitOnLastWindowClosed(False)
                report.update(
                    pyside=PySide6.__version__,
                    qt_platform=app.platformName(),
                    installed_module=str(Path(azauthlib.__file__).resolve()),
                )
                require(app.platformName() == expected_qpa, "Native Qt platform plugin not active")
                # Native stderr avoids a Python callback deadlocking the QML loader
                # while another thread holds the GIL. Engine warnings still fail below.
                capture = UrlCapture()
                for scheme in ("https", "http", "mailto"):
                    QDesktopServices.setUrlHandler(scheme, capture, "opened")
                warnings = []
                try:
                    os.chdir(temp)  # Prove resource loading does not depend on checkout cwd.
                    profile = profiles.create_profile("CI temporary profile", select=False)
                    profile = profiles.rename_profile(profile, "CI renamed profile")
                    profiles.remove_profile(profile)
                    require(
                        profile.id not in {p.id for p in profiles.list_profiles()},
                        "Temporary profile removal failed",
                    )
                    report["checks"].append("temporary profile create/rename/remove")
                    resources = config_app.PackageResources()
                    shortcut_desktop = temp / "shortcut-desktop"
                    shortcut_desktop.mkdir()
                    shortcut = shortcuts.create_app_shortcut(
                        desktop_dir=shortcut_desktop,
                        icon_path=resources.path("assets", config_app._TASKBAR_ICON_NAME),
                        data_dir=temp / "shortcut-assets",
                        applications_dir=temp / "shortcut-applications",
                    )
                    require(
                        all(path.exists() and path.is_relative_to(temp) for path in shortcut.paths),
                        "Native launcher was not created inside the temporary test directory",
                    )
                    report["checks"].append("native app shortcut creation (temporary folders only)")
                    controller = config_app.ConfigurationController(resources)
                    require(
                        set(controller.legalDocuments) == {"terms", "privacy"},
                        "Bundled policies missing",
                    )
                    require(
                        set(controller.legalDocumentUrls) == {"terms", "privacy"},
                        "Policies fell back to unavailable notices",
                    )

                    def check_windows_identity(window):
                        if sys.platform != "win32":
                            return
                        from azauthlib.gui.windows_taskbar import _WindowPropertyStore

                        with _WindowPropertyStore(int(window.winId())) as store:
                            require(
                                store.get_string(5) == config_app._APP_ID,
                                "Windows shell application identity missing",
                            )
                            require(
                                store.get_string(3)
                                == str(
                                    resources.path(
                                        "assets", config_app._TASKBAR_ICON_NAME
                                    ).resolve()
                                )
                                + ",0",
                                "Windows shell icon missing",
                            )

                    config_app.configure_application_identity(app, resources)
                    require(
                        app.organizationDomain() == "doydl.studio",
                        "Application organization domain is incorrect",
                    )
                    report["checks"].append("application organization domain")
                    engine = QQmlApplicationEngine()
                    engine.warnings.connect(
                        lambda values: warnings.extend(value.toString() for value in values)
                    )
                    # Inspect startup flags/icon without ever showing a splash window.
                    component = QQmlComponent(
                        engine,
                        QUrl.fromLocalFile(
                            str(resources.path("gui", "qml", "components", "StartupSplash.qml"))
                        ),
                    )
                    startup = component.createWithInitialProperties(
                        {
                            "visible": False,
                            "previewMode": True,
                            "logoSource": QUrl.fromLocalFile(
                                str(resources.path("assets", config_app._STARTUP_LOGO))
                            ),
                        }
                    )
                    require(isinstance(startup, QQuickWindow), "Startup QML failed to load")
                    config_app.configure_window_taskbar_identity(startup, resources)
                    require(
                        not startup.isVisible() and not startup.icon().isNull(),
                        "Hidden startup icon missing",
                    )
                    require(
                        startup.flags() & Qt.WindowType_Mask == Qt.Window
                        and not startup.flags() & Qt.WindowStaysOnTopHint,
                        "Unexpected startup window flags",
                    )
                    check_windows_identity(startup)
                    startup.destroy()
                    report["checks"].append("hidden startup identity (splash never shown)")
                    main = config_app.load_configuration_qml(
                        engine, resources, controller, show_splash=False
                    )
                    home = find_item(main, "providerSelectorHome")
                    connections_page = find_item(main, "connectionManagerWindow")
                    wait_for(
                        lambda: (
                            main.isVisible()
                            and main.opacity() == 1
                            and main.property("startupRevealed")
                            and home.property("ready")
                            and not main.property("navigationLocked")
                        ),
                        "installed GUI startup",
                    )
                    require(main.property("startupSplash") is None, "Splash unexpectedly created")
                    require(home.property("loadedLogoCount") == 6, "Some provider logos failed")
                    require(
                        controller.connectionsDeferred and not connections_page.property("opened"),
                        "Connections should load only after a service is opened",
                    )
                    require(not main.icon().isNull(), "Application icon missing")
                    check_windows_identity(main)
                    report["checks"].extend(
                        [
                            "installed-wheel startup",
                            "six original provider logos",
                            "deferred Connections startup",
                            "application icon",
                        ]
                    )
                    report["graphics_api"] = str(main.rendererInterface().graphicsApi())
                    require(
                        "Software" not in report["graphics_api"],
                        "Qt software scene graph cannot validate the custom shaders",
                    )

                    def snapshot(name):
                        QTest.qWait(150)
                        frame = main.grabWindow()
                        require(not frame.isNull(), "Unable to capture native window")
                        require(
                            frame.save(str(screenshots / (name + ".png"))),
                            "Unable to save screenshot",
                        )

                    def click(name):
                        item = find_item(main, name)
                        require(
                            item is not None
                            and item.property("visible")
                            and item.property("enabled"),
                            "Control unavailable: " + name,
                        )
                        point = item.mapToScene(
                            QPointF(item.width() / 2, item.height() / 2)
                        ).toPoint()
                        QTest.mouseClick(main, Qt.LeftButton, Qt.NoModifier, point)
                        QTest.qWait(100)

                    def check_drawers(page, prefix):
                        for topic, link in (
                            ("terms", "footerTermsLink"),
                            ("privacy", "footerPrivacyLink"),
                            ("about", "footerAboutLink"),
                        ):
                            click(link)
                            wait_for(
                                lambda expected=topic: page.property("drawerTopic") == expected,
                                prefix + " " + topic + " drawer",
                            )
                            QTest.qWait(650)
                            snapshot(prefix + "-" + topic)
                            QTest.keyClick(main, Qt.Key_Escape)
                            wait_for(lambda: page.property("drawerTopic") == "", "drawer close")
                            QTest.qWait(650)
                        report["checks"].append(prefix + " Terms/Privacy/About drawers")

                    snapshot("home")
                    check_drawers(home, "home")
                    click("providerContinueButton")
                    wait_for(
                        lambda: (
                            main.property("currentPage") == "connections"
                            and connections_page.property("opened")
                            and controller.connectionsReady
                            and not main.property("navigationLocked")
                        ),
                        "Connections navigation",
                    )
                    snapshot("connections")
                    check_drawers(connections_page, "connections")
                    click("connectionsBackHomeButton")
                    wait_for(
                        lambda: (
                            main.property("currentPage") == "providers"
                            and not main.property("navigationLocked")
                        ),
                        "return to Home",
                    )
                    report["checks"].append("Home/Connections round-trip navigation")
                    require(not warnings, "QML warnings: " + "\n".join(warnings))
                    require(not external_urls, "Unexpected external URL activation")
                    report["checks"].append("no QML warnings")
                except Exception:
                    if main is not None and main.isVisible():
                        main.grabWindow().save(str(screenshots / "failure.png"))
                    raise
                finally:
                    if main is not None:
                        main.setProperty("closingAllowed", True)
                        main.close()
                        main.destroy()
                    if startup is not None:
                        startup.destroy()
                        startup.deleteLater()
                    if engine is not None:
                        engine.deleteLater()
                    app.processEvents()
                    if resources is not None:
                        resources.close()
                    for scheme in ("https", "http", "mailto"):
                        QDesktopServices.unsetUrlHandler(scheme)
                    (artifacts / "qml-warnings.log").write_text(
                        "\n".join(warnings), encoding="utf-8"
                    )
                    os.chdir(previous_cwd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args(argv)
    artifacts = args.artifacts.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(artifacts / "smoke.log", encoding="utf-8"),
        ],
    )
    report = {
        "status": "failed",
        "system": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version,
        "checks": [],
        "scope": "No live authentication/keyring, "
        "splash display, Wayland, signing, or interactive desktop-shell checks.",
    }
    try:
        faulthandler.enable()
        faulthandler.dump_traceback_later(120, exit=True)
        run_checks(args.installed.resolve(), artifacts, report)
        report["status"] = "passed"
        LOG.info("Native installed-wheel GUI checks passed: %s", report["checks"])
        return 0
    except Exception as error:
        report["error"] = str(error)
        LOG.exception("Native GUI checks failed")
        return 1
    finally:
        faulthandler.cancel_dump_traceback_later()
        (artifacts / "smoke-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
