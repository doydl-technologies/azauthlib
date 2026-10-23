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

"""PySide6 and Qt Quick configuration application for azauthlib."""

from __future__ import annotations

import atexit
import os
import re
import sys
from contextlib import ExitStack, suppress
from importlib.resources import as_file, files
from pathlib import Path
from threading import Event, Thread
from uuid import UUID

from PySide6.QtCore import Property, QObject, QPoint, QStandardPaths, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import (
    QCursor,
    QDesktopServices,
    QFont,
    QGuiApplication,
    QIcon,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickTextDocument, QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
from shiboken6 import isValid

from .. import profiles
from ..appdata import get_config_dir
from ..credentials import (
    CredentialStoreError,
    has_stored_secret,
    load_public_configuration,
    save_configuration,
)
from ..profiles import (
    Profile,
    ProfileStoreError,
    active_profile,
    create_profile,
    list_profiles,
    select_profile,
)
from . import platform_integration
from .platform_integration import apply_title_bar as _apply_native_title_bar
from .platform_integration import apply_titlebar_icon as _apply_windows_titlebar_icon
from .platform_integration import disable_maximizing as _disable_windows_maximizing
from .single_instance import SingleInstance
from .theme import (
    ACCENT_PRESETS,
    SERVICE_ANIMATIONS,
    ThemeMode,
    load_appearance_preferences,
    load_startup_preferences,
    load_visited_services,
    load_zoom_preference,
    record_service_visit,
    save_appearance_preferences,
    save_settings_preferences,
    save_zoom_preference,
)

_TENANT_ALIAS = re.compile(r"^(common|organizations|consumers|[A-Za-z0-9.-]+\.[A-Za-z]{2,})$")

_APP_ID = "doydl-technologies.azauthlib"
_APP_TITLE = "azauthlib"
_TITLEBAR_ICON_NAME = "azauthlib-titlebar.ico"
_TASKBAR_ICON_NAME = "azauthlib-taskbar.ico"

_HEADER_LOGO = "logo/svg/azauthlib-wordmark-qt.svg"

_STARTUP_LOGO = "logo/svg/azauthlib-wordmark-qt.svg"

_AUTH_METHODS = frozenset(
    {"interactive", "device_code", "client_credentials", "client_certificate"}
)
_PROVIDERS = {
    "graph": "Microsoft Graph",
    "keyvault": "Azure Key Vault",
    "dataverse": "Dataverse / Dynamics 365",
    "storage": "Azure Storage",
    "sql": "Azure SQL",
    "exchange": "Exchange Online",
}

# Qt scales the full scene, popups, text and input coordinates together, on top
# of the monitor's normal DPI scaling. An explicit QT_SCALE_FACTOR wins.
_UI_SCALE = 0.85

# Lock Connections zoom without overwriting its saved preference.
CONNECTIONS_ZOOM_LOCKED = True


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except (ValueError, AttributeError):
        return False
    return True


def validate_client_id(client_id: str) -> bool:
    return _is_uuid(client_id)


def validate_tenant_id(tenant_id: str) -> bool:
    return _is_uuid(tenant_id) or bool(_TENANT_ALIAS.fullmatch(tenant_id))


def validate_client_secret(client_secret: str) -> bool:
    return (
        isinstance(client_secret, str)
        and bool(client_secret.strip())
        and not any(ord(char) < 0x20 or ord(char) == 0x7F for char in client_secret)
    )


class PackageResources:
    """Keep package resources materialized for the lifetime of the Qt application."""

    def __init__(self) -> None:
        self._stack = ExitStack()
        self._paths: dict[tuple[str, ...], Path] = {}

    def path(self, *parts: str) -> Path:
        key = tuple(parts)
        cached = self._paths.get(key)
        if cached is not None:
            return cached
        resource = files("azauthlib").joinpath(*parts)
        path = Path(self._stack.enter_context(as_file(resource)))
        self._paths[key] = path
        return path

    def close(self) -> None:
        self._stack.close()


class ConfigurationController(QObject):
    """Bridge QML presentation state to azauthlib validation and secure persistence."""

    themeChanged = Signal()
    appearanceChanged = Signal()
    startupPreferencesChanged = Signal()
    preferencesErrorChanged = Signal()
    warmStartStatusChanged = Signal()
    _warmCachePrepared = Signal(int, bool)
    zoomChanged = Signal()
    providerChanged = Signal()
    legalDocumentsChanged = Signal()
    connectionPreparationChanged = Signal()
    serviceWarmupChanged = Signal()
    _connectionProgress = Signal(int, int, str)
    _connectionsPrepared = Signal(int, object, str)
    authMethodChanged = Signal()
    profileListChanged = Signal()
    currentProfileChanged = Signal()
    profileDataChanged = Signal()
    tenantErrorChanged = Signal()
    clientErrorChanged = Signal()
    secretErrorChanged = Signal()
    dialogRequested = Signal(str, str, str, bool)
    focusRequested = Signal(str)
    quitRequested = Signal()
    shortcutBusyChanged = Signal()
    _shortcutFinished = Signal(str, bool)

    def __init__(
        self, resources: PackageResources, *, startup_state=None, defer_connections=True
    ) -> None:
        super().__init__()
        self._resources = resources
        self._startup_preferences = load_startup_preferences(
            directory=profiles.get_config_dir(create=False)
        )
        self._preferences_error = ""
        self._warm_cache_job = 0
        self._warm_cache_cancel = Event()
        self._warm_start_status = "idle"
        self._warmCachePrepared.connect(self._finish_warm_cache_preparation)
        app = QGuiApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.cancelWarmCachePreparation)
        self._appearance_preferences = (
            startup_state["appearancePreferences"]
            if startup_state and "appearancePreferences" in startup_state
            else load_appearance_preferences(directory=profiles.get_config_dir(create=False))
        )
        self._connections_deferred = defer_connections and not (
            startup_state and "profiles" in startup_state
        )
        self._connections_ready = not self._connections_deferred
        self._connection_background = False
        self._background_connections_ready = False
        self._background_services_attempted = set()
        self._visited_services = load_visited_services(
            directory=profiles.get_config_dir(create=False)
        )
        self._connections_loading = False
        self._connections_error = ""
        self._connection_progress = 100 if self._connections_ready else 0
        self._connection_message = ""
        self._connection_job = 0
        self._connection_cancel = Event()
        self._qml_engine = None
        self._connectionProgress.connect(self._report_connection_progress)
        self._connectionsPrepared.connect(self._finish_connection_preparation)
        self._shortcut_busy = False
        self._shortcutFinished.connect(self._finish_shortcut)
        # Session navigation state, separate from saved credentials/profiles.
        self._selected_provider = "graph"
        if startup_state is not None and "legalDocuments" in startup_state:
            self._legal_documents = dict(startup_state["legalDocuments"])
            self._legal_document_urls = dict(startup_state.get("legalDocumentUrls", {}))
        else:
            from .legal_terms import load_legal_documents

            legal = load_legal_documents(resources)
            self._legal_documents = legal["documents"]
            self._legal_document_urls = legal["urls"]
        # Cache this while the splash is visible, not on the first About click.
        self._about_markdown = (
            startup_state["aboutMarkdown"]
            if startup_state and "aboutMarkdown" in startup_state
            else resources.path("assets", "docs", "legal", "INDEPENDENCE_AND_NOTICES.md").read_text(
                encoding="utf-8"
            )
        )
        self._theme: ThemeMode = "dark"
        self._zoom_percent = (
            startup_state["zoomPercent"]
            if startup_state and "zoomPercent" in startup_state
            else load_zoom_preference(directory=profiles.get_config_dir(create=False))
        )
        self._profiles = (
            []
            if self._connections_deferred
            else (
                startup_state["profiles"]
                if startup_state and "profiles" in startup_state
                else list(list_profiles())
            )
        )
        self._current_profile = (
            startup_state["active"]
            if startup_state and "active" in startup_state
            else active_profile()
            if self._profiles
            else None
        )
        self._auth_method = "interactive"
        self._saved_auth_method = "interactive"
        self._profile_tenant_id = ""
        self._profile_client_id = ""
        self._has_stored_secret = False
        self._errors = dict.fromkeys(("tenant", "client", "secret"), "")
        self._close_after_dialog = False
        if startup_state and "values" in startup_state:
            self._apply_profile_data(startup_state["values"], startup_state["hasSecret"])
        elif not self._connections_deferred:
            self._refresh_profile_data()
        from .connections import ConnectionManagerController

        self._connection_manager = ConnectionManagerController(
            self,
            startup_state=startup_state if startup_state and "profiles" in startup_state else None,
            deferred=self._connections_deferred,
        )
        self._connection_manager.storeChanged.connect(self._reload_profiles)
        self._connection_manager.activationRequested.connect(self.selectProfile)

    @Property(QObject, constant=True)
    def connectionManager(self) -> QObject:
        return self._connection_manager

    @Property("QVariantMap", notify=appearanceChanged)
    def appearancePreferences(self):
        return dict(self._appearance_preferences)

    @Property("QVariantMap", notify=startupPreferencesChanged)
    def startupPreferences(self):
        return dict(self._startup_preferences)

    @Property(str, notify=preferencesErrorChanged)
    def preferencesError(self):
        return self._preferences_error

    @Property(bool, constant=True)
    def loginStartupSupported(self):
        from .login_startup import supported

        return supported()

    @Property(str, notify=warmStartStatusChanged)
    def warmStartStatus(self):
        return self._warm_start_status

    def _prepare_warm_cache(self):
        enabled = self._startup_preferences["warm_start"]
        if enabled and self._warm_start_status == "preparing":
            return
        self.cancelWarmCachePreparation()
        self._warm_cache_job += 1
        job = self._warm_cache_job
        self._warm_cache_cancel = Event()
        cancel = self._warm_cache_cancel
        provider = self._qml_engine.imageProvider("providerlogos") if self._qml_engine else None
        snapshots = provider.configure_warm_start(enabled) if provider is not None else []
        self._warm_start_status = "preparing" if enabled else "idle"
        self.warmStartStatusChanged.emit()
        if not enabled:
            return

        def prepare():
            from .startup_cache import prepare_warm_cache

            # Own the resource lifetime on the worker; closing the UI's resource
            # stack must not invalidate paths while a cache write is finishing.
            resources = PackageResources()
            try:
                ready = prepare_warm_cache(resources, snapshots, cancel.is_set)
            except Exception:
                ready = False  # Optional preparation must not undo a successful Settings save.
            finally:
                resources.close()
            if not cancel.is_set():
                with suppress(RuntimeError):
                    self._warmCachePrepared.emit(job, ready)

        try:
            self._warm_cache_thread = Thread(
                target=prepare, daemon=True, name="azauthlib-warm-cache"
            )
            self._warm_cache_thread.start()
        except (OSError, RuntimeError):
            self._warm_start_status = "unavailable"
            self.warmStartStatusChanged.emit()

    @Slot(int, bool)
    def _finish_warm_cache_preparation(self, job, ready):
        if job != self._warm_cache_job or self._warm_cache_cancel.is_set():
            return
        self._warm_start_status = "ready" if ready else "unavailable"
        self.warmStartStatusChanged.emit()

    @Slot()
    def cancelWarmCachePreparation(self):
        self._warm_cache_cancel.set()

    @Slot(str, bool, str, bool, bool, bool, result=bool)
    def savePreferences(
        self, accent, show_info, service_animation, warm_start, adaptive_splash, launch_at_login
    ):
        """One Settings transaction, including reversible user login registration."""
        from .login_startup import apply_login_startup
        from .shortcuts import ShortcutError

        self._preferences_error = ""
        self.preferencesErrorChanged.emit()
        startup = {
            "warm_start": warm_start,
            "adaptive_splash": adaptive_splash,
            "launch_at_login": launch_at_login,
        }
        if startup == self._startup_preferences:
            return self.saveAppearancePreferences(accent, show_info, service_animation)
        if (
            accent not in ACCENT_PRESETS
            or type(show_info) is not bool
            or service_animation not in SERVICE_ANIMATIONS
            or any(type(value) is not bool for value in startup.values())
            or self._connection_manager.editing
            or self._connection_manager.testing
            or (self._connections_loading and not self._connection_background)
        ):
            return False
        rollback = None
        try:
            if launch_at_login != self._startup_preferences["launch_at_login"]:
                rollback = apply_login_startup(launch_at_login)
            if not save_settings_preferences(
                accent,
                show_info,
                service_animation,
                startup,
                directory=profiles.get_config_dir(create=False),
            ):
                raise OSError("Preferences could not be saved")
        except (OSError, RuntimeError, ValueError, ShortcutError):
            self._preferences_error = (
                "Preferences could not be saved. Check that the app is still installed "
                "in this location and that your account can change login-startup settings."
            )
            if rollback is not None:
                try:
                    rollback()
                except (OSError, RuntimeError):
                    self._preferences_error += (
                        " The login-startup change could not be undone. "
                        "Check your operating system's startup-app settings."
                    )
            self.preferencesErrorChanged.emit()
            return False
        if startup["warm_start"] != self._startup_preferences["warm_start"]:
            self._background_services_attempted.clear()
        self._startup_preferences = startup
        if not startup["warm_start"]:
            self.discardBackgroundConnections()
        self._appearance_preferences = load_appearance_preferences(
            directory=profiles.get_config_dir(create=False)
        )
        self.startupPreferencesChanged.emit()
        self.serviceWarmupChanged.emit()
        self.appearanceChanged.emit()
        self._prepare_warm_cache()
        return True

    @Slot(str, bool, result=bool)
    @Slot(str, bool, str, result=bool)
    def saveAppearancePreferences(
        self, accent: str, show_info: bool, service_animation=None
    ) -> bool:
        if (
            self._connection_manager.editing
            or self._connection_manager.testing
            or (self._connections_loading and not self._connection_background)
        ):
            return False
        if not save_appearance_preferences(
            accent, show_info, service_animation, directory=profiles.get_config_dir(create=False)
        ):
            return False
        self._appearance_preferences = load_appearance_preferences(
            directory=profiles.get_config_dir(create=False)
        )
        self.appearanceChanged.emit()
        if self._startup_preferences["warm_start"]:
            self._prepare_warm_cache()
        return True

    @Property(bool, constant=True)
    def connectionsDeferred(self):
        return self._connections_deferred

    @Property(bool, notify=connectionPreparationChanged)
    def connectionsReady(self):
        return self._connections_ready

    @Property(bool, notify=connectionPreparationChanged)
    def connectionsLoading(self):
        return self._connections_loading

    @Property(str, notify=connectionPreparationChanged)
    def connectionsError(self):
        return self._connections_error

    @Property(int, notify=connectionPreparationChanged)
    def connectionLoadProgress(self):
        return self._connection_progress

    @Property(str, notify=connectionPreparationChanged)
    def connectionLoadMessage(self):
        return self._connection_message

    @Property(bool, notify=connectionPreparationChanged)
    def connectionsBackgroundPreparing(self):
        return self._connection_background

    @Property(bool, notify=serviceWarmupChanged)
    def canWarmVisitedService(self):
        return (
            self._startup_preferences["warm_start"]
            and self._selected_provider == "graph"
            and self._selected_provider in self._visited_services
            and self._selected_provider not in self._background_services_attempted
            and not self._connections_ready
            and not self._connections_loading
        )

    @Slot()
    def recordServiceVisit(self):
        if self._selected_provider != "graph":
            return
        if record_service_visit("graph", directory=profiles.get_config_dir(create=False)):
            self._visited_services = load_visited_services(
                directory=profiles.get_config_dir(create=False)
            )
            self.serviceWarmupChanged.emit()

    @Slot()
    def prepareVisitedService(self):
        if not self.canWarmVisitedService:
            return
        if self._connection_manager.editing or self._connection_manager.testing:
            return
        self._background_services_attempted.add(self._selected_provider)
        self._start_connection_preparation(background=True)

    @Slot()
    def discardBackgroundConnections(self):
        if self._connection_background:
            self.cancelConnectionPreparation()
        if self._background_connections_ready:
            self._background_connections_ready = False
            self._connections_ready = False
            self._connection_manager.discard_prepared_state()
            self.connectionPreparationChanged.emit()
            self.serviceWarmupChanged.emit()

    @Slot()
    def prepareConnections(self):
        """Service-selection phase: no profile, keyring or avatar work in the splash."""
        refresh = self._background_connections_ready
        if self._connection_background:
            self.cancelConnectionPreparation()
        if (self._connections_ready and not refresh) or self._connections_loading:
            return
        self._start_connection_preparation(background=False)

    def _start_connection_preparation(self, *, background):
        if not background and self._background_connections_ready:
            self._connection_manager.discard_prepared_state()
        self._connection_job += 1
        job = self._connection_job
        self._connection_cancel = cancel = Event()
        self._connections_loading = True
        self._connections_ready = False
        self._connection_background = background
        self._connections_error = ""
        self._connection_progress = 0
        self._connection_message = "Initializing runtime context…"
        self.connectionPreparationChanged.emit()
        self.serviceWarmupChanged.emit()

        def report(value, message):
            if cancel.is_set():
                raise InterruptedError()
            self._connectionProgress.emit(job, value, message)

        def prepare():
            try:
                state = (
                    prepare_connections_state(report, background=True)
                    if background
                    else prepare_connections_state(report)
                )
                if avatar_provider is not None:
                    avatar_provider.preload(
                        lambda done, total: report(
                            75 + int(12 * done / total), "Priming visual caches…"
                        ),
                        cancel.is_set,
                    )
                if not cancel.is_set():
                    self._connectionsPrepared.emit(job, state, "")
            except InterruptedError:
                pass
            except Exception:
                with suppress(RuntimeError):
                    self._connectionsPrepared.emit(
                        job,
                        None,
                        "Connections could not be loaded. "
                        "Check saved files and secure storage, then retry.",
                    )

        try:
            from .svg_images import ensure_image_providers

            avatar_provider = (
                ensure_image_providers(self._qml_engine, self._resources)
                if self._qml_engine is not None
                else None
            )
            Thread(target=prepare, daemon=True, name="azauthlib-service-selection").start()
        except Exception:
            self._finish_connection_preparation(
                job, None, "Unable to start loading connections. Please retry."
            )

    @Slot(int, int, str)
    def _report_connection_progress(self, job, value, message):
        if job != self._connection_job or self._connection_cancel.is_set():
            return
        self._connection_progress = max(self._connection_progress, min(90, value))
        self._connection_message = message
        self.connectionPreparationChanged.emit()

    @Slot(int, object, str)
    def _finish_connection_preparation(self, job, state, error):
        if job != self._connection_job or self._connection_cancel.is_set():
            return
        self._connections_loading = False
        background = self._connection_background
        self._connection_background = False
        if state is None:
            self._connections_error = error
            self._connection_message = "Connections could not be loaded."
        else:
            self._profiles = state["profiles"]
            self._current_profile = state["active"]
            self._apply_profile_data(state["values"], state["hasSecret"])
            self.profileListChanged.emit()
            self.currentProfileChanged.emit()
            self._connection_manager.install_prepared_state(state)
            self._connections_ready = True
            self._background_connections_ready = background
            self._connection_progress = 90
            self._connection_message = "Composing the render graph…"
        self.connectionPreparationChanged.emit()
        self.serviceWarmupChanged.emit()

    @Slot()
    def cancelConnectionPreparation(self):
        if not self._connections_loading:
            return
        self._connection_cancel.set()
        self._connection_job += 1
        self._connections_loading = False
        self._connection_background = False
        self._connection_progress = 0
        self._connection_message = ""
        self.connectionPreparationChanged.emit()
        self.serviceWarmupChanged.emit()

    @Property(bool, constant=True)
    def shortcutSupported(self) -> bool:
        return sys.platform in {"win32", "darwin"} or sys.platform.startswith("linux")

    @Property(bool, notify=shortcutBusyChanged)
    def shortcutBusy(self) -> bool:
        return self._shortcut_busy

    @Slot()
    def createAppShortcut(self) -> None:
        """Create a per-user launcher only when requested from the interface."""
        if self._shortcut_busy or not self.shortcutSupported:
            return
        from .shortcuts import ShortcutError, create_app_shortcut

        desktop = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
        try:
            icon = self._resources.path("assets", _TASKBAR_ICON_NAME)
        except OSError:
            self._show_dialog(
                "Shortcut unavailable", "The application icon is unavailable.", "error"
            )
            return
        self._shortcut_busy = True
        self.shortcutBusyChanged.emit()

        def create():
            try:
                message = create_app_shortcut(desktop_dir=desktop, icon_path=icon).message
                success = True
            except ShortcutError as exc:
                message, success = str(exc), False
            except Exception:
                message, success = (
                    "The shortcut could not be created. Check folder permissions and try again.",
                    False,
                )
            with suppress(RuntimeError):
                self._shortcutFinished.emit(message, success)

        Thread(target=create, name="azauthlib-shortcut", daemon=True).start()

    @Slot(str, bool)
    def _finish_shortcut(self, message: str, success: bool) -> None:
        self._shortcut_busy = False
        self.shortcutBusyChanged.emit()
        self._show_dialog(
            "Shortcut created" if success else "Shortcut unavailable",
            message,
            "success" if success else "error",
        )

    @Property(str, notify=providerChanged)
    def selectedProviderId(self) -> str:
        return self._selected_provider

    @Property(str, notify=providerChanged)
    def selectedProviderName(self) -> str:
        return _PROVIDERS.get(self._selected_provider, "")

    @Slot(str, result=bool)
    def setSelectedProvider(self, provider: str) -> bool:
        """Select one known provider, or clear selection without touching storage."""
        if provider and provider not in _PROVIDERS:
            return False
        if provider != self._selected_provider:
            if self._connection_background:
                self.cancelConnectionPreparation()
            self._selected_provider = provider
            self.providerChanged.emit()
            self.serviceWarmupChanged.emit()
        return True

    @Property(int, notify=zoomChanged)
    def zoomPercent(self) -> int:
        return 100 if CONNECTIONS_ZOOM_LOCKED else self._zoom_percent

    @Property(bool, constant=True)
    def zoomLocked(self) -> bool:
        return CONNECTIONS_ZOOM_LOCKED

    @Slot(int)
    def setZoomPercent(self, value: int) -> None:
        if CONNECTIONS_ZOOM_LOCKED or type(value) is not int:
            return
        value = max(70, min(125, value))
        if value == self._zoom_percent:
            return
        self._zoom_percent = value
        self.zoomChanged.emit()
        save_zoom_preference(value, directory=profiles.get_config_dir(create=False))

    @Slot()
    def _reload_profiles(self) -> None:
        self._profiles = list(list_profiles())
        self.profileListChanged.emit()
        active = active_profile() if self._profiles else None
        if active is None:
            self._activate_profile(None)
            return
        values = load_public_configuration(profile=active.id)
        saved = (
            values.get("tenant_id") or "",
            values.get("client_id") or "",
            values.get("auth_method") or "interactive",
        )
        if active.id != self.currentProfileId or saved != (
            self._profile_tenant_id,
            self._profile_client_id,
            self._saved_auth_method,
        ):
            self._activate_profile(active)
        elif active != self._current_profile:
            self._current_profile = active
            self.currentProfileChanged.emit()

    @Property(str, notify=themeChanged)
    def theme(self) -> str:
        return self._theme

    @Property(str, constant=True)
    def aboutMarkdown(self) -> str:
        """Read the bundled notice without network access or working-directory assumptions."""
        return self._about_markdown

    @Property("QVariantMap", notify=legalDocumentsChanged)
    def legalDocuments(self):
        return dict(self._legal_documents)

    @Property("QVariantMap", constant=True)
    def legalDocumentUrls(self):
        return dict(self._legal_document_urls)

    @Slot(str, result=bool)
    def openLegalDocument(self, topic):
        """Open only a package-resolved policy file, never a caller-supplied URL."""
        url = self._legal_document_urls.get(topic, "")
        return bool(url) and QDesktopServices.openUrl(QUrl(url))

    @Slot(str, QObject)
    def prepareLegalDocument(self, topic, quick_document):
        """Prepare native HTML before reveal; rendering failures stay offline."""
        try:
            if not isinstance(quick_document, QQuickTextDocument):
                raise ValueError("Missing legal document")
            document = quick_document.textDocument()
            if document is None or not document.toPlainText().strip():
                raise ValueError("Empty legal document")
            self.formatAboutDocument(quick_document)
        except Exception:
            QTimer.singleShot(0, lambda: self._discard_legal_document(topic))

    def _discard_legal_document(self, topic):
        from .legal_terms import unavailable_document

        replacement = unavailable_document(topic)
        if self._legal_documents.get(topic) != replacement:
            self._legal_documents[topic] = replacement
            self.legalDocumentsChanged.emit()

    @Slot(QObject)
    def formatAboutDocument(self, quick_document: QObject) -> None:
        """Style native drawer blocks without changing their words."""
        if not isinstance(quick_document, QQuickTextDocument):
            return
        document = quick_document.textDocument()
        if document is None:
            return
        # Hundreds of live edits otherwise relayout the entire notice for each
        # block. Prepare one transaction, then perform a single final layout.
        layout_enabled = document.isLayoutEnabled()
        document.setLayoutEnabled(False)
        document.setUndoRedoEnabled(False)  # This notice is permanently read-only.
        transaction = QTextCursor(document)
        transaction.beginEditBlock()
        try:
            block = document.begin()
            policy_metadata = block.text() in ("Terms of Use", "Privacy Policy")
            while block.isValid():
                cursor = QTextCursor(block)
                block_format = block.blockFormat()
                heading = block_format.headingLevel()
                if heading and block.blockNumber():
                    policy_metadata = False
                metadata = not heading and block.text().startswith(
                    (
                        "Developer:",
                        "Developer and Maintainer:",
                        "Repository:",
                        "App Version:",
                        "Project:",
                    )
                )
                metadata = metadata or (
                    policy_metadata
                    and not heading
                    and block.text().startswith(
                        (
                            "Effective date:",
                            "Publisher:",
                            "Companion document:",
                        )
                    )
                )
                block_format.setTopMargin(14 if heading and block.blockNumber() else 0)
                block_format.setBottomMargin(0 if metadata else 9 if not block.textList() else 4)
                block_format.setLineHeight(100, QTextBlockFormat.ProportionalHeight.value)
                cursor.setBlockFormat(block_format)
                if heading:
                    font = QFont("Manrope")
                    font.setPixelSize(16 if heading == 1 else 13)
                    font.setWeight(QFont.Bold)
                    char_format = QTextCharFormat()
                    char_format.setFont(font)
                    # Replace Markdown's relative font sizing; do not enlarge
                    # the explicit pixel size again through a format merge.
                    cursor.setPosition(
                        block.position() + block.length() - 1, QTextCursor.KeepAnchor
                    )
                    cursor.setBlockCharFormat(char_format)
                    cursor.setCharFormat(char_format)
                block = block.next()
        finally:
            transaction.endEditBlock()
            document.setLayoutEnabled(layout_enabled)

    @Property(str, notify=themeChanged)
    def logoUrl(self) -> str:
        return self._resource_url("assets", _HEADER_LOGO)

    @Property(str, notify=themeChanged)
    def startupLogoUrl(self) -> str:
        return self._resource_url("assets", _STARTUP_LOGO)

    @Property(str, notify=authMethodChanged)
    def authMethod(self) -> str:
        return self._auth_method

    @authMethod.setter
    def authMethod(self, value: str) -> None:
        if value not in _AUTH_METHODS or value == self._auth_method:
            return
        self._auth_method = value
        if value != "client_credentials":
            self._set_error("secret", "")
        self.authMethodChanged.emit()

    @Property("QStringList", notify=profileListChanged)
    def profileNames(self) -> list[str]:
        return [profile.name for profile in self._profiles]

    @Property(str, notify=currentProfileChanged)
    def currentProfileName(self) -> str:
        return self._current_profile.name if self._current_profile else ""

    @Property(str, notify=currentProfileChanged)
    def currentProfileId(self) -> str:
        """Stable identity for the active marker in the Connections list."""
        return self._current_profile.id if self._current_profile else ""

    @Property(str, notify=profileDataChanged)
    def profileTenantId(self) -> str:
        return self._profile_tenant_id

    @Property(str, notify=profileDataChanged)
    def profileClientId(self) -> str:
        return self._profile_client_id

    @Property(bool, notify=profileDataChanged)
    def hasStoredSecret(self) -> bool:
        return self._has_stored_secret

    @Property(str, notify=authMethodChanged)
    def secretHint(self) -> str:
        if self._auth_method == "client_credentials":
            return "Required for the selected client credentials flow"
        return "Required only for the client credentials flow"

    @Property(str, notify=tenantErrorChanged)
    def tenantError(self) -> str:
        return self._errors["tenant"]

    @Property(str, notify=clientErrorChanged)
    def clientError(self) -> str:
        return self._errors["client"]

    @Property(str, notify=secretErrorChanged)
    def secretError(self) -> str:
        return self._errors["secret"]

    @Slot()
    def toggleTheme(self) -> None:
        # Dark-only presentation retains this slot for API compatibility.
        pass

    @Slot(str, result=str)
    def assetUrl(self, filename: str) -> str:
        return self._resource_url("assets", filename)

    @Slot(str)
    def clearFieldError(self, field: str) -> None:
        self._set_error(field, "")

    @Slot(str, result=bool)
    def createProfile(self, name: str) -> bool:
        try:
            profile = create_profile(name)
        except (TypeError, ValueError, ProfileStoreError, OSError) as exc:
            self._show_dialog("Unable to create profile", str(exc), "error")
            return False
        self._profiles = list(list_profiles())
        self.profileListChanged.emit()
        self._activate_profile(profile)
        return True

    @Slot(str)
    def selectProfile(self, name: str) -> None:
        try:
            profile = select_profile(name)
        except (TypeError, ValueError, ProfileStoreError, OSError) as exc:
            self._show_dialog("Unable to select profile", str(exc), "error")
            return
        self._activate_profile(profile)

    @Slot(str, str, str, str, result=bool)
    def canSaveConfiguration(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        auth_method: str,
    ) -> bool:
        """Return whether the current form satisfies the save requirements."""

        if self._current_profile is None or auth_method not in _AUTH_METHODS:
            return False
        if not validate_tenant_id(tenant_id.strip()):
            return False
        if not validate_client_id(client_id.strip()):
            return False
        if auth_method == "client_certificate":
            return False  # Certificate edits use the validated Connections Manager editor.
        if auth_method != "client_credentials":
            return True
        if validate_client_secret(client_secret):
            return True
        return client_id.strip() == self._profile_client_id and self._has_stored_secret

    @Slot(str, str, str)
    def saveConfiguration(self, tenant_id: str, client_id: str, client_secret: str) -> None:
        """Validate input and delegate persistence to the credential store."""

        tenant_id = tenant_id.strip()
        client_id = client_id.strip()
        self._clear_errors()

        if self._auth_method == "client_certificate":
            self._show_dialog(
                "Certificate connection",
                "Use the Connections Manager to edit and validate certificate credentials.",
                "information",
            )
            return

        if self._current_profile is None:
            self._show_dialog(
                "No connection selected", "Add a connection before saving settings.", "information"
            )
            return

        if not validate_tenant_id(tenant_id):
            message = "Enter a tenant UUID, verified domain, common, organizations, or consumers."
            self._validation_error("tenant", "Invalid tenant", message)
            return

        if not validate_client_id(client_id):
            message = "Client ID must be a UUID."
            self._validation_error("client", "Invalid client ID", message)
            return

        stored_secret_is_usable = client_id == self._profile_client_id and self._has_stored_secret
        if (
            self._auth_method == "client_credentials"
            and not validate_client_secret(client_secret)
            and not stored_secret_is_usable
        ):
            if client_secret:
                message = "Client secret contains unsupported control characters."
            else:
                message = "Client credentials authentication requires a secret."
            self._validation_error("secret", "Invalid client secret", message)
            return

        try:
            save_configuration(
                client_id=client_id,
                tenant_id=tenant_id,
                client_secret=client_secret or None,
                profile=self._current_profile.id,
                auth_method=self._auth_method,
            )
        except CredentialStoreError as exc:
            self._show_dialog(
                "Secure storage unavailable",
                str(exc),
                "error",
            )
            return

        self._profile_tenant_id = tenant_id
        self._profile_client_id = client_id
        self._saved_auth_method = self._auth_method
        if client_secret:
            self._has_stored_secret = True
        self.profileDataChanged.emit()
        self._show_dialog(
            "Configuration saved",
            f"{self._current_profile.name} was saved securely.",
            "success",
        )

    @Slot()
    def acknowledgeDialog(self) -> None:
        if self._close_after_dialog:
            self._close_after_dialog = False
            self.quitRequested.emit()

    @Slot()
    def requestClose(self) -> None:
        self.quitRequested.emit()

    def _resource_url(self, *parts: str) -> str:
        try:
            path = self._resources.path(*parts)
        except (FileNotFoundError, ModuleNotFoundError, OSError):
            return ""
        return QUrl.fromLocalFile(str(path)).toString()

    def _validation_error(self, field: str, title: str, message: str) -> None:
        self._set_error(field, message)
        self.focusRequested.emit(field)
        self._show_dialog(title, message, "error")

    def _show_dialog(
        self,
        title: str,
        message: str,
        variant: str,
        *,
        close_after: bool = False,
    ) -> None:
        self._close_after_dialog = close_after
        self.dialogRequested.emit(title, message, variant, close_after)

    def _clear_errors(self) -> None:
        for field in ("tenant", "client", "secret"):
            self._set_error(field, "")

    def _activate_profile(self, profile: Profile | None) -> None:
        changed = profile != self._current_profile
        self._current_profile = profile
        if changed:
            self.currentProfileChanged.emit()
        self._clear_errors()
        self._refresh_profile_data()

    def _refresh_profile_data(self) -> None:
        if self._current_profile is None:
            self._apply_profile_data({}, False)
            return
        values = load_public_configuration(profile=self._current_profile.id)
        try:
            stored = has_stored_secret(values.get("client_id"))
        except CredentialStoreError:
            stored = False
        self._apply_profile_data(values, stored)

    def _apply_profile_data(self, values, stored) -> None:
        self._profile_tenant_id = values.get("tenant_id") or ""
        self._profile_client_id = values.get("client_id") or ""
        method = values.get("auth_method") or "interactive"
        self._saved_auth_method = method
        method_changed = method != self._auth_method
        self._auth_method = method
        self._has_stored_secret = stored
        if method_changed:
            self.authMethodChanged.emit()
        self.profileDataChanged.emit()

    def _set_error(self, field: str, message: str) -> None:
        signals = {
            "tenant": self.tenantErrorChanged,
            "client": self.clientErrorChanged,
            "secret": self.secretErrorChanged,
        }
        signal = signals.get(field)
        if signal is None:
            return
        if self._errors[field] == message:
            return
        self._errors[field] = message
        signal.emit()


