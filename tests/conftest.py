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

"""Isolate tests from user configuration, credential stores, and the network."""

import socket

import pytest

from azauthlib import appdata, credentials


@pytest.fixture(autouse=True)
def isolated_user_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(appdata, "user_config_path", lambda *_, **__: tmp_path / "config")
    monkeypatch.setattr(appdata, "user_cache_path", lambda *_, **__: tmp_path / "cache")
    for name in ("CLIENT_ID", "TENANT_ID", "CLIENT_SECRET", "AZURE_AUTHORITY"):
        monkeypatch.delenv(name, raising=False)
    secrets = {}
    monkeypatch.setattr(
        credentials.keyring, "get_password", lambda service, client: secrets.get((service, client))
    )
    monkeypatch.setattr(
        credentials.keyring,
        "set_password",
        lambda service, client, value: secrets.update({(service, client): value}),
    )
    monkeypatch.setattr(
        credentials.keyring,
        "delete_password",
        lambda service, client: secrets.pop((service, client)),
    )

    def no_network(*_args, **_kwargs):
        pytest.fail("Unit tests must not contact external services")

    monkeypatch.setattr(socket, "create_connection", no_network)
