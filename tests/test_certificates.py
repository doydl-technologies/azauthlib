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

"""Certificate import/authentication tests using disposable, isolated credentials."""

import base64
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from azauthlib import Authentication, authentication, credentials, profiles
from azauthlib.certificates import CertificateError, file_identity, import_certificate

CLIENT = "a8bf703b-a38a-4786-a4c1-96ea20531620"
TENANT = "91273e86-781d-4a9e-b3a1-e06c74d8a043"
PASSWORD = "disposable-fixture-password"


@pytest.fixture
def bundle(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Isolated fixture")])
    now = datetime.now(timezone.utc)

    def certificate(start=-1, end=90):
        return (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now + timedelta(days=start))
            .not_valid_after(now + timedelta(days=end))
            .sign(key, hashes.SHA256())
        )

    cert = certificate()
    key_path = tmp_path / "private key.pem"
    cert_path = tmp_path / "public certificate.pem"
    pfx_path = tmp_path / "certificate.pfx"
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(PASSWORD.encode()),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    pfx_path.write_bytes(
        pkcs12.serialize_key_and_certificates(
            b"fixture", key, cert, None, serialization.BestAvailableEncryption(PASSWORD.encode())
        )
    )
    return {
        "pem": {"format": "pem", "key_path": str(key_path), "certificate_path": str(cert_path)},
        "pfx": {"format": "pfx", "key_path": str(pfx_path)},
        "key": key,
        "certificate": certificate,
        "cert_path": cert_path,
    }


@pytest.mark.parametrize("format", ["pem", "pfx"])
def test_import_validates_pair_and_returns_sha256_credential(bundle, format):
    imported = import_certificate(bundle[format], PASSWORD)
    assert len(imported.public["fingerprint"]) == 64
    assert "private_key" not in imported.public
    assert "passphrase" not in imported.credential
    assert "thumbprint" not in imported.credential
    assert "BEGIN PRIVATE KEY" in imported.credential["private_key"]
    assert imported.identity == file_identity(bundle[format])
    assert "PRIVATE KEY" not in repr(imported)


@pytest.mark.parametrize("format", ["pem", "pfx"])
def test_wrong_password_is_safe_and_never_echoed(bundle, format):
    with pytest.raises(CertificateError) as error:
        import_certificate(bundle[format], "wrong-sensitive-password")
    assert "wrong-sensitive-password" not in str(error.value)
    assert "password" in str(error.value)


@pytest.mark.parametrize(
    ("start", "end", "message"), [(-90, -1, "expired"), (1, 90, "not valid yet")]
)
def test_dates_checked_locally(bundle, start, end, message):
    bundle["cert_path"].write_bytes(
        bundle["certificate"](start, end).public_bytes(serialization.Encoding.PEM)
    )
    with pytest.raises(CertificateError, match=message):
        import_certificate(bundle["pem"], PASSWORD)