def _report_qml_warnings(warnings) -> None:
    for warning in warnings:
        print(f"QML: {warning.toString()}", file=sys.stderr)


def _set_windows_app_id() -> None:
    platform_integration.set_app_id(_APP_ID)


def configure_application_identity(app, resources: PackageResources) -> None:
    """Set the same app identity/icon for production and diagnostic launchers."""
    _set_windows_app_id()
    app.setApplicationName("azauthlib")
    app.setApplicationDisplayName(_APP_TITLE)
    app.setOrganizationName("DOYDL Technologies")
    app.setOrganizationDomain("doydl.studio")
    if sys.platform.startswith("linux"):
        app.setDesktopFileName("doydl-azauthlib")
    icon = QIcon(str(resources.path("assets", _TASKBAR_ICON_NAME)))
    if icon.isNull():
        raise RuntimeError("Unable to load the bundled azauthlib taskbar icon")
    app.setWindowIcon(icon)


def center_window_on_screen(window, screen=None):
    """Center the final native frame, including caption, in one monitor's work area."""
    screen = screen or window.screen() or QGuiApplication.primaryScreen()
    if screen is None:
        return
    window.setScreen(screen)
    window.winId()  # Native frame margins must exist before computing the position.
    available = screen.availableGeometry()
    frame = window.frameGeometry()
    window.setFramePosition(
        QPoint(
            available.x() + (available.width() - frame.width()) // 2,
            available.y() + (available.height() - frame.height()) // 2,
        )
    )


