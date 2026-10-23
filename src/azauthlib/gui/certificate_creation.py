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

"""Non-blocking certificate generation; Qt signals carry public output details only."""

from contextlib import suppress
from threading import Event, Thread

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..appdata import get_config_dir
from ..certificate_creation import (
    CertificateCreationCancelled,
    create_certificate,
    validate_creation,
)
from ..certificates import CertificateError


class CertificateCreationController(QObject):
    changed = Signal()
    created = Signal("QVariantMap")
    _finished = Signal()

    def __init__(self, parent, *, allowed):
        super().__init__(parent)
        self._allowed = allowed
        self._busy = False
        self._cancel = Event()
        self._result = None
        self._state = {"busy": False, "cancelling": False, "message": "", "files": {}}
        self._finished.connect(self._finish)

    @Property("QVariantMap", notify=changed)
    def state(self):
        return self._state

    @Property(str, constant=True)
    def defaultFolder(self):
        return str(get_config_dir(create=False) / "certificates")

    @Slot(str, str, str, str, str, str, result="QVariantMap")
    def validate(self, name, format, days, password, confirmation, folder):
        return validate_creation(name, format, days, password, confirmation, folder)

    @Slot(str, str, str, str, str, str, result=bool)
    def create(self, name, format, days, password, confirmation, folder):
        if self._busy or not self._allowed():
            return False
        validation = self.validate(name, format, days, password, confirmation, folder)
        if not validation["valid"]:
            self._state = {
                "busy": False,
                "cancelling": False,
                "files": {},
                "message": "Correct the highlighted fields before creating a certificate.",
            }
            self.changed.emit()
            return False
        self._cancel = cancel = Event()
        self._busy = True
        self._state = {
            "busy": True,
            "cancelling": False,
            "files": {},
            "message": "Generating an encrypted RSA-3072 certificate...",
        }
        self.changed.emit()

        def generate():
            try:
                result = {
                    "files": create_certificate(
                        name=name,
                        format=format,
                        days=days,
                        password=password,
                        confirmation=confirmation,
                        output_folder=folder,
                        cancel=cancel,
                    )
                }
            except CertificateCreationCancelled:
                result = {
                    "message": "Certificate creation cancelled. No generated files were kept."
                }
            except CertificateError as exc:
                result = {"message": str(exc)}
            except Exception:
                result = {
                    "message": (
                        "Certificate creation could not complete. "
                        "Check the output folder and try again."
                    )
                }
            self._result = result
            with suppress(RuntimeError):
                self._finished.emit()

        try:
            Thread(target=generate, daemon=True, name="certificate-creation").start()
        except RuntimeError:
            self._result = {"message": "Unable to start certificate creation. Please try again."}
            self._finish()
        return True

    @Slot()
    def cancel(self):
        if self._busy:
            self._cancel.set()
            self._state = {
                **self._state,
                "cancelling": True,
                "message": "Cancelling after the current cryptographic operation...",
            }
            self.changed.emit()

    @Slot()
    def clear(self):
        if not self._busy:
            self._state = {"busy": False, "cancelling": False, "message": "", "files": {}}
            self.changed.emit()

    @Slot()
    def _finish(self):
        result, self._result = self._result or {}, None
        self._busy = False
        files = result.get("files", {})
        late_cancel = files and self._cancel.is_set()
        message = result.get(
            "message", "Certificate created. Upload only the public certificate to Entra."
        )
        if late_cancel:
            message = (
                "Creation finished before cancellation. Files were kept in: " + files["folder"]
            )
        self._state = {"busy": False, "cancelling": False, "files": files, "message": message}
        self.changed.emit()
        if files and not late_cancel and self._allowed():
            self.created.emit(files)