def test_mismatch_and_public_only_rejected(bundle, tmp_path):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    path = tmp_path / "other.pem"
    path.write_bytes(
        other.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    with pytest.raises(CertificateError, match="does not match"):
        import_certificate({**bundle["pem"], "key_path": str(path)})
    with pytest.raises(CertificateError):
        import_certificate({"format": "pfx", "key_path": str(bundle["cert_path"])})


def test_rotation_pinned_until_explicit_reimport(bundle):
    saved = import_certificate(bundle["pem"], PASSWORD).public
    bundle["cert_path"].write_bytes(
        bundle["certificate"](-1, 180).public_bytes(serialization.Encoding.PEM)
    )
    with pytest.raises(CertificateError, match="has changed"):
        import_certificate(saved, PASSWORD)
    assert import_certificate(saved, PASSWORD, verify_fingerprint=False).public != saved


def save(bundle, profile, **kwargs):
    return credentials.save_configuration(
        profile=profile,
        client_id=CLIENT,
        tenant_id=TENANT,
        auth_method="client_certificate",
        certificate=import_certificate(bundle["pfx"], PASSWORD).public,
        certificate_password_value=PASSWORD,
        remember_certificate_password=True,
        **kwargs,
    )


def test_secure_profile_scoped_storage_and_default_builder(bundle):
    first, second = profiles.create_profile("First"), profiles.create_profile("Second")
    one, two = save(bundle, first), save(bundle, second)
    spec1 = credentials.load_public_configuration(profile=first)["certificate"]
    spec2 = credentials.load_public_configuration(profile=second)["certificate"]
    assert spec1["password_ref"] != spec2["password_ref"]
    assert PASSWORD not in one.read_text() + two.read_text()
    encoded = one.read_text().split("CERTIFICATE_CONFIG=", 1)[1].strip()
    assert PASSWORD not in json.dumps(json.loads(base64.b64decode(encoded)))
    assert (
        credentials.certificate_password(spec1, profile=first, client_id=CLIENT, tenant_id=TENANT)
        == PASSWORD
    )
    with pytest.raises(credentials.CredentialStoreError, match="different profile"):
        credentials.certificate_password(spec1, profile=second, client_id=CLIENT, tenant_id=TENANT)
    auth = Authentication(profile=first).Build.Default()
    assert auth.client_secret is None and auth.certificate["fingerprint"] == spec1["fingerprint"]


def test_certificate_auth_never_falls_back_to_environment_secret(bundle, monkeypatch):
    profile = profiles.create_profile("Certificate")
    save(bundle, profile)
    monkeypatch.setenv("CLIENT_SECRET", "must-not-use-this")
    auth = Authentication(profile=profile).Build.Default()
    captured = {}

    class App:
        def __init__(self, **options):
            captured.update(options)

        def acquire_token_for_client(self, scopes):
            assert scopes == ["https://graph.microsoft.com/.default"]
            return {"access_token": "fixture-token", "expires_in": 3600}

    monkeypatch.setattr(authentication, "ConfidentialClientApplication", App)
    monkeypatch.setattr(auth, "_cache", lambda: None)
    auth.ClientCredentials()
    assert isinstance(captured["client_credential"], dict)
    assert "private_key" in captured["client_credential"]
    Path(bundle["pfx"]["key_path"]).unlink()
    with pytest.raises(CertificateError):
        auth.ClientCredentials()


def test_configuration_failure_rolls_back_new_password(bundle, monkeypatch):
    profile = profiles.create_profile("Rollback")
    target = save(bundle, profile)
    original = target.read_bytes()
    before = []
    deleted = []
    setter = credentials.keyring.set_password
    deleter = credentials.keyring.delete_password
    monkeypatch.setattr(
        credentials.keyring, "set_password", lambda s, k, v: (before.append(k), setter(s, k, v))
    )
    monkeypatch.setattr(
        credentials.keyring, "delete_password", lambda s, k: (deleted.append(k), deleter(s, k))
    )

    def fail(*_):
        raise OSError("simulated failure")

    monkeypatch.setattr(credentials.os, "replace", fail)
    with pytest.raises(OSError):
        save(bundle, profile)
    assert before == deleted
    assert target.read_bytes() == original


def test_keyring_failure_does_not_fall_back_to_plaintext(bundle, monkeypatch):
    profile = profiles.create_profile("No keyring")

    def fail(*_):
        raise RuntimeError("sensitive backend details")

    monkeypatch.setattr(credentials.keyring, "set_password", fail)
    with pytest.raises(credentials.CredentialStoreError) as error:
        save(bundle, profile)
    assert "sensitive" not in str(error.value)
    assert not profiles.profile_config_path(profile).exists()


def test_remember_opt_out_removes_old_password_but_preserves_files(bundle):
    profile = profiles.create_profile("Opt out")
    save(bundle, profile)
    spec = credentials.load_public_configuration(profile=profile)["certificate"]
    credentials.save_configuration(
        profile=profile,
        client_id=CLIENT,
        tenant_id=TENANT,
        auth_method="client_certificate",
        certificate=spec,
        certificate_password_value=PASSWORD,
        remember_certificate_password=False,
    )
    current = credentials.load_public_configuration(profile=profile)["certificate"]
    assert "password_ref" not in current
    assert (
        credentials.keyring.get_password(credentials.CERTIFICATE_SERVICE, spec["password_ref"])
        is None
    )
    assert Path(spec["key_path"]).exists()


def test_certificate_connection_test_uses_confidential_app(bundle, monkeypatch):
    from threading import Event

    from azauthlib.gui import connections

    profile = profiles.create_profile("Test cert")
    save(bundle, profile)
    values = credentials.load_public_configuration(profile=profile)
    values["_profile_id"] = profile.id
    seen = []

    class App:
        def __init__(self, **options):
            seen.append(options["client_credential"])
            options["http_client"].token_status = 200

        def acquire_token_for_client(self, scopes):
            return {"access_token": "fixture-token"}

    monkeypatch.setattr(connections, "ConfidentialClientApplication", App)
    passed, message = connections.test_saved_connection(values, Event(), lambda *_: None)
    assert passed and "HTTP 200" in message
    assert "private_key" in seen[0]


@pytest.mark.parametrize("format", ["pfx", "pem"])
def test_real_msal_constructs_sha256_certificate_assertion_offline(bundle, format):
    from msal import ConfidentialClientApplication

    requests = []
    issuer = f"https://login.microsoftonline.com/{TENANT}/v2.0"

    class Response:
        status_code = 200
        headers = {}

        def __init__(self, value):
            self.text = json.dumps(value)

    class Transport:
        def get(self, url, **_):
            assert "openid-configuration" in url
            return Response(
                {
                    "authorization_endpoint": f"{issuer}/authorize",
                    "token_endpoint": f"{issuer}/token",
                    "issuer": issuer,
                }
            )

        def post(self, url, data=None, **_):
            assert url == f"{issuer}/token"
            assertion = data["client_assertion"]
            if isinstance(assertion, bytes):
                assertion = assertion.decode("ascii")
            header = assertion.split(".")[0]
            header = json.loads(base64.urlsafe_b64decode(header + "=" * (-len(header) % 4)))
            assert "x5t#S256" in header and "x5t" not in header
            assert "private_key" not in data and PASSWORD not in str(data)
            requests.append(header)
            return Response(
                {"access_token": "offline-fixture", "expires_in": 3600, "token_type": "Bearer"}
            )

    app = ConfidentialClientApplication(
        CLIENT,
        authority=f"https://login.microsoftonline.com/{TENANT}",
        client_credential=import_certificate(bundle[format], PASSWORD).credential,
        http_client=Transport(),
        instance_discovery=False,
    )
    assert app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])[
        "access_token"
    ]
    assert len(requests) == 1