def configure_window_taskbar_identity(window, resources: PackageResources) -> None:
    """Give startup, preview, and main windows the same identity before show()."""
    window.setIcon(QGuiApplication.instance().windowIcon())
    try:
        platform_integration.apply_window_identity(
            window,
            app_id=_APP_ID,
            title=_APP_TITLE,
            icon_path=resources.path("assets", _TASKBAR_ICON_NAME),
        )
    except OSError as error:
        # A shell customization failure must not prevent opening the app.
        print(f"Native window identity: {error}", file=sys.stderr)


def create_startup_splash(engine: QQmlApplicationEngine, resources: PackageResources):
    """Show only the minimal splash; never read profiles or secure storage here."""
    app = QGuiApplication.instance()
    configure_application_identity(app, resources)
    from .svg_images import ensure_accent_theme

    ensure_accent_theme(engine, resources)
    qml_root = resources.path("gui", "qml", "Main.qml").parent
    engine.addImportPath(str(qml_root))
    component = QQmlComponent(
        engine, QUrl.fromLocalFile(str(qml_root / "components" / "StartupSplash.qml"))
    )
    splash = component.createWithInitialProperties(
        {
            "visible": False,
            "logoSource": QUrl.fromLocalFile(str(resources.path("assets", _STARTUP_LOGO))),
        }
    )
    if not isinstance(splash, QQuickWindow):
        errors = "\n".join(error.toString() for error in component.errors())
        raise RuntimeError("Unable to load the azauthlib splash screen: " + errors)
    # QObject ownership only: a native window parent would hide the splash.
    QObject.setParent(splash, engine)
    configure_window_taskbar_identity(splash, resources)
    screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
    center_window_on_screen(splash, screen)
    engine.setIncubationController(splash.incubationController())
    splash.show()
    return splash


