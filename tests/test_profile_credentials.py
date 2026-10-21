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

"""Regression tests for saved authentication methods and credential loading."""

import pytest

from azauthlib import Authentication, credentials, profiles


@pytest.mark.parametrize("method", ["interactive", "device_code", "client_credentials"])
def test_default_builder_accepts_real_saved_configuration(method):
    profile = profiles.create_profile("Saved")
    credentials.save_configuration(
        profile=profile,
        client_id="saved-client",
        tenant_id="saved-tenant",
        client_secret="saved-secret",
        authority="https://login.microsoftonline.com/saved-tenant",
        auth_method=method,
    )
    auth = Authentication(profile=profile)
    assert auth.Build.Default() is auth
    assert auth.client_id == "saved-client"
    assert auth.tenant_id == "saved-tenant"
    assert auth.client_secret == "saved-secret"
    assert auth.authority == "https://login.microsoftonline.com/saved-tenant"
    assert credentials.load_public_configuration(profile=profile)["auth_method"] == method
    assert auth.Build.Default(authority="https://authority.example").authority.endswith(".example")


def test_public_configuration_does_not_read_keyring(monkeypatch):
    def forbidden(*_):
        pytest.fail("Public configuration must not read secrets")

    monkeypatch.setattr(credentials.keyring, "get_password", forbidden)
    assert credentials.load_public_configuration()["auth_method"] == "interactive"


def test_invalid_saved_authentication_method_falls_back():
    path = profiles.profile_config_path()
    path.parent.mkdir()
    path.write_text("AUTH_METHOD=unsupported\n", encoding="utf-8")
    assert credentials.load_public_configuration()["auth_method"] == "interactive"


def test_explicit_file_and_profile_cannot_be_combined(tmp_path):
    with pytest.raises(ValueError, match="cannot be used together"):
        credentials.load_credentials(tmp_path / ".env", profile="Default")
    with pytest.raises(ValueError, match="cannot be used together"):
        credentials.save_configuration(
            path=tmp_path / ".env", profile="Default", client_id="client", tenant_id="tenant"
        )


def test_invalid_authentication_method_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="unsupported"):
        credentials.save_configuration(
            path=tmp_path / ".env", client_id="client", tenant_id="tenant", auth_method="invalid"
        )


def test_has_stored_secret_and_backend_failure(monkeypatch):
    assert not credentials.has_stored_secret(None)
    assert not credentials.has_stored_secret("client")
    credentials.keyring.set_password("azauthlib", "client", "test-secret")
    assert credentials.has_stored_secret("client")

    def fail(*_):
        raise RuntimeError("Keyring unavailable")

    monkeypatch.setattr(credentials.keyring, "get_password", fail)
    with pytest.raises(credentials.CredentialStoreError, match="OS keyring"):
        credentials.has_stored_secret("client")


def test_failed_configuration_replace_preserves_original_and_removes_temporary(monkeypatch):
    target = credentials.save_configuration(client_id="original", tenant_id="tenant")
    original = target.read_bytes()

    def fail(*_):
        raise OSError("Cannot replace configuration")

    monkeypatch.setattr(credentials.os, "replace", fail)
    with pytest.raises(OSError, match="Cannot replace"):
        credentials.save_configuration(client_id="replacement", tenant_id="tenant")
    assert target.read_bytes() == original
    assert list(target.parent.iterdir()) == [target]
