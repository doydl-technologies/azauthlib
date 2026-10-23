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

"""Creation, protected output, cancellation, and GUI handoff use isolated fixtures only."""

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event

import pytest
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12

from azauthlib import certificate_creation, profiles
from azauthlib.certificate_creation import (
    CertificateCreationCancelled,
    create_certificate,
    validate_creation,
)
from azauthlib.certificates import CertificateError, import_certificate

PASSWORD = "temporary-fixture-passphrase"


def options(folder, **overrides):
    return {
        "name": "Fixture certificate",
        "format": "pfx",
        "days": "90",
        "password": PASSWORD,
        "confirmation": PASSWORD,
        "output_folder": str(folder),
        **overrides,
    }


@pytest.mark.parametrize("days", ["", "0", "-1", "1.5", "forever", "99999999999"])
def test_bad_timeframes_are_rejected_without_writes(tmp_path, days):
    folder = tmp_path / "not-created"
    result = validate_creation(**options(folder, days=days))
    assert not result["valid"] and result["days"]
    with pytest.raises(CertificateError):
        create_certificate(**options(folder, days=days))
    assert not folder.exists()


def test_field_validation_and_default_expiration(tmp_path):
    result = validate_creation(**options(tmp_path))
    assert result["valid"]
    expiry = datetime.fromisoformat(result["expires"])
    assert abs((expiry - datetime.now(timezone.utc) - timedelta(days=90)).total_seconds()) < 3
    for changes, field in [
        ({"name": " "}, "name"),
        ({"name": "x" * 65}, "name"),
        ({"password": "abc"}, "password"),
        ({"confirmation": "different"}, "confirmation"),
        ({"format": "unknown"}, "format"),
        ({"output_folder": "relative"}, "folder"),
    ]:
        assert validate_creation(**options(tmp_path, **changes))[field]


@pytest.mark.parametrize(("format", "days"), [("pfx", "90"), ("pem", "180")])
def test_created_files_are_encrypted_and_importable(tmp_path, format, days):
    result = create_certificate(**options(tmp_path, format=format, days=days))
    imported = import_certificate(result, PASSWORD)
    public = x509.load_der_x509_certificate(Path(result["public_cer"]).read_bytes())
    assert public.not_valid_after_utc == datetime.fromisoformat(imported.public["not_after"])
    assert (
        abs(
            (
                public.not_valid_after_utc - datetime.now(timezone.utc) - timedelta(days=int(days))
            ).total_seconds()
        )
        < 5
    )
    assert not public.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
    assert public.extensions.get_extension_for_class(x509.KeyUsage).value.digital_signature
    assert public.public_key().key_size == 3072
    assert public.signature_hash_algorithm.name == "sha256"
    private = Path(result["key_path"]).read_bytes()
    assert PASSWORD.encode() not in private
    if format == "pem":
        assert b"BEGIN ENCRYPTED PRIVATE KEY" in private
    else:
        assert pkcs12.load_key_and_certificates(private, PASSWORD.encode())[0] is not None
    with pytest.raises(CertificateError):
        import_certificate(result, "incorrect-password")
    assert set(p.name for p in Path(result["folder"]).iterdir()) == {
        "azauthlib.private.pfx" if format == "pfx" else "azauthlib.private.pem",
        "azauthlib.public.cer",
        "azauthlib.public.pem",
    }
    if os.name != "nt":
        assert Path(result["folder"]).stat().st_mode & 0o777 == 0o700
        assert Path(result["key_path"]).stat().st_mode & 0o777 == 0o600


def test_existing_credentials_never_overwritten(tmp_path):
    marker = tmp_path / "azauthlib.private.pfx"
    marker.write_bytes(b"existing-user-file")
    first = create_certificate(**options(tmp_path))
    second = create_certificate(**options(tmp_path))
    assert first["folder"] != second["folder"]
    assert marker.read_bytes() == b"existing-user-file"
    assert Path(first["key_path"]).read_bytes() != Path(second["key_path"]).read_bytes()


def test_cancel_before_work_creates_nothing(tmp_path):
    cancel = Event()
    cancel.set()
    with pytest.raises(CertificateCreationCancelled):
        create_certificate(**options(tmp_path / "not-created"), cancel=cancel)
    assert not (tmp_path / "not-created").exists()