def prepare_startup_state(report, resources):
    """Splash scope: shared display/legal content only, never connection data."""
    from .legal_terms import load_legal_documents

    appearance = load_appearance_preferences(directory=profiles.get_config_dir(create=False))
    zoom = load_zoom_preference(directory=profiles.get_config_dir(create=False))
    report(35, "Display preferences loaded")
    startup = load_startup_preferences(directory=profiles.get_config_dir(create=False))
    from .startup_cache import load_shared_content, save_shared_content

    cached = load_shared_content(resources) if startup["warm_start"] else None
    from .legal_terms import POLICY_FILES

    legal = (
        {
            "documents": cached["legalDocuments"],
            "urls": {
                topic: resources.path("assets", "docs", "legal", name).resolve().as_uri()
                for topic, name in POLICY_FILES.items()
            },
        }
        if cached
        else load_legal_documents(resources)
    )
    report(60, "Terms of Use and Privacy Policy prepared")
    about = (
        cached["aboutMarkdown"]
        if cached
        else resources.path("assets", "docs", "legal", "INDEPENDENCE_AND_NOTICES.md").read_text(
            encoding="utf-8"
        )
    )
    if startup["warm_start"] and cached is None:
        save_shared_content(resources, legal["documents"], about)
    report(80, "About azauthlib and shared resources prepared")
    return {
        "appearancePreferences": appearance,
        "zoomPercent": zoom,
        "legalDocuments": legal["documents"],
        "legalDocumentUrls": legal["urls"],
        "aboutMarkdown": about,
    }