def test_test_history_invalidated_by_file_replacement(bundle):
    from azauthlib.gui.connection_results import ConnectionResults

    values = {
        "auth_method": "client_certificate",
        "certificate": import_certificate(bundle["pem"], PASSWORD).public,
    }
    history = ConnectionResults()
    tag = history.fingerprint(values, create=True)
    history.remember("profile", tag, True)
    assert history.state("profile", values) == "passed"
    bundle["cert_path"].write_bytes(
        bundle["certificate"](-1, 180).public_bytes(serialization.Encoding.PEM)
    )
    assert history.state("profile", values) == "untested"


@pytest.fixture
def qt_app(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuickControls2 import QQuickStyle

    if QGuiApplication.instance() is None:
        QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication([])
    return app


def wait_for(qt_app, predicate):
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        qt_app.processEvents()
        time.sleep(0.005)
    assert predicate()


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        ("CN=Signer", "CN=Signer"),
        (r"O=Example,CN=Signer\, Production", "CN=Signer, Production"),
        ("OU=Only a unit", "Not provided"),
        ("not a distinguished name", "not a distinguished name"),
        ("", "Not provided"),
    ],
)
def test_certificate_common_name_is_display_only(subject, expected, qt_app):
    from PySide6.QtCore import QObject

    from azauthlib.gui.connections import ConnectionManagerController

    owner = QObject()
    manager = ConnectionManagerController(owner)
    original = manager.editor.copy()
    assert manager.certificateCommonName(subject) == expected
    assert manager.editor == original


def test_async_import_save_cancel_and_no_secret_in_qml_state(bundle, qt_app):
    from PySide6.QtCore import QObject

    from azauthlib.gui.connections import ConnectionManagerController

    owner = QObject()
    manager = ConnectionManagerController(owner)
    manager.beginAdd()
    manager.resetCertificateDraft()
    importer = manager.certificateImport
    spec = bundle["pfx"]
    importer.updateDraft("pfx", spec["key_path"], "", PASSWORD, True, CLIENT, TENANT)
    assert not manager.validateConnectionDraft("Cert", TENANT, CLIENT, "", "client_certificate")[
        "valid"
    ]
    wait_for(qt_app, lambda: importer.state.get("valid"))
    assert PASSWORD not in str(importer.state)
    assert manager.saveConnection("Cert", TENANT, CLIENT, "", "client_certificate")
    assert manager.editor["certificate"]["fingerprint"]
    manager.beginEdit()
    manager.resetCertificateDraft()
    importer.updateDraft("pfx", spec["key_path"], "", "", True, CLIENT, TENANT)
    wait_for(qt_app, lambda: importer.state.get("valid"))
    assert not importer.state["changed"]
    importer.updateDraft("pfx", spec["key_path"], "", "invalid", True, CLIENT, TENANT)
    manager.cancelEdit()
    wait_for(qt_app, lambda: not importer._running)
    assert not importer.state["valid"] and importer._prepared is None


