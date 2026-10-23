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

"""Debounced, stale-result-safe certificate validation for the connection editor."""

from contextlib import suppress
from threading import Thread

from PySide6.QtCore import Property, QFileSystemWatcher, QObject, QTimer, Signal, Slot

from ..certificates import CertificateError, file_identity, import_certificate
from ..credentials import CredentialStoreError, certificate_password


class CertificateImportController(QObject):
    changed = Signal()
    _finished = Signal(int)

    def __init__(self, parent):
        super().__init__(parent)
        self._generation = 0
        self._running = False
        self._worker_result = None
        self._request = None
        self._prepared = None
        self._original = {}
        self._last_input = None
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._file_changed)
        self._state = {
            "valid": False,
            "busy": False,
            "changed": False,
            "message": "Choose certificate files to validate.",
        }
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._start)
        self._finished.connect(self._finish)

    @Property("QVariantMap", notify=changed)
    def state(self):
        return self._state

    def reset(self, editor):
        self._generation += 1
        self._timer.stop()
        self._last_input = None
        if self._watcher.files():
            self._watcher.removePaths(self._watcher.files())
        self._request = self._prepared = None
        self._original = dict(editor)
        self._state = {
            "valid": False,
            "busy": False,
            "changed": False,
            "message": "Choose certificate files to validate.",
        }
        self.changed.emit()

    @Slot(str, str, str, str, bool, str, str)
    @Slot(str, str, str, str, bool, str, str, bool)
    def updateDraft(
        self,
        format,
        key_path,
        certificate_path,
        password,
        remember,
        client,
        tenant,
        no_password=False,
    ):
        self._last_input = (
            format,
            key_path,
            certificate_path,
            password,
            remember,
            client,
            tenant,
            no_password,
        )
        if self._watcher.files():
            self._watcher.removePaths(self._watcher.files())
        self._generation += 1
        self._prepared = None
        spec = {
            "format": format,
            "key_path": key_path.strip(),
            "certificate_path": certificate_path.strip() if format == "pem" else "",
        }
        self._request = (
            self._generation,
            spec,
            password,
            remember,
            client.strip(),
            tenant.strip(),
            dict(self._original),
            no_password,
        )
        self._state = {
            "valid": False,
            "busy": True,
            "changed": True,
            "message": "Validating certificate locally...",
        }
        self.changed.emit()
        self._timer.start()

    def _start(self):
        if self._running or self._request is None:
            return
        request, self._request = self._request, None
        self._running = True

        def validate():
            generation, spec, password, remember, client, tenant, original, no_password = request
            saved = original.get("certificate") or {}
            try:
                saved_password = None
                same_owner = client == original.get("client") and tenant == original.get("tenant")
                same_files = all(
                    spec.get(k, "") == saved.get(k, "")
                    for k in ("format", "key_path", "certificate_path")
                )
                if same_owner and not no_password:
                    saved_password = original.get("_session_password")
                    if saved.get("password_ref"):
                        try:
                            saved_password = certificate_password(
                                saved, profile=original["id"], client_id=client, tenant_id=tenant
                            )
                        except CredentialStoreError:
                            # A replacement password must be able to repair missing storage.
                            if not password:
                                raise
                effective_password = (
                    None if no_password else password or (saved_password if same_files else None)
                )
                imported = import_certificate(spec, effective_password, verify_fingerprint=False)
                if imported.identity != file_identity(spec):
                    raise CertificateError(
                        "The selected files changed during validation. Try again."
                    )
                # Authentication reloads the signing key; validation retains no key bytes.
                imported.credential.clear()
                changed = (
                    any(imported.public.get(k) != saved.get(k) for k in imported.public)
                    or bool(remember and effective_password) != bool(saved.get("password_ref"))
                    or bool(password and (effective_password != saved_password or not remember))
                )
                # Never emit key material, passwords or parser exception text.
                result = {
                    "public": imported.public,
                    "password": effective_password,
                    "remember": remember,
                    "client": client,
                    "tenant": tenant,
                    "changed": changed,
                    "identity": imported.identity,
                    "material": imported,
                }
            except (CertificateError, CredentialStoreError) as exc:
                result = {"error": str(exc)}
            except Exception:
                result = {
                    "error": (
                        "Certificate validation could not complete. "
                        "Check the selected files and secure storage."
                    )
                }
            # Keep sensitive results in Python, not in QML-visible signal payloads.
            self._worker_result = (generation, result)
            with suppress(RuntimeError):
                self._finished.emit(generation)

        Thread(target=validate, daemon=True, name="certificate-import").start()

    @Slot(str)
    def _file_changed(self, _path):
        if self._last_input is not None:
            self.updateDraft(*self._last_input)

    @Slot(int)
    def _finish(self, generation):
        completed, self._worker_result = self._worker_result, None
        if completed is None or completed[0] != generation:
            return
        result = completed[1]
        self._running = False
        if generation == self._generation:
            if "error" in result:
                self._state = {
                    "valid": False,
                    "busy": False,
                    "changed": True,
                    "message": result["error"],
                }
            else:
                self._prepared = result
                paths = [result["public"]["key_path"]]
                if result["public"]["format"] == "pem":
                    paths.append(result["public"]["certificate_path"])
                self._watcher.addPaths(paths)
                self._state = {
                    "valid": True,
                    "busy": False,
                    "changed": result["changed"],
                    "message": (
                        "Valid locally. Upload the public certificate to Entra, "
                        "then test authentication."
                    ),
                    **result["public"],
                }
            self.changed.emit()
        if self._request is not None:
            self._start()

    def prepared(self, client, tenant):
        value = self._prepared
        if (
            not value
            or self._state.get("busy")
            or value["client"] != client
            or value["tenant"] != tenant
        ):
            raise CertificateError(
                "Validate the certificate for this client and tenant before saving."
            )
        return value

    def discard(self):
        self.reset({})