def prepare_connections_state(report, *, background=False):
    """Service-selection worker data; Qt objects are installed on the GUI thread."""
    # Percentages are weighted startup milestones, not an elapsed-time estimate.
    from .connection_results import ConnectionResults

    saved = list(list_profiles())
    active = active_profile() if saved else None
    report(35, "Reconciling persisted state…")
    values = (
        load_public_configuration(profile=active.id) if active else {"auth_method": "interactive"}
    )
    report(50, "Aligning execution parameters…")
    # Match normal controller behavior if optional secure storage is unavailable.
    try:
        stored = has_stored_secret(values.get("client_id")) if active and not background else False
    except CredentialStoreError:
        stored = False
    report(65, "Resolving secure references…")
    results = ConnectionResults()
    editor = (
        {
            "id": active.id,
            "name": active.name,
            "avatar": active.avatar,
            "tenant": values.get("tenant_id") or "",
            "client": values.get("client_id") or "",
            "method": values["auth_method"],
            "hasSecret": stored,
            "certificate": values.get("certificate") or {},
            "testResult": results.state(active.id, values) if not background else {},
        }
        if active
        else {}
    )
    report(75, "Reconstituting session state…")
    return {
        "profiles": saved,
        "active": active,
        "values": values,
        "hasSecret": stored,
        "results": results,
        "editor": editor,
    }