@pytest.mark.parametrize("cancelled", [False, True])
def test_mid_write_failure_or_cancel_rolls_back_only_generated_files(
    tmp_path, monkeypatch, cancelled
):
    marker = tmp_path / "existing.txt"
    marker.write_text("preserve me", encoding="ascii")
    cancel = Event()
    original = certificate_creation.os.fsync

    def interrupt(fd):
        if cancelled:
            original(fd)
            cancel.set()
        else:
            raise OSError("Simulated write failure")

    monkeypatch.setattr(certificate_creation.os, "fsync", interrupt)
    with pytest.raises(CertificateError):
        create_certificate(**options(tmp_path), cancel=cancel)
    assert list(tmp_path.iterdir()) == [marker]


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL behavior")
def test_windows_folder_acl_failure_writes_no_private_material(tmp_path, monkeypatch):
    def fail(_):
        raise OSError("Simulated ACL failure")

    monkeypatch.setattr(certificate_creation, "_protect_windows_directory", fail)
    with pytest.raises(CertificateError):
        create_certificate(**options(tmp_path))
    assert not list(tmp_path.iterdir())


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL behavior")
def test_windows_output_directory_has_protected_dacl(tmp_path):
    import ctypes
    from ctypes import wintypes

    files = create_certificate(**options(tmp_path))
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    get_security = advapi.GetFileSecurityW
    get_security.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    get_security.restype = wintypes.BOOL
    needed = wintypes.DWORD()
    get_security(files["folder"], 4, None, 0, ctypes.byref(needed))
    assert needed.value
    descriptor = ctypes.create_string_buffer(needed.value)
    assert get_security(files["folder"], 4, descriptor, needed.value, ctypes.byref(needed))
    get_control = advapi.GetSecurityDescriptorControl
    get_control.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.WORD),
        ctypes.POINTER(wintypes.DWORD),
    ]
    get_control.restype = wintypes.BOOL
    control, revision = wintypes.WORD(), wintypes.DWORD()
    assert get_control(descriptor, ctypes.byref(control), ctypes.byref(revision))
    assert control.value & 0x1000  # SE_DACL_PROTECTED: no permissive parent inheritance.