def test_replacing_encrypted_file_with_unencrypted_file_can_clear_retained_password(bundle, qt_app):
    from PySide6.QtCore import QObject

    from azauthlib.gui.connections import ConnectionManagerController

    profile = profiles.create_profile("Remove password")
    save(bundle, profile)
    owner = QObject()
    manager = ConnectionManagerController(owner)
    manager.selectConnection(profile.id)
    manager.beginEdit()
    manager.resetCertificateDraft()
    path = Path(bundle["pfx"]["key_path"])
    path.write_bytes(
        pkcs12.serialize_key_and_certificates(
            b"fixture", bundle["key"], bundle["certificate"](), None, serialization.NoEncryption()
        )
    )
    importer = manager.certificateImport
    importer.updateDraft("pfx", str(path), "", "", False, CLIENT, TENANT, True)
    wait_for(qt_app, lambda: importer.state.get("valid"))
    assert importer.state["changed"]
    assert manager.saveConnection("Remove password", TENANT, CLIENT, "", "client_certificate")
    assert "password_ref" not in manager.editor["certificate"]


def test_connection_action_tiles_keep_slots_and_preserve_editor_rules(qt_app):
    from PySide6.QtCore import QMetaObject, QObject, QPointF
    from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
    from PySide6.QtQuick import QQuickItem

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
    wait_for(qt_app, lambda: window.findChild(QObject, "managerAddButton") is not None)
    window.setProperty("currentPage", "connections")
    window.setProperty("navigationProgress", 1)
    window.setProperty("startupRevealed", True)
    panel = window.findChild(QQuickItem, "connectionsHomeContent")
    window.show()  # Expose the offscreen window so grabToImage exercises real transitions.
    manager = controller.connectionManager
    # Direct controller construction creates a legacy default profile. Remove
    # that isolated fixture so this exercise starts with a genuinely empty list.
    for _ in list(manager.profiles):
        manager.removeSelected()
    qt_app.processEvents()
    assert not manager.profiles

    def item(name):
        return window.findChild(QQuickItem, "manager" + name)

    def position(name):
        return item(name).mapToItem(panel, QPointF(0, 0))

    def cancel_is_centered():
        cancel = item("CancelButton")
        actions = item("SidebarActions")
        center = cancel.mapToItem(actions, QPointF(cancel.width() / 2, cancel.height() / 2))
        return abs(center.x() - actions.width() / 2) < 0.01

    def assert_close_centered(button):
        artwork = button.findChild(QQuickItem, "connectionSvgImage")
        center = artwork.mapToItem(button, QPointF(artwork.width() / 2, artwork.height() / 2))
        assert center.x() == pytest.approx(button.width() / 2)
        assert center.y() == pytest.approx(button.height() / 2)

    def click(name):
        button = item(name)
        assert button.property("visible") and button.property("enabled")
        QMetaObject.invokeMethod(button, "clicked")
        wait_for(qt_app, lambda: not panel.property("contentTransitionBusy"))
        qt_app.processEvents()

    def preview(name):
        directory = os.environ.get("AZAUTHLIB_ACTION_PREVIEW_DIR")
        if directory:
            window.grabWindow().save(str(Path(directory) / name))

    qt_app.processEvents()
    icons = {
        "AddButton": "Monocolor-Filled-Sky-Blue-circle-plus.svg",
        "EditButton": "edit-utensil.svg",
        "RemoveButton": "Monocolor-Outlined-Pink-Red-trash.svg",
        "UseButton": "Monocolor-Rounded-Filled-Light-Gray-Radio-Button-Checked.svg",
    }
    for name, filename in icons.items():
        button = item(name)
        assert button.property("tileLayout")
        tooltip = QQmlExpression(engine.contextForObject(button), button, "ToolTip.text")
        assert tooltip.evaluate()[0] == ""
        assert button.property("iconSource").toString().endswith("/actions/" + filename)
        assert 80 <= button.width() <= 116
        assert button.height() == 46
    assert position("AddButton").x() == position("RemoveButton").x()
    assert position("EditButton").x() == position("UseButton").x()
    assert position("AddButton").y() == position("EditButton").y()
    assert position("RemoveButton").y() == position("UseButton").y()
    assert (
        position("RemoveButton").y() + item("RemoveButton").height()
        < position("ProfilesViewport").y()
    )
    assert not item("EditButton").property("enabled")
    assert not item("RemoveButton").property("enabled")
    assert not item("UseButton").property("enabled")
    assert item("UseButton").property("text") == "Set Active"
    assert item("UseButtonSurface").property("borderColor").name() == "#cccccc"
    assert item("UseButton").property("textColor").name() == "#cccccc"
    assert item("EditButtonSurface").property("borderColor").name() == "#345b85"
    assert window.findChild(QObject, "managerEmptyAddButton") is None
    assert window.findChild(QObject, "managerDetailActions") is None
    avatar_button = item("ChangeAvatar")
    avatar_tip = QQmlExpression(
        engine.contextForObject(avatar_button), avatar_button, "ToolTip.text"
    )
    assert avatar_tip.evaluate()[0] == "Choose avatar"
    profile_y = position("ProfilesViewport").y()
    add_position = position("AddButton")
    edit_position = position("EditButton")

    click("AddButton")
    assert manager.editing and manager.creatingConnection
    assert position("CancelButton") == add_position
    assert position("SaveButton") == edit_position
    assert position("ProfilesViewport").y() == profile_y
    assert not item("AddButton").property("visible")
    assert not item("EditButton").property("visible")
    assert not item("RemoveButton").property("visible")
    assert not item("UseButton").property("visible")
    assert item("SaveButton").property("visible")
    assert not item("SaveButton").property("enabled")
    preview("connection-actions-create.png")
    click("CancelButton")
    assert not manager.editing and manager.profiles == []

    click("AddButton")
    for name, text in (
        ("NameField", "Tile layout profile"),
        ("TenantField", TENANT),
        ("ClientField", CLIENT),
    ):
        item(name).setProperty("text", text)
    qt_app.processEvents()
    assert item("SaveButton").property("enabled")
    click("SaveButton")
    assert not manager.editing and len(manager.profiles) == 1
    assert manager.editor["name"] == "Tile layout profile"
    preview("connection-actions-saved.png")

    click("EditButton")
    assert manager.editing and not manager.creatingConnection
    assert not item("SaveButton").property("visible")
    wait_for(qt_app, cancel_is_centered)
    preview("connection-actions-cancel-only.png")
    assert position("ProfilesViewport").y() == profile_y
    item("NameField").setProperty("text", "Changed profile")
    qt_app.processEvents()
    assert item("SaveButton").property("visible") and item("SaveButton").property("enabled")
    assert position("SaveButton") == edit_position
    wait_for(qt_app, lambda: position("CancelButton") == add_position)
    preview("connection-actions-edit-changed.png")
    item("NameField").setProperty("text", "Tile layout profile")
    qt_app.processEvents()
    assert not item("SaveButton").property("visible")
    wait_for(qt_app, cancel_is_centered)
    click("CancelButton")
    assert not manager.editing and manager.editor["name"] == "Tile layout profile"

    click("AddButton")
    for name, text in (
        ("NameField", "Second profile"),
        ("TenantField", TENANT),
        ("ClientField", CLIENT),
    ):
        item(name).setProperty("text", text)
    qt_app.processEvents()
    click("SaveButton")
    assert len(manager.profiles) == 2
    preview("connection-actions-saved.png")
    panel.setProperty("helpTopic", "auth")
    wait_for(qt_app, lambda: panel.property("helpProgress") > 0.999)
    qt_app.processEvents()
    for name in icons:
        button = item(name)
        assert button.width() >= 80
        label = button.findChild(QObject, "manager" + name + "TransitionLabel")
        assert not label.property("truncated")
        artwork = button.findChild(QObject, "connectionCompatibleSvgImage")
        assert artwork.property("visible")
        assert QQmlExpression(engine.rootContext(), artwork, "status === 1").evaluate()[0]
    preview("connection-actions-help.png")
    assert_close_centered(panel.findChild(QQuickItem, "managerHelpCloseButton"))
    panel.setProperty("helpTopic", "")
    wait_for(qt_app, lambda: panel.property("helpProgress") < 0.001)
    click("ChangeAvatar")
    qt_app.processEvents()
    assert_close_centered(window.findChild(QQuickItem, "avatarPickerClose"))
    QMetaObject.invokeMethod(window.findChild(QObject, "avatarPickerClose"), "clicked")
    picker = window.findChild(QObject, "managerAvatarPicker")
    wait_for(qt_app, lambda: not picker.property("visible"))
    click("UseButton")
    click("UseDialogConfirmButton")
    assert controller.currentProfileId == manager.selectedId
    assert item("UseButton").property("text") == "Active"
    active_icon = item("UseButton").property("iconSource").toString()
    assert active_icon.endswith(
        "/actions/Multicolor-Filled-Mint-Green-Transparent-circle-check.svg"
    )
    assert not item("UseButton").property("enabled")
    manager._busy = True
    manager.testChanged.emit()
    qt_app.processEvents()
    for name in icons:
        assert not item(name).property("enabled")
    manager._busy = False
    manager.testChanged.emit()
    qt_app.processEvents()
    click("RemoveButton")
    click("RemoveDialogConfirmButton")
    assert len(manager.profiles) == 1
    assert item("AddButton").property("visible") and item("AddButton").property("enabled")
    assert not warnings, "\n".join(warnings)
    window.setProperty("closingAllowed", True)
    window.close()
    engine.deleteLater()
    qt_app.processEvents()
    resources.close()


