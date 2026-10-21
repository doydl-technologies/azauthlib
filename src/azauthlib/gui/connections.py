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

"""Optional memory-only authentication tests with credential-bound outcome history."""

from __future__ import annotations

import hmac
import re
import secrets
import time
from contextlib import suppress
from threading import Event, Thread
from urllib.parse import urlsplit

import keyring
import requests
from msal import ConfidentialClientApplication, PublicClientApplication, TokenCache
from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from ..credentials import (
    KEYRING_SERVICE,
    CredentialStoreError,
    has_stored_secret,
    load_public_configuration,
    save_configuration,
)
from ..profiles import (
    ProfileStoreError,
    _validated_name,
    active_profile,
    create_profile,
    list_profiles,
    remove_profile,
    rename_profile,
    resolve_profile,
    select_profile,
)
from .connection_results import ConnectionResults

_STORE_ERRORS = (CredentialStoreError, ProfileStoreError, OSError, TypeError, ValueError)
_GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]


class _TestCancelled(RuntimeError):
    pass


class _TestHttpClient:
    """Bounded HTTPS transport that records only the token endpoint's status."""

    def __init__(self, cancel: Event):
        self.cancel = cancel
        self.deadline = time.monotonic() + 180
        self.session = requests.Session()
        self.token_status = 0

    def _request(self, method, url, **kwargs):
        if self.cancel.is_set() or time.monotonic() >= self.deadline:
            raise _TestCancelled()
        address = urlsplit(url)
        if address.scheme != "https" or address.hostname != "login.microsoftonline.com":
            raise ValueError("Only the Microsoft public-cloud authority is supported by this test.")
        # No redirects with posted credentials, and never disable TLS verification.
        kwargs["timeout"] = (5, 15)
        kwargs["allow_redirects"] = False
        kwargs["verify"] = True
        response = self.session.request(method, url, **kwargs)
        if address.path.rstrip("/").endswith("/token"):
            self.token_status = response.status_code
        if self.cancel.is_set():
            raise _TestCancelled()
        return response

    def get(self, url, **kwargs):
        return self._request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._request("POST", url, **kwargs)


def _result_message(result: dict, status: int) -> tuple[bool, str]:
    # A metadata HTTP 200 or a pending device code is not a successful login.
    if status == 200 and result.get("access_token") and not result.get("error"):
        return True, (
            "Test passed — HTTP 200. Microsoft issued an access token for this connection. "
            "This checks authentication, not permissions for every Microsoft Graph operation."
        )
    error = result.get("error", "no_access_token")
    if not isinstance(error, str) or not re.fullmatch(r"[a-zA-Z0-9_]{1,80}", error):
        error = "authentication_failed"
    guidance = {
        "invalid_client": "Check the client ID and secret value, including its expiry.",
        "unauthorized_client": "Check the app registration's authentication settings.",
        "invalid_scope": "Check the app's Microsoft Graph permissions and consent.",
        "access_denied": "Sign-in or consent was declined.",
        "authorization_declined": "Sign-in was declined.",
        "expired_token": "The sign-in code expired. Start a new test.",  # nosec B105 # Display text, not a token.
        "authorization_pending": "Sign-in was not completed before the test timed out.",
    }.get(error, "Check the tenant, app registration, permissions, and sign-in requirements.")
    code = f"HTTP {status}" if status else "no successful token response"
    # Never display raw response bodies, tokens, secrets, or exception strings.
    return False, f"Test did not pass — {code} ({error}). {guidance}"