class StartupBootstrap(QObject):
    """Prepare shared state with a splash-first or load-time-adaptive presentation."""

    _progress = Signal(int, str)
    _prepared = Signal(object, str)

    def __init__(self, app, engine, resources, splash):
        super().__init__(engine)
        self.app, self.engine, self.resources, self.splash = app, engine, resources, splash
        self.controller = self.window = None
        self._cancelled = Event()
        self._running = False
        self._scheduled = False
        self._adaptive = splash is None
        self._building_ui = False
        self._shared_prepared = Event()
        self._splash_hold_active = False
        self._splash_frame_seen = False
        self._last_progress = (0, "Preparing application…")
        self._splash_timer = QTimer(self)
        self._splash_timer.setSingleShot(True)
        self._splash_timer.setInterval(350)
        self._splash_timer.timeout.connect(self._show_delayed_splash)
        self._splash_hold_timer = QTimer(self)
        self._splash_hold_timer.setSingleShot(True)
        self._splash_hold_timer.setInterval(400)
        self._splash_hold_timer.timeout.connect(self._release_splash_hold)
        self._progress.connect(self._set_progress)
        self._prepared.connect(self._finish)
        if splash is not None:
            self._connect_splash()

    def _connect_splash(self):
        self.splash.retryRequested.connect(self.start)
        self.splash.abortRequested.connect(self.abort)

    @Slot()
    def _show_delayed_splash(self, force=False):
        if self._cancelled.is_set() or (
            self.window is not None and self.window.property("startupRevealed")
        ):
            return
        if not force and (
            self._building_ui or (self._shared_prepared.is_set() and self.window is None)
        ):
            # A due timer can be delivered by processEvents inside the QML
            # loader. Never create a splash during that almost-ready handoff.
            if not self._building_ui:
                self._splash_timer.start()
            return
        if self.splash is None:
            try:
                self.splash = create_startup_splash(self.engine, self.resources)
            except (OSError, RuntimeError):
                # A broken fallback must not leave an invisible process alive.
                print("The azauthlib startup interface could not be loaded.", file=sys.stderr)
                self.shutdown()
                self.app.exit(1)
                return
            self._connect_splash()
            self._splash_hold_active = True
            # Failsafe if a render backend never presents a frame.
            self._splash_hold_timer.start(2000)
            self.splash.frameSwapped.connect(self._first_adaptive_splash_frame)
            self._set_progress(*self._last_progress)
            if self.window is not None:
                self.window.setProperty("startupSplashHold", True)
                self.window.setProperty("startupSplash", self.splash)

    @Slot()
    def _first_adaptive_splash_frame(self):
        if self._splash_frame_seen:
            return
        self._splash_frame_seen = True
        self.splash.frameSwapped.disconnect(self._first_adaptive_splash_frame)
        self._splash_hold_timer.start(400)

    @Slot()
    def _release_splash_hold(self):
        self._splash_hold_active = False
        if self.window is not None:
            self.window.setProperty("startupSplashHold", False)

    def _show_error(self, message):
        self._splash_timer.stop()
        self._show_delayed_splash(force=True)
        if self.splash is not None:
            self.splash.setProperty("statusText", message)
            self.splash.setProperty("failed", True)

    def start_after_first_frame(self):
        if self._adaptive:
            self._splash_timer.start()
            QTimer.singleShot(0, self.start)
            return
        # processEvents alone does not guarantee that Windows has presented it.
        self.splash.frameSwapped.connect(self._first_frame)
        self.splash.update()

    @Slot()
    def _first_frame(self):
        if self._scheduled:
            return
        self._scheduled = True
        self.splash.frameSwapped.disconnect(self._first_frame)
        QTimer.singleShot(0, self.start)

    @Slot(int, str)
    def _set_progress(self, value, message):
        if self._cancelled.is_set():
            return
        self._last_progress = (value, message)
        if self.splash is not None:
            self.splash.setProperty("progress", value)
            self.splash.setProperty("statusText", message)

    @Slot()
    def start(self):
        if self._running or self._cancelled.is_set() or self.window is not None:
            return
        self._running = True
        self._shared_prepared.clear()
        if self.splash is not None:
            self.splash.setProperty("failed", False)
        self._set_progress(0, "Checking application instance…")

        def report(value, message):
            if self._cancelled.is_set():
                raise InterruptedError()
            self._progress.emit(value, message)

        def prepare():
            try:
                report(10, "Application instance checked")
                state = prepare_startup_state(report, self.resources)
                if not self._cancelled.is_set():
                    self._shared_prepared.set()
                    self._prepared.emit(state, "")
            except InterruptedError:
                pass
            except Exception:
                # Exception text may contain credentials or private filesystem details.
                with suppress(RuntimeError):
                    self._prepared.emit(
                        None, "Shared application resources could not be loaded. Please retry."
                    )

        try:
            from .svg_images import ensure_image_providers

            # Qt objects stay on the GUI thread; shared preparation runs on
            # the worker. Adaptive startup need not create a splash at all.
            ensure_image_providers(self.engine, self.resources, include_avatars=False)
            Thread(target=prepare, daemon=True, name="azauthlib-startup").start()
        except RuntimeError:
            self._finish(None, "Unable to start loading. Please retry.")

    @Slot(object, str)
    def _finish(self, state, error):
        self._running = False
        if self._cancelled.is_set():
            return
        if state is None:
            self._show_error(error)
            return
        self._building_ui = True
        self._splash_timer.stop()
        try:
            self.controller = ConfigurationController(self.resources, startup_state=state)
            self.controller.quitRequested.connect(self.app.quit)
            self.app.aboutToQuit.connect(self.controller.connectionManager.cancelTest)
            self.app.aboutToQuit.connect(self.controller.cancelConnectionPreparation)
            self._set_progress(87, "Application controls prepared")
            self.window = load_configuration_qml(
                self.engine,
                self.resources,
                self.controller,
                splash=self.splash,
                show_splash=self.splash is not None,
                skip_startup_minimum=self._adaptive,
                hold_startup_splash=self._splash_hold_active,
            )
            self.window.setProperty("startupSplashHold", self._splash_hold_active)
            # A timer may have created the splash while the loader processed
            # queued events; attach that same window before the readiness gate.
            if self.splash is not None and not self.window.property("startupRevealed"):
                self.window.setProperty("startupSplash", self.splash)
            self.window.startupRevealRequested.connect(self._splash_timer.stop)
            if (
                self._adaptive
                and self.splash is None
                and not self.window.property("startupRevealed")
            ):
                self._splash_timer.start()
            _disable_windows_maximizing(self.window)
            _apply_native_title_bar(self.window, dark=self.controller.theme == "dark")
            _apply_windows_titlebar_icon(
                self.window, self.resources.path("assets", _TITLEBAR_ICON_NAME)
            )
            self.controller.themeChanged.connect(
                lambda: _apply_native_title_bar(self.window, dark=self.controller.theme == "dark")
            )
        except Exception:
            if self.window is not None:
                self.window.setProperty("startupSplash", None)
                self.window.setProperty("closingAllowed", True)
                self.window.close()
                self.window.deleteLater()
                self.window = None
                self.engine.setIncubationController(
                    self.splash.incubationController() if self.splash is not None else None
                )
            if self.controller is not None:
                self.controller.deleteLater()
                self.controller = None
            self._show_error("Unable to prepare the interface. Please retry.")
        finally:
            self._building_ui = False

    @Slot()
    def abort(self):
        self.shutdown()
        if self.splash is not None:
            self.splash.hide()
        self.app.quit()

    def shutdown(self):
        self._cancelled.set()
        self._splash_timer.stop()
        self._splash_hold_timer.stop()
        if self.controller is not None:
            self.controller.cancelConnectionPreparation()
            self.controller.cancelWarmCachePreparation()

    @Slot()
    def activate(self):
        """Relaunches reuse the live UI, without resetting edits or test state."""
        target = self.window if self.window is not None and self.window.isVisible() else self.splash
        modal = QGuiApplication.modalWindow()
        if modal is not None and modal.isVisible():
            target = modal
        if target is None or not target.isVisible():
            return  # The normal first-frame handoff will activate the main UI.
        if target.windowState() == Qt.WindowMinimized:
            target.showNormal()
        target.raise_()
        target.requestActivate()
        platform_integration.activate_window(target)