def test_cancel_palette_preserves_raised_and_pressed_states(qt_app):
    from PySide6.QtCore import QObject, QUrl
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

    from azauthlib.gui.config_app import PackageResources

    resources = PackageResources()
    engine = QQmlApplicationEngine()
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str(resources.path("gui", "qml", "components", "ConnectionButton.qml"))),
    )
    button = component.createWithInitialProperties(
        {"variant": "cancel", "text": "Cancel", "objectName": "cancelPaletteProbe"}
    )
    assert button is not None, "\n".join(error.toString() for error in component.errors())
    surface = button.findChild(QObject, "cancelPaletteProbeSurface")
    assert surface.property("middleColor").name() == "#6b7280"
    assert button.property("textColor").name() == "#ffffff"
    assert not surface.property("sunken")
    button.setProperty("down", True)
    assert surface.property("sunken")
    assert surface.property("middleColor").name() != "#6b7280"
    button.setProperty("down", False)
    assert surface.property("middleColor").name() == "#6b7280"
    assert not surface.property("sunken")
    button.deleteLater()
    engine.deleteLater()
    qt_app.processEvents()
    resources.close()


def test_gui_loads_certificate_controls_and_switches_format(bundle, qt_app):
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
    window.show()  # Layout/collapse assertions require an exposed offscreen window.
    for object_name in (
        "managerCancelButton",
        "managerCancelTestButton",
        "certificateCreationCancel",
        "avatarPickerCancel",
        "managerDiscardDialogCancelButton",
        "managerRemoveDialogCancelButton",
        "managerUseDialogCancelButton",
        "connectionsLeaveTestDialogCancelButton",
    ):
        button = window.findChild(QObject, object_name)
        assert button is not None, object_name
        assert button.property("variant") == "cancel", object_name
    manager.beginAdd()
    qt_app.processEvents()
    selector = window.findChild(QObject, "managerMethodSelector")
    assert selector is not None
    add_button = window.findChild(QObject, "managerAddButton")
    actions = window.findChild(QObject, "managerSidebarActions")
    profile_viewport = window.findChild(QObject, "managerProfilesViewport")
    assert actions.property("y") + actions.property("height") < profile_viewport.property("y")
    assert add_button.property("tileLayout")
    assert not add_button.property("visible")
    assert window.findChild(QObject, "managerCancelButton").property("visible")
    assert window.findChild(QObject, "managerSaveButton").property("visible")
    assert window.findChild(QObject, "managerEmptyAddButton") is None
    assert window.findChild(QObject, "managerDetailActions") is None
    avatar_button = window.findChild(QObject, "managerChangeAvatar")
    assert avatar_button.property("visible") and avatar_button.property("enabled")
    QMetaObject.invokeMethod(avatar_button, "clicked")
    qt_app.processEvents()
    picker = window.findChild(QObject, "managerAvatarPicker")
    assert picker.property("visible")
    picker.setProperty("pendingAvatar", manager.avatarChoices[1])
    QMetaObject.invokeMethod(window.findChild(QObject, "avatarPickerApply"), "clicked")
    wait_for(qt_app, lambda: not picker.property("visible"))
    assert manager.avatar == manager.avatarChoices[1]
    assert manager.setAvatar("")
    selector.setProperty("currentIndex", 3)
    qt_app.processEvents()
    editor = window.findChild(QObject, "managerCertificateEditor")
    assert editor is not None and editor.property("visible")
    assert window.findChild(QObject, "managerCertificateKeyField") is not None
    assert window.findChild(QObject, "managerCertificatePublicField") is not None
    panel = window.findChild(QObject, "connectionsHomeContent")

    def check_drawer(button_name, topic, title):
        button = window.findChild(QObject, button_name)
        assert button is not None and button.property("enabled")
        QMetaObject.invokeMethod(button, "clicked")
        qt_app.processEvents()
        assert panel.property("helpTopic") == topic
        assert panel.findChild(QObject, "managerHelpTitle").property("text") == title
        assert button.property("expanded") and not button.property("enabled")
        # Certificate help uses the shared shelf, never a field-level popup.
        assert window.findChild(QObject, "managerCertificatePasswordFieldInfoPopup") is None
        QMetaObject.invokeMethod(panel.findChild(QObject, "managerHelpCloseButton"), "clicked")
        qt_app.processEvents()
        assert panel.property("helpTopic") == ""

    check_drawer("managerCertificateFormatInfoButton", "certificateFormat", "Certificate format")
    check_drawer("managerCertificateKeyFieldInfoButton", "certificateFile", "Certificate file")
    check_drawer(
        "managerCertificatePasswordFieldInfoButton", "certificatePassword", "Private-key password"
    )
    for object_name, value in (
        ("managerNameField", "Certificate preview"),
        ("managerTenantField", TENANT),
        ("managerClientField", CLIENT),
        ("managerCertificateKeyField", bundle["pfx"]["key_path"]),
        ("managerCertificatePasswordField", PASSWORD),
    ):
        window.findChild(QObject, object_name).setProperty("text", value)
    window.findChild(QObject, "managerRememberCertificatePassword").setProperty("checked", True)
    QMetaObject.invokeMethod(editor, "validate")
    wait_for(qt_app, lambda: manager.certificateImport.state.get("valid"))
    save_button = window.findChild(QObject, "managerSaveButton")
    assert save_button.property("enabled")
    card = window.findChild(QObject, "managerCertificateSummary")
    assert card.property("visible")
    assert card.property("commonName") == "CN=Isolated fixture"
    assert card.property("fingerprint") == manager.certificateImport.state["fingerprint"]
    assert card.property("borderColor").name() == "#32bada"
    canvas = window.findChild(QObject, "connectionsZoomCanvas")
    assert card.property("contentScale") == pytest.approx(canvas.property("scale"))
    assert not window.findChild(QObject, "managerDetailsViewport").property("pixelAligned")
    for name in (
        "certificateDetailsDivider_Common name (CN)",
        "certificateDetailsDivider_Expires",
        "certificateDetailsDivider_SHA-256 fingerprint",
        "certificateDetailsFooterDivider",
    ):
        divider = window.findChild(QObject, name)
        assert divider.property("contentScale") == pytest.approx(card.property("contentScale"))
        assert divider.property("implicitHeight") == 1
    assert not window.findChild(QObject, "managerCertificateValidation").property("visible")
    assert not window.findChild(QObject, "managerFieldGuidance").property("visible")
    profile_icon = window.findChild(QObject, "managerCertificateDetailsProfileIcon")
    svg_icon = window.findChild(QObject, "managerCertificateDetailsSvgIcon")
    assert profile_icon is not None and svg_icon is not None
    assert profile_icon.property("avatarId") == "app-service-certificates.svg"
    assert profile_icon.property("visible") and not svg_icon.property("visible")
    card.setProperty("useProfileAvatar", False)
    qt_app.processEvents()
    assert not profile_icon.property("visible") and svg_icon.property("visible")
    assert (
        svg_icon.property("sourceOverride")
        .toString()
        .endswith("/technology/Monocolor-Filled-White-Certificate-Diploma-Degree.svg")
    )
    card.setProperty("useProfileAvatar", True)
    qt_app.processEvents()
    assert profile_icon.property("visible") and not svg_icon.property("visible")
    expiry = datetime.fromisoformat(manager.certificateImport.state["not_after"]).timestamp() * 1000
    for now, expected in (
        (expiry - 90 * 86400000, "in 90 days"),
        (expiry - 1000, "in 1 day"),
        (expiry, "Expired"),
    ):
        card.setProperty("nowMilliseconds", now)
        assert card.property("expirationStatus") == expected
    assert card.property("expired")
    assert card.property("expirationColor").name() == "#ff889e"
    card.setProperty("nowMilliseconds", time.time() * 1000)
    wait_for(qt_app, lambda: card.property("width") > 0)
    qt_app.processEvents()
    expanded_height = card.property("height")
    toggle = window.findChild(QObject, "managerCertificateDetailsToggle")
    QMetaObject.invokeMethod(toggle, "clicked")
    wait_for(qt_app, lambda: card.property("revealProgress") == 0)
    qt_app.processEvents()
    assert card.property("height") < expanded_height
    assert not window.findChild(QObject, "managerCertificateDetailsBody").property("visible")
    QMetaObject.invokeMethod(toggle, "clicked")
    wait_for(qt_app, lambda: card.property("revealProgress") == 1)
    check_drawer("managerCertificateDetailsInfoButton", "certificateDetails", "Certificate details")
    preview_dir = os.environ.get("AZAUTHLIB_CERTIFICATE_PREVIEW_DIR")
    if preview_dir:
        qt_app.processEvents()
        window.grabWindow().save(str(Path(preview_dir) / "certificate-pfx.png"))
    assert manager.saveConnection("Certificate preview", TENANT, CLIENT, "", "client_certificate")
    manager.beginEdit()
    wait_for(qt_app, lambda: manager.certificateImport.state.get("valid"))
    assert avatar_button.property("visible") and avatar_button.property("enabled")
    assert manager.setAvatar(manager.avatarChoices[1])
    qt_app.processEvents()
    assert save_button.property("visible") and save_button.property("enabled")
    assert window.findChild(QObject, "managerNameField").property("text") == "Certificate preview"
    assert manager.setAvatar("")
    qt_app.processEvents()
    assert not save_button.property("visible")
    window.findChild(QObject, "managerCertificatePasswordField").setProperty("text", PASSWORD)
    QMetaObject.invokeMethod(editor, "validate")
    wait_for(qt_app, lambda: manager.certificateImport.state.get("valid"))
    assert not save_button.property("visible")
    window.findChild(QObject, "managerCertificateFormat").setProperty("currentIndex", 1)
    qt_app.processEvents()
    check_drawer("managerCertificateKeyFieldInfoButton", "privateKeyFile", "Private key file")
    check_drawer(
        "managerCertificatePublicFieldInfoButton", "publicCertificate", "Public certificate"
    )
    window.findChild(QObject, "managerCertificateKeyField").setProperty(
        "text", bundle["pem"]["key_path"]
    )
    window.findChild(QObject, "managerCertificatePublicField").setProperty(
        "text", bundle["pem"]["certificate_path"]
    )
    QMetaObject.invokeMethod(editor, "validate")
    wait_for(qt_app, lambda: manager.certificateImport.state.get("valid"))
    assert save_button.property("visible") and save_button.property("enabled")
    if preview_dir:
        qt_app.processEvents()
        window.grabWindow().save(str(Path(preview_dir) / "certificate-pem.png"))
    manager.cancelEdit()
    qt_app.processEvents()
    assert card.property("visible") and not save_button.property("visible")
    for label in ("Common name (CN)", "Expires", "SHA-256 fingerprint"):
        value = window.findChild(QObject, "certificateDetailValue_" + label)
        assert value.property("readOnly") and value.property("selectByMouse")
        assert value.property("width") > 0 and value.property("height") > 0
    if preview_dir:
        viewport = window.findChild(QObject, "managerDetailsViewport")
        viewport.setProperty(
            "contentY", max(0, viewport.property("contentHeight") - viewport.property("height"))
        )
        qt_app.processEvents()
        window.grabWindow().save(str(Path(preview_dir) / "certificate-details-card.png"))
    # Testing must dismiss contextual help and disable all certificate info controls.
    for button_name in ("managerEditButton", "managerTestButton"):
        button = window.findChild(QObject, button_name)
        surface = window.findChild(QObject, button_name + "Surface")
        assert not surface.property("sunken") and not surface.property("recessedFill")
        button.setProperty("down", True)
        assert surface.property("sunken") and surface.property("recessedFill")
        button.setProperty("down", False)
        assert not surface.property("sunken") and not surface.property("recessedFill")
    check_drawer("managerCertificateFormatInfoButton", "certificateFormat", "Certificate format")
    QMetaObject.invokeMethod(
        window.findChild(QObject, "managerCertificateKeyFieldInfoButton"), "clicked"
    )
    manager._busy = True
    manager.testChanged.emit()
    qt_app.processEvents()
    assert not avatar_button.property("enabled")
    assert panel.property("helpTopic") == ""
    assert not window.findChild(QObject, "managerCertificateFormatInfoButton").property("enabled")
    assert not window.findChild(QObject, "managerCertificateKeyFieldInfoButton").property("enabled")
    assert not window.findChild(QObject, "managerCertificateDetailsInfoButton").property("enabled")
    assert not toggle.property("enabled")
    manager._busy = False
    manager.testChanged.emit()
    assert not warnings, "\n".join(warnings)
    window.setProperty("closingAllowed", True)
    window.close()
    engine.deleteLater()
    qt_app.processEvents()
    resources.close()