def test_saved_connection(values: dict, cancel: Event, device_callback) -> tuple[bool, str]:
    """Authenticate saved values using MSAL with a fresh, memory-only cache."""

    transport = _TestHttpClient(cancel)
    try:
        authority = f"https://login.microsoftonline.com/{values['tenant_id']}"
        if values.get("authority") and values["authority"].rstrip("/") != authority:
            return (
                False,
                "This initial test supports the standard Microsoft public-cloud authority.",
            )
        options = {
            "client_id": values["client_id"],
            "authority": authority,
            "http_client": transport,
            "token_cache": TokenCache(),
            "instance_discovery": False,
            "enable_pii_log": False,
        }
        if values["auth_method"] == "client_credentials":
            secret = (
                values["_client_secret"]
                if "_client_secret" in values
                else keyring.get_password(KEYRING_SERVICE, values["client_id"])
            )
            if not secret:
                return (
                    False,
                    "No saved client secret was found. Edit and save this connection first.",
                )
            app = ConfidentialClientApplication(client_credential=secret, **options)
            result = app.acquire_token_for_client(scopes=_GRAPH_SCOPE)
        else:
            app = PublicClientApplication(exclude_scopes=["offline_access"], **options)
            if values["auth_method"] == "device_code":
                flow = app.initiate_device_flow(scopes=_GRAPH_SCOPE)
                if "user_code" not in flow:
                    return _result_message(flow, transport.token_status)
                device_callback(flow["user_code"], flow.get("verification_uri", ""))
                flow["expires_at"] = min(flow["expires_at"], time.time() + 180)
                result = app.acquire_token_by_device_flow(
                    flow,
                    exit_condition=lambda current: (
                        cancel.is_set() or current["expires_at"] < time.time()
                    ),
                )
            else:
                # MSAL uses the registered http://localhost desktop redirect URI.
                result = app.acquire_token_interactive(scopes=_GRAPH_SCOPE, timeout=120)
        if cancel.is_set():
            raise _TestCancelled()
        return _result_message(result or {}, transport.token_status)
    except _TestCancelled:
        return False, "Connection test cancelled or timed out."
    except requests.RequestException:
        return False, "Connection test could not reach Microsoft. Check your network and try again."
    except Exception:
        return False, (
            "Connection test could not complete. Check secure storage, tenant and app settings. "
            "Interactive sign-in needs the http://localhost desktop redirect URI."
        )
    finally:
        transport.session.close()