class _FirstFrameReveal(QObject):
    """Apply the first presented frame's window changes on the GUI thread."""

    def __init__(self, window):
        super().__init__(window)
        self._window = window
        self._seen = False

    @Slot()
    def reveal(self):
        if self._seen:
            return  # More than one frame signal can already be queued.
        self._seen = True
        window = self._window
        window.frameSwapped.disconnect(self.reveal)
        if window.isVisible():
            # Keep the native frame transparent until Qt has painted it;
            # otherwise Windows can briefly show a white unpainted window.
            window.setOpacity(1)
            active_splash = window.property("startupSplash")
            if isinstance(active_splash, QQuickWindow):
                active_splash.hide()
            window.requestActivate()


def load_configuration_qml(
    engine: QQmlApplicationEngine,
    resources: PackageResources,
    controller: ConfigurationController,
    *,
    splash: QQuickWindow | None = None,
    show_splash: bool = True,
    skip_startup_minimum: bool = False,
    hold_startup_splash: bool = False,
) -> QQuickWindow:
    """Load the interface; tests/previews may bypass splash creation entirely."""
    if not show_splash and splash is not None:
        raise ValueError("Cannot skip an explicitly supplied startup splash")
    app = QGuiApplication.instance()
    configure_application_identity(app, resources)
    from .svg_images import ensure_accent_theme, ensure_image_providers

    ensure_accent_theme(engine, resources, controller.appearancePreferences["accent"])
    ensure_image_providers(engine, resources, include_avatars=not controller.connectionsDeferred)
    controller._qml_engine = engine
    qml_root = resources.path("gui", "qml", "Main.qml").parent
    engine.addImportPath(str(qml_root))
    own_splash = show_splash and splash is None
    if own_splash:
        splash = create_startup_splash(engine, resources)
        splash.abortRequested.connect(lambda: QTimer.singleShot(0, QGuiApplication.instance().quit))
    if splash is not None:
        splash.setProperty("progress", 88)
        splash.setProperty("statusText", "Building Main Menu and loading service logos…")
    app.processEvents()
    quit_on_last_window = app.quitOnLastWindowClosed()
    # Keep startup/visibility changes from ending the app before the handoff.
    app.setQuitOnLastWindowClosed(False)
    try:
        previous_roots = set(engine.rootObjects())
        engine.setInitialProperties(
            {
                "appController": controller,
                "startupSplash": splash,
                "startupMinimumElapsed": not show_splash or skip_startup_minimum,
                # A warm Home can become ready during engine.load(), before
                # Python has connected the native-window reveal handler.
                "startupSplashHold": True,
                "adaptiveStartup": skip_startup_minimum,
            }
        )
        engine.load(QUrl.fromLocalFile(str(qml_root / "Main.qml")))
        created_roots = [root for root in engine.rootObjects() if root not in previous_roots]
        if not created_roots:
            raise RuntimeError("Unable to load the azauthlib QML interface")
        window = created_roots[0]
        if not isinstance(window, QQuickWindow):
            raise RuntimeError("The azauthlib main scene did not create a Qt Quick window")
        # Set the native window's large icon explicitly as well as Qt's global
        # fallback. The separate title-bar override only replaces ICON_SMALL.
        window.setIcon(app.windowIcon())

        first_frame_reveal = _FirstFrameReveal(window)

        def reveal_main():
            screen = (
                splash.screen()
                if splash is not None
                else QGuiApplication.screenAt(QCursor.pos()) or app.primaryScreen()
            )
            if screen is not None:
                window.setScreen(screen)
            center_window_on_screen(window, screen)
            configure_window_taskbar_identity(window, resources)
            # frameSwapped originates on the render thread with threaded backends.
            window.frameSwapped.connect(first_frame_reveal.reveal, Qt.QueuedConnection)
            window.show()
            # Account for any final frame adjustment by the window manager.
            center_window_on_screen(window, screen)
            app.setQuitOnLastWindowClosed(quit_on_last_window)

        window.startupRevealRequested.connect(reveal_main)

        def update_incubation_controller():
            # Async QML must keep loading while the main window is hidden, and
            # must use the main render loop after the splash has disappeared.
            if not isValid(engine) or not isValid(window):
                return
            active = window if window.isVisible() else splash
            engine.setIncubationController(
                active.incubationController() if active is not None and isValid(active) else None
            )

        window.visibleChanged.connect(update_incubation_controller)
        update_incubation_controller()
        window.setProperty("startupSplashHold", hold_startup_splash)
        return window
    except Exception:
        app.setQuitOnLastWindowClosed(quit_on_last_window)
        if own_splash:
            splash.hide()
            splash.deleteLater()
        raise


