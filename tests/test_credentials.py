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

"""Tests for configuration loading and credential storage."""

import pytest

from azauthlib import credentials


def test_configuration_never_writes_secret(monkeypatch, tmp_path):
    stored = {}
    monkeypatch.setattr(
        credentials.keyring,
        "set_password",
        lambda service, username, password: stored.update(
            service=service, username=username, password=password
        ),
    )
    target = credentials.save_configuration(
        client_id="client-id",
        tenant_id="tenant-id",
        client_secret="top-secret",
        path=tmp_path / ".env",
    )
    text = target.read_text(encoding="utf-8")
    assert "CLIENT_ID=client-id" in text
    assert "CLIENT_SECRET" not in text
    assert "top-secret" not in text
    assert stored["password"] == "top-secret"


def test_load_credentials_uses_one_exact_file(monkeypatch, tmp_path):
    target = tmp_path / "chosen.env"
    target.write_text("CLIENT_ID=file-client\nTENANT_ID=file-tenant\n", encoding="utf-8")
    monkeypatch.delenv("CLIENT_ID", raising=False)
    monkeypatch.delenv("TENANT_ID", raising=False)
    monkeypatch.delenv("CLIENT_SECRET", raising=False)
    monkeypatch.setattr(credentials.keyring, "get_password", lambda *_: "keyring-secret")
    result = credentials.load_credentials(target)
    assert result["client_id"] == "file-client"
    assert result["tenant_id"] == "file-tenant"
    assert result["client_secret"] == "keyring-secret"


def test_keyring_failure_is_actionable(monkeypatch, tmp_path):
    def fail(*_):
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(credentials.keyring, "set_password", fail)
    with pytest.raises(credentials.CredentialStoreError, match="OS keyring"):
        credentials.save_configuration(
            client_id="client",
            tenant_id="tenant",
            client_secret="secret",
            path=tmp_path / ".env",
        )


def test_load_keyring_failure_is_actionable(monkeypatch, tmp_path):
    target = tmp_path / ".env"
    target.write_text("CLIENT_ID=client\nTENANT_ID=tenant\n", encoding="utf-8")
    monkeypatch.delenv("CLIENT_SECRET", raising=False)
    monkeypatch.setattr(
        credentials.keyring,
        "get_password",
        lambda *_: (_ for _ in ()).throw(RuntimeError("unavailable")),
    )
    with pytest.raises(credentials.CredentialStoreError, match="OS keyring"):
        credentials.load_credentials(target)


def test_configuration_validation_and_authority(monkeypatch, tmp_path):
    with pytest.raises(ValueError, match="required"):
        credentials.save_configuration(client_id="", tenant_id="tenant", path=tmp_path / ".env")
    monkeypatch.setattr(credentials.keyring, "set_password", lambda *_: None)
    target = credentials.save_configuration(
        client_id="client",
        tenant_id="tenant",
        authority="https://authority.example",
        path=tmp_path / ".env",
    )
    assert "AZURE_AUTHORITY=https://authority.example" in target.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("client_id", "client\nINJECTED=value"),
        ("tenant_id", "tenant\rINJECTED=value"),
        ("authority", "https://example.test\x7fmalformed"),
    ],
)
def test_configuration_rejects_control_characters(tmp_path, field, value):
    values = {
        "client_id": "client",
        "tenant_id": "tenant",
        "authority": "https://example.test",
    }
    values[field] = value
    with pytest.raises(ValueError, match="control"):
        credentials.save_configuration(**values, path=tmp_path / ".env")