class ConnectionManagerController(QObject):
    """Keep manager selection and drafts separate from the main configuration form."""

    profilesChanged = Signal()
    selectionChanged = Signal()
    editorChanged = Signal()
    statusChanged = Signal()
    testChanged = Signal()
    deviceCodeChanged = Signal()
    storeChanged = Signal()
    activationRequested = Signal(str)
    actionCompleted = Signal(str)
    openingPrepared = Signal(bool)
    _openFinished = Signal(object)
    _testFinished = Signal(int, bool, str, object)
    _deviceReceived = Signal(int, str, str)

    def __init__(self, parent: QObject, *, startup_state=None):
        super().__init__(parent)
        self._profiles = []
        active = (
            startup_state["active"]
            if startup_state
            else (active_profile() if list_profiles() else None)
        )
        self._selected = active.id if active else ""
        self._editor = {}
        self._editing = False
        self._edit_secret_key = self._edit_secret_digest = None
        self._status = "Choose a saved connection, or add one. Testing is optional."
        self._status_kind = "information"
        self._busy = False
        self._device_code = ""
        self._device_url = ""
        self._job = 0
        self._cancel = Event()
        self._preparing_open = False
        self._results = startup_state["results"] if startup_state else ConnectionResults()
        self._prepared_startup = None
        self._openFinished.connect(self._finish_open)
        self._testFinished.connect(self._finish_test)
        self._deviceReceived.connect(self._receive_device)
        if startup_state:
            self._profiles = [{"id": p.id, "name": p.name} for p in startup_state["profiles"]]
            self._editor = startup_state["editor"]
            self._prepared_startup = {
                "profiles": self._profiles,
                "selected": self._selected,
                "editor": self._editor,
            }
        else:
            self.refresh()

    @Property("QVariantList", notify=profilesChanged)
    def profiles(self):
        return self._profiles

    @Property(str, notify=selectionChanged)
    def selectedId(self):
        return self._selected

    @Property("QVariantMap", notify=editorChanged)
    def editor(self):
        return self._editor

    @Property(bool, notify=editorChanged)
    def editing(self):
        return self._editing

    @Property(bool, notify=editorChanged)
    def creatingConnection(self):
        return self._editing and not self._editor.get("id")

    @Slot(str, str, str, str, str, result=bool)
    def connectionDraftChanged(self, name, tenant, client, secret, method):
        """Compare effective saved values in memory; never return/read a secret here."""
        if not self._editing:
            return False
        if self.creatingConnection:
            return (
                any(value.strip() for value in (name, tenant, client, secret))
                or method != "interactive"
            )
        if any(
            value.strip() != self._editor.get(field, "")
            for field, value in (
                ("name", name),
                ("tenant", tenant),
                ("client", client),
                ("method", method),
            )
        ):
            return True
        # Blank means retain the saved secret, and other methods do not save it.
        if method != "client_credentials" or not secret:
            return False
        if self._edit_secret_digest is None:
            return True  # Secure storage was unavailable: do not discard a replacement.
        candidate = hmac.digest(self._edit_secret_key, secret.encode("utf-8"), "sha256")
        return not hmac.compare_digest(candidate, self._edit_secret_digest)

    @Slot(str, str, str, str, str, result="QVariantMap")
    def validateConnectionDraft(self, name, tenant, client, secret, method):
        """Validate draft values without filesystem or credential-store access."""
        from .config_app import validate_client_id, validate_client_secret, validate_tenant_id

        errors = {}
        try:
            normalized = _validated_name(name)
            if any(
                p["name"].casefold() == normalized.casefold() and p["id"] != self._editor.get("id")
                for p in self._profiles
            ):
                errors["name"] = "A connection with this name already exists."
        except (TypeError, ValueError) as exc:
            errors["name"] = str(exc)
        tenant, client = tenant.strip(), client.strip()
        if not tenant:
            errors["tenant"] = "Tenant ID or verified domain is required."
        elif not validate_tenant_id(tenant):
            errors["tenant"] = "Use a tenant UUID, verified domain, or supported audience."
        elif method == "client_credentials" and tenant in ("common", "organizations", "consumers"):
            errors["tenant"] = "Client credentials needs a specific tenant UUID or domain."
        if not client:
            errors["client"] = "Application (client) ID is required."
        elif not validate_client_id(client):
            errors["client"] = "Use the Application (client) UUID from Entra."
        if method not in ("interactive", "device_code", "client_credentials"):
            errors["method"] = "Choose a supported authentication method."
        if method == "client_credentials":
            reusable = (
                not self.creatingConnection
                and self._editor.get("hasSecret")
                and client == self._editor.get("client")
            )
            if not secret and not reusable:
                errors["secret"] = "Client secret value is required for this method."  # nosec B105 # noqa: S105 -- validation message
            elif secret and not validate_client_secret(secret):
                errors["secret"] = "Secret must contain non-space text and no control characters."  # nosec B105 # noqa: S105 -- validation message
        return {**errors, "valid": not errors}

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Property(str, notify=statusChanged)
    def statusKind(self):
        return self._status_kind

    @Property(bool, notify=testChanged)
    def testing(self):
        return self._busy

    @Property(str, notify=editorChanged)
    def testResult(self):
        return "untested" if self._editing else self._editor.get("testResult", "untested")

    @Property(str, notify=deviceCodeChanged)
    def deviceCode(self):
        return self._device_code

    @Property(str, notify=deviceCodeChanged)
    def deviceUrl(self):
        return self._device_url

    @Slot(result=bool)
    def copyDeviceCode(self):
        """Copy only the currently active sign-in code, never its label or URL."""
        if not self._busy or not self._device_code or QGuiApplication.instance() is None:
            return False
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return False
        clipboard.setText(self._device_code)
        return True

    def _set_status(self, text, kind="information"):
        self._status, self._status_kind = text, kind
        self.statusChanged.emit()

    @Slot()
    def refresh(self):
        try:
            self._profiles = [{"id": p.id, "name": p.name} for p in list_profiles()]
            self.profilesChanged.emit()
            if self._selected not in [p["id"] for p in self._profiles]:
                self._selected = self._profiles[0]["id"] if self._profiles else ""
                self.selectionChanged.emit()
            if not self._editing:
                self._load_editor()
                if not self._profiles:
                    self._set_status("No connections yet. Add a connection to get started.")
        except _STORE_ERRORS as exc:
            self._set_status(str(exc), "error")

    def _load_editor(self):
        self._edit_secret_key = self._edit_secret_digest = None
        if not self._selected:
            self._editor = {}
            self.editorChanged.emit()
            return
        profile = resolve_profile(self._selected)
        self._editor = self._read_editor(profile)
        if self._editing and self._editor.get("hasSecret"):
            # One edit-session snapshot, not a keyring lookup on each keystroke.
            # Only an ephemeral, keyed digest stays in Python; never send it to QML.
            self._edit_secret_key = secrets.token_bytes(32)
            try:
                value = keyring.get_password(KEYRING_SERVICE, self._editor["client"])
                if value is not None:
                    self._edit_secret_digest = hmac.digest(
                        self._edit_secret_key, value.encode("utf-8"), "sha256"
                    )
            except Exception:
                self._edit_secret_digest = None
        self.editorChanged.emit()

    def _read_editor(self, profile):
        """Read public values and secret presence, never return a stored secret."""
        values = load_public_configuration(profile=profile.id)
        try:
            stored = has_stored_secret(values.get("client_id"))
        except CredentialStoreError:
            stored = False
        return {
            "id": profile.id,
            "name": profile.name,
            "tenant": values.get("tenant_id") or "",
            "client": values.get("client_id") or "",
            "method": values["auth_method"],
            "hasSecret": stored,
            "testResult": self._results.state(profile.id, values),
        }

    @Slot()
    def prepareForOpen(self):
        """Perform potentially slow file/keyring reads without blocking QML."""
        if self._preparing_open:
            return
        self._preparing_open = True
        if self._prepared_startup is not None:
            prepared, self._prepared_startup = self._prepared_startup, None
            QTimer.singleShot(0, self, lambda: self._finish_open(prepared))
            return
        selected = self._selected

        def prepare():
            try:
                saved = list_profiles()
                profile = next((p for p in saved if p.id == selected), saved[0] if saved else None)
                result = {
                    "profiles": [{"id": p.id, "name": p.name} for p in saved],
                    "selected": profile.id if profile else "",
                    "editor": self._read_editor(profile) if profile else {},
                }
            except Exception:
                # Do not expose credential-store exception contents to the UI.
                result = None
            with suppress(RuntimeError):
                self._openFinished.emit(result)

        try:
            Thread(target=prepare, daemon=True, name="connections-open").start()
        except RuntimeError:
            self._finish_open(None)

    @Slot(object)
    def _finish_open(self, result):
        # Queued signal delivery applies all QObject state on the UI thread.
        self._preparing_open = False
        if result is None:
            self.openingPrepared.emit(False)
            return
        self._profiles = result["profiles"]
        self._selected = result["selected"]
        self._editor = result["editor"]
        self._editing = False
        self.profilesChanged.emit()
        self.selectionChanged.emit()
        self.editorChanged.emit()
        if not self._profiles:
            self._set_status("No connections yet. Add a connection to get started.")
        self.openingPrepared.emit(True)

    @Slot(str)
    def selectConnection(self, profile_id):
        if self._busy or self._editing:
            return
        try:
            self._selected = resolve_profile(profile_id).id
            self._editing = False
            self.selectionChanged.emit()
            self._load_editor()
            self._set_status(
                f"Viewing saved details for “{self._editor['name']}”. Click Edit to change them."
            )
        except _STORE_ERRORS as exc:
            self._set_status(str(exc), "error")

    @Slot()
    def beginAdd(self):
        if self._busy or self._editing:
            return
        self._editing = True
        self._edit_secret_key = self._edit_secret_digest = None
        self._editor = {
            "id": "",
            "name": "",
            "tenant": "",
            "client": "",
            "method": "interactive",
            "hasSecret": False,
        }
        self.editorChanged.emit()
        self._set_status("Enter your Microsoft Entra app registration values. Testing is optional.")

    @Slot()
    def beginEdit(self):
        if self._busy or self._editing or not self._selected:
            return
        try:
            self._editing = True
            self._load_editor()
            self._set_status(
                "Leave the secret blank to keep the saved secret for the same client ID."
            )
        except _STORE_ERRORS as exc:
            self._set_status(str(exc), "error")

    @Slot()
    def cancelEdit(self):
        was_editing = self._editing
        self._editing = False
        self._edit_secret_key = self._edit_secret_digest = None
        self.refresh()
        if was_editing and self._editor:
            self._set_status("Changes cancelled. Your saved connection has not changed.")

    @Slot(str, str, str, str, str, result=bool)
    def saveConnection(self, name, tenant, client, secret, method):
        from .config_app import validate_client_id, validate_client_secret, validate_tenant_id

        if not self._editing or self._busy:
            return False
        tenant, client = tenant.strip(), client.strip()
        if not validate_tenant_id(tenant) or not validate_client_id(client):
            self._set_status(
                "Enter a valid Tenant ID/domain and Application (client) UUID.", "error"
            )
            return False
        if method not in ("interactive", "device_code", "client_credentials"):
            self._set_status("Choose a supported authentication method.", "error")
            return False
        if method == "client_credentials" and tenant in ("common", "organizations", "consumers"):
            self._set_status("Client credentials requires a specific tenant ID or domain.", "error")
            return False
        if secret and not validate_client_secret(secret):
            self._set_status("The secret contains unsupported control characters.", "error")
            return False
        created = None
        original = None
        try:
            if method == "client_credentials" and not secret and not has_stored_secret(client):
                self._set_status(
                    "Client credentials requires a secret value (not its Secret ID).", "error"
                )
                return False
            if self._editor["id"]:
                original = resolve_profile(self._editor["id"])
                profile = rename_profile(original, name)
                authority = load_public_configuration(profile=profile.id).get("authority")
            else:
                profile = created = create_profile(name, select=False)
                authority = None
            save_configuration(
                client_id=client,
                tenant_id=tenant,
                client_secret=secret or None,
                profile=profile.id,
                auth_method=method,
                authority=authority,
            )
        except _STORE_ERRORS as exc:
            with suppress(*_STORE_ERRORS):
                if created:
                    remove_profile(created)
                elif original:
                    rename_profile(original, original.name)
            self.refresh()
            self._set_status(f"Unable to save connection: {exc}", "error")
            return False
        self._selected = profile.id
        self._editing = False
        self._edit_secret_key = self._edit_secret_digest = None
        self.selectionChanged.emit()
        self.refresh()
        self.storeChanged.emit()
        self._set_status(
            f'"{profile.name}" saved securely. '
            "You can test it, or set it as the active connection.",
            "success",
        )
        self.actionCompleted.emit("created" if created else "saved")
        return True

    @Slot()
    def useSelected(self):
        if self._busy or self._editing or not self._selected:
            return
        try:
            profile = select_profile(self._selected)
            self.activationRequested.emit(profile.id)
            self._set_status(f'"{profile.name}" is now the active connection.', "success")
            self.actionCompleted.emit("activated")
        except _STORE_ERRORS as exc:
            self._set_status(str(exc), "error")

    @Slot()
    def removeSelected(self):
        if self._busy or self._editing or not self._selected:
            return
        try:
            profile = remove_profile(self._selected)
            self._results.forget(profile.id)
            self.refresh()
            self.storeChanged.emit()
            self._set_status(
                f'"{profile.name}" removed. Files archived under removed-profiles in '
                "app config/cache storage; shared OS secrets were kept.",
                "success",
            )
            self.actionCompleted.emit("removed")
        except _STORE_ERRORS as exc:
            self._set_status(str(exc), "error")

    @Slot()
    def testSelected(self):
        from .config_app import validate_client_id, validate_tenant_id

        if self._busy or self._editing or not self._selected:
            return
        try:
            profile = resolve_profile(self._selected)
            values = load_public_configuration(profile=profile.id)
            if not validate_tenant_id(values.get("tenant_id") or "") or not validate_client_id(
                values.get("client_id") or ""
            ):
                self._set_status(
                    "Save valid credentials for this connection before testing.", "error"
                )
                return
        except _STORE_ERRORS as exc:
            self._set_status(str(exc), "error")
            return
        self._job += 1
        job = self._job
        self._cancel = cancel = Event()
        self._busy = True
        self._device_code = self._device_url = ""
        self.testChanged.emit()
        self.deviceCodeChanged.emit()
        message = f'Testing "{profile.name}"'
        if values["auth_method"] == "interactive":
            message += " — complete sign-in in your browser (up to two minutes)."
        else:
            message += " — waiting for Microsoft."
        self._set_status(message)

        def run():
            def device(code, url):
                with suppress(RuntimeError):
                    self._deviceReceived.emit(job, code, url)

            snapshot = dict(values)
            if snapshot["auth_method"] == "client_credentials":
                try:
                    snapshot["_client_secret"] = keyring.get_password(
                        KEYRING_SERVICE, snapshot["client_id"]
                    )
                except Exception:
                    snapshot["_client_secret"] = None
            tag = self._results.fingerprint(snapshot, create=True)
            try:
                passed, message = test_saved_connection(snapshot, cancel, device)
            except Exception:
                # Always deliver completion if an unexpected worker error escapes
                # the transport helper. Never expose exception/credential text.
                passed, message = (
                    False,
                    (
                        "Connection test could not complete. Check your connection settings "
                        "and try again."
                    ),
                )
            proof = None
            if not cancel.is_set() and tag:
                try:
                    current = load_public_configuration(profile=profile.id)
                    current_tag = self._results.fingerprint(current)
                    proof = {
                        "profile": profile.id,
                        "fingerprint": tag if current_tag == tag else None,
                        "credentialsChanged": current_tag is not None and current_tag != tag,
                    }
                except _STORE_ERRORS:
                    pass
            with suppress(RuntimeError):
                self._testFinished.emit(job, passed, message, proof)

        # No work happens on the GUI thread, and closing the app never waits for
        # an abandoned browser sign-in. Cancellation prevents subsequent HTTP.
        Thread(target=run, name="azauthlib-connection-test", daemon=True).start()

    @Slot()
    def cancelTest(self):
        if not self._busy:
            return
        self._cancel.set()
        self._job += 1  # Ignore any late response from the cancelled operation.
        self._busy = False
        self._device_code = self._device_url = ""
        self.testChanged.emit()
        self.deviceCodeChanged.emit()
        self._set_status("Test cancelled. Any browser sign-in tab may be closed.")

    @Slot(int, str, str)
    def _receive_device(self, job, code, url):
        if job != self._job or not self._busy:
            return
        self._device_code, self._device_url = code, url
        self.deviceCodeChanged.emit()
        self._set_status("Enter the code at Microsoft's sign-in page, then return here.")

    @Slot(int, bool, str, object)
    def _finish_test(self, job, passed, message, proof=None):
        if job != self._job or not self._busy:
            return
        if proof and proof.get("fingerprint"):
            self._results.remember(proof["profile"], proof["fingerprint"], passed)
        # The worker verified the saved values and secret. No further keyring
        # access is needed on the UI thread merely to update the icon.
        verified = proof and proof.get("fingerprint") and proof["profile"] == self._selected
        self._editor["testResult"] = ("passed" if passed else "failed") if verified else "untested"
        self.editorChanged.emit()
        self._busy = False
        self._device_code = self._device_url = ""
        self.testChanged.emit()
        self.deviceCodeChanged.emit()
        if proof and proof.get("credentialsChanged"):
            self._set_status(
                "Saved credentials changed while testing. Test the current credentials again."
            )
        else:
            self._set_status(message, "success" if passed else "error")