def main() -> int:
    _set_windows_app_id()

    resources = None
    instance = None
    startup = None
    try:
        # Must be set before creating QGuiApplication; affects this process only.
        os.environ.setdefault("QT_SCALE_FACTOR", str(_UI_SCALE))
        QQuickStyle.setStyle("Basic")
        app = QGuiApplication(sys.argv)
        instance = SingleInstance(get_config_dir(create=True) / "azauthlib-app.lock", app)
        if not instance.start():
            if not instance.forwarded:
                print(
                    "The running azauthlib instance is not responding to activation.",
                    file=sys.stderr,
                )
            return 0 if instance.forwarded else 1
        resources = PackageResources()
        configure_application_identity(app, resources)

        engine = QQmlApplicationEngine()
        engine.warnings.connect(_report_qml_warnings)
        preferences = load_startup_preferences(directory=profiles.get_config_dir(create=False))
        splash = (
            None if preferences["adaptive_splash"] else create_startup_splash(engine, resources)
        )
        startup = StartupBootstrap(app, engine, resources, splash)
        instance.activationRequested.connect(startup.activate)
        atexit.register(startup.shutdown)
        app.aboutToQuit.connect(startup.shutdown)
        startup.start_after_first_frame()
        return app.exec()
    finally:
        if startup is not None:
            startup.shutdown()
            atexit.unregister(startup.shutdown)
        if instance is not None:
            instance.close()
        if resources is not None:
            resources.close()


if __name__ == "__main__":
    raise SystemExit(main())