@pytest.fixture
def qt_app(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuickControls2 import QQuickStyle

    if QGuiApplication.instance() is None:
        QQuickStyle.setStyle("Basic")
    return QGuiApplication.instance() or QGuiApplication([])


def wait_for(app, predicate):
    deadline = time.monotonic() + 10
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert predicate()


def test_controller_stays_responsive_and_blocks_duplicate_jobs(qt_app, tmp_path, monkeypatch):
    from PySide6.QtCore import QObject

    from azauthlib.gui import certificate_creation as gui_creation

    started, release = Event(), Event()

    def generate(**kwargs):
        started.set()
        assert release.wait(5)
        assert kwargs["cancel"].is_set()
        raise CertificateCreationCancelled()

    monkeypatch.setattr(gui_creation, "create_certificate", generate)
    owner = QObject()
    creator = gui_creation.CertificateCreationController(owner, allowed=lambda: True)
    arguments = ("Fixture", "pfx", "90", PASSWORD, PASSWORD, str(tmp_path))
    assert creator.create(*arguments)
    wait_for(qt_app, started.is_set)
    assert creator.state["busy"] and PASSWORD not in str(creator.state)
    assert not creator.create(*arguments)
    creator.cancel()
    assert creator.state["cancelling"]
    release.set()
    wait_for(qt_app, lambda: not creator.state["busy"])
    assert "cancelled" in creator.state["message"]
    assert not creator.state["files"]


def test_late_cancel_keeps_output_paths_but_does_not_autofill(qt_app, tmp_path, monkeypatch):
    from PySide6.QtCore import QObject

    from azauthlib.gui import certificate_creation as gui_creation

    reached_return = Event()
    public_result = {"folder": str(tmp_path), "public_cer": str(tmp_path / "public.cer")}

    def generate(**_):
        reached_return.set()
        return public_result

    monkeypatch.setattr(gui_creation, "create_certificate", generate)
    owner = QObject()
    creator = gui_creation.CertificateCreationController(owner, allowed=lambda: True)
    emitted = []
    creator.created.connect(emitted.append)
    assert creator.create("Fixture", "pfx", "90", PASSWORD, PASSWORD, str(tmp_path))
    assert reached_return.wait(5)
    creator.cancel()  # Result is queued but has not been delivered to the UI yet.
    wait_for(qt_app, lambda: not creator.state["busy"])
    assert creator.state["files"] == public_result and not emitted
    assert "kept" in creator.state["message"]


@pytest.mark.parametrize("format", ["pfx", "pem"])
def test_gui_defaults_to_90_days_and_autofills_created_files(qt_app, tmp_path, format):
    from PySide6.QtCore import QMetaObject, QObject
    from PySide6.QtQml import QQmlApplicationEngine

    from azauthlib.gui.config_app import (
        ConfigurationController,
        PackageResources,
        load_configuration_qml,
    )

    resources = PackageResources()
    controller = ConfigurationController(resources, defer_connections=False)
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda entries: warnings.extend(e.toString() for e in entries))
    window = load_configuration_qml(engine, resources, controller, show_splash=False)
    wait_for(qt_app, lambda: window.findChild(QObject, "managerMethodSelector") is not None)
    window.setProperty("currentPage", "connections")
    window.setProperty("navigationProgress", 1)
    window.setProperty("startupRevealed", True)
    manager = controller.connectionManager
    manager.beginAdd()
    qt_app.processEvents()
    window.findChild(QObject, "managerMethodSelector").setProperty("currentIndex", 3)
    qt_app.processEvents()
    launch = window.findChild(QObject, "managerCreateCertificateButton")
    assert launch.property("enabled") and launch.property("visible")
    QMetaObject.invokeMethod(launch, "clicked")
    qt_app.processEvents()
    dialog = window.findChild(QObject, "managerCreateCertificateDialog")
    assert dialog.property("visible") and dialog.property("selectedDays") == "90"
    confirm = window.findChild(QObject, "certificateCreationConfirm")
    assert not confirm.property("enabled")
    for object_name, value in (
        ("certificateCreationName", "GUI fixture"),
        ("certificateCreationOutputFolder", str(tmp_path / "created files")),
        ("certificateCreationPassword", PASSWORD),
        ("certificateCreationConfirmation", "mismatch"),
    ):
        window.findChild(QObject, object_name).setProperty("text", value)
    assert not confirm.property("enabled")
    window.findChild(QObject, "certificateCreationConfirmation").setProperty("text", PASSWORD)
    window.findChild(QObject, "certificateCreationFormat").setProperty(
        "currentIndex", 1 if format == "pem" else 0
    )
    timeframe = window.findChild(QObject, "certificateCreationTimeframe")
    timeframe.setProperty("currentIndex", 4)
    custom_days = window.findChild(QObject, "certificateCreationDays")
    custom_days.setProperty("text", "0")
    assert not confirm.property("enabled")
    custom_days.setProperty("text", "45")
    assert confirm.property("enabled")
    QMetaObject.invokeMethod(confirm, "clicked")
    assert manager.certificateCreator.state["busy"] and not confirm.property("enabled")
    wait_for(qt_app, lambda: not dialog.property("visible"))
    wait_for(qt_app, lambda: manager.certificateImport.state.get("valid"))
    files = manager.certificateCreator.state["files"]
    assert files["days"] == 45 and files["format"] == format
    assert (
        window.findChild(QObject, "managerCertificateKeyField").property("text")
        == files["key_path"]
    )
    assert window.findChild(QObject, "managerCertificatePasswordField").property("text") == PASSWORD
    assert window.findChild(QObject, "certificateCreationPassword").property("text") == ""
    assert window.findChild(QObject, "certificateCreationConfirmation").property("text") == ""
    assert window.findChild(QObject, "managerGeneratedCertificateFiles").property("visible")
    assert not any(profile.name == "GUI fixture" for profile in profiles.list_profiles())
    QMetaObject.invokeMethod(launch, "clicked")
    qt_app.processEvents()
    assert dialog.property("selectedDays") == "90"
    assert not confirm.property("enabled")
    QMetaObject.invokeMethod(window.findChild(QObject, "certificateCreationCancel"), "clicked")
    wait_for(qt_app, lambda: not dialog.property("visible"))
    assert (
        window.findChild(QObject, "managerCertificateKeyField").property("text")
        == files["key_path"]
    )
    manager.cancelEdit()
    assert Path(files["key_path"]).is_file()  # Files survive cancelling the connection draft.
    assert not warnings, "\n".join(warnings)
    window.setProperty("closingAllowed", True)
    window.close()
    engine.deleteLater()
    qt_app.processEvents()
    resources.close()
