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

"""Tests for profile isolation, validation, and recoverable removal."""

import json
from pathlib import Path

import pytest

from azauthlib import Authentication, credentials, profiles
from azauthlib._configure import get_settings


def test_default_profile_is_lazy():
    assert profiles.list_profiles() == (profiles.Profile("default", "Default"),)
    assert profiles.active_profile().id == "default"
    assert not profiles.get_config_dir().exists()
    assert not profiles.get_cache_dir().exists()


def test_create_select_resolve_and_rename():
    first = profiles.create_profile("Accounting")
    other = profiles.create_profile("Reports", select=False)
    assert profiles.active_profile() == first
    assert profiles.resolve_profile("ACCOUNTING") == first
    assert profiles.resolve_profile(first.id) == first
    assert profiles.resolve_profile(first) == first
    assert profiles.select_profile(other) == other
    assert profiles.select_profile(other) == other
    before = get_settings(other)
    renamed = profiles.rename_profile(other, "Reporting")
    assert profiles.rename_profile(renamed, "Reporting") == renamed
    assert get_settings(renamed) == before
    assert profiles.active_profile() == renamed
    with pytest.raises(ValueError, match="Unknown"):
        profiles.resolve_profile("Reports")


@pytest.mark.parametrize("name", ["", " ", "x" * 65, "bad\nname", "bad\x7fname", None])
def test_invalid_names_are_rejected(name):
    with pytest.raises((TypeError, ValueError)):
        profiles.create_profile(name)


def test_duplicate_names_and_unknown_profiles():
    first = profiles.create_profile("Accounting")
    other = profiles.create_profile("Reports")
    with pytest.raises(ValueError, match="already exists"):
        profiles.create_profile("ACCOUNTING")
    with pytest.raises(ValueError, match="already exists"):
        profiles.rename_profile(other, first.name)
    with pytest.raises(ValueError, match="Unknown"):
        profiles.select_profile("missing")
    with pytest.raises(TypeError, match="profile must"):
        profiles.resolve_profile(12)


def test_profile_settings_are_isolated_and_explicit_selection_is_stable():
    first = profiles.create_profile("First")
    credentials.save_configuration(
        profile=first, client_id="first-client", tenant_id="tenant", auth_method="device_code"
    )
    original = Authentication(profile=first)
    second = profiles.create_profile("Second")
    credentials.save_configuration(profile=second, client_id="second-client", tenant_id="tenant")
    assert get_settings(first) != get_settings(second)
    assert get_settings(first).token_path != get_settings(second).token_path
    assert Authentication().Build.Default().client_id == "second-client"
    assert original.Build.Default().client_id == "first-client"
    assert Authentication(profile="First").Build.Default().client_id == "first-client"


def test_default_profile_uses_root_paths():
    settings = get_settings("Default")
    assert settings.env_path == profiles.get_config_dir() / ".env"
    assert settings.token_path == profiles.get_cache_dir() / "msal-cache.bin"


def test_remove_archives_only_known_files_and_preserves_shared_secrets(monkeypatch):
    selected = profiles.create_profile("Removed")
    credentials.save_configuration(
        profile=selected, client_id="client", tenant_id="tenant", client_secret="test-secret"
    )
    settings = get_settings(selected)
    settings.token_path.parent.mkdir(parents=True)
    settings.token_path.write_bytes(b"opaque encrypted cache")
    lock = Path(str(settings.token_path) + ".lockfile")
    lock.write_bytes(b"lock")
    unrelated = settings.token_path.parent / "unrelated.txt"
    unrelated.write_text("keep", encoding="utf-8")
    monkeypatch.setattr(
        credentials.keyring, "delete_password", lambda *_: pytest.fail("Shared secret deleted")
    )
    profiles.remove_profile(selected)
    assert profiles.active_profile().id == "default"
    assert unrelated.read_text(encoding="utf-8") == "keep"
    assert credentials.keyring.get_password("azauthlib", "client") == "test-secret"
    assert not settings.env_path.exists()
    assert not settings.token_path.exists()
    assert not lock.exists()
    assert len(list(profiles.get_config_dir().glob("removed-profiles/*/.env"))) == 1
    assert len(list(profiles.get_cache_dir().glob("removed-profiles/*/msal-cache.bin"))) == 1


def test_remove_all_profiles_keeps_registry_empty():
    profiles.remove_profile("Default")
    assert profiles.list_profiles() == ()
    with pytest.raises(ValueError, match="No connections"):
        profiles.active_profile()
    with pytest.raises(ValueError, match="No connections"):
        Authentication()
    first = profiles.create_profile("First", select=False)
    assert profiles.active_profile() == first
    profiles.remove_profile(first)
    assert profiles.list_profiles() == ()


def test_remove_rolls_back_files_if_registry_write_fails(monkeypatch):
    selected = profiles.create_profile("Retained")
    credentials.save_configuration(profile=selected, client_id="client", tenant_id="tenant")
    path = get_settings(selected).env_path
    before = path.read_bytes()

    def fail(_registry):
        raise OSError("Registry unavailable")

    monkeypatch.setattr(profiles, "_write_registry", fail)
    with pytest.raises(OSError, match="Registry unavailable"):
        profiles.remove_profile(selected)
    assert path.read_bytes() == before
    assert profiles.resolve_profile(selected) == selected


@pytest.mark.parametrize(
    "registry",
    [
        [],
        {"version": 2},
        {"version": 1, "profiles": None},
        {"version": 1, "profiles": [None]},
        {"version": 1, "profiles": [{"id": "../escape", "name": "Escape"}]},
        {"version": 1, "profiles": [{"id": "one", "name": ""}]},
        {"version": 1, "profiles": [], "active": "missing"},
        {"version": 1, "profiles": []},
        {"version": 1, "profiles": [{"id": "one", "name": "One"}], "active": "missing"},
        {
            "version": 1,
            "profiles": [{"id": "one", "name": "One"}, {"id": "one", "name": "Two"}],
            "active": "one",
        },
        {
            "version": 1,
            "profiles": [{"id": "one", "name": "One"}, {"id": "two", "name": "ONE"}],
            "active": "one",
        },
    ],
)
def test_invalid_registry_is_not_silently_replaced(registry):
    path = profiles.get_config_dir() / "profiles.json"
    path.parent.mkdir()
    content = json.dumps(registry)
    path.write_text(content, encoding="utf-8")
    with pytest.raises(profiles.ProfileStoreError):
        profiles.list_profiles()
    assert path.read_text(encoding="utf-8") == content


def test_malformed_json_is_actionable():
    path = profiles.get_config_dir() / "profiles.json"
    path.parent.mkdir()
    path.write_text("{", encoding="utf-8")
    with pytest.raises(profiles.ProfileStoreError, match="Unable to read"):
        profiles.list_profiles()


def test_registry_write_failure_does_not_leave_temporary_files(monkeypatch):
    def fail(*_):
        raise OSError("Cannot replace registry")

    monkeypatch.setattr(profiles.os, "replace", fail)
    with pytest.raises(OSError, match="Cannot replace"):
        profiles.create_profile("Unsaved")
    assert not list(profiles.get_config_dir().iterdir())
