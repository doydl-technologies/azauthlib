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

"""Tests for application-data paths and filesystem safety helpers."""

from pathlib import Path

import pytest

from azauthlib import appdata


def test_import_helpers_do_not_create_directories(monkeypatch, tmp_path):
    expected = tmp_path / "config"
    monkeypatch.setattr(appdata, "user_config_path", lambda *_, **__: expected)
    assert appdata.get_config_dir(create=False) == expected
    assert not expected.exists()


def test_omit_cannot_escape_application_root(monkeypatch, tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr(appdata, "get_config_dir", lambda **_: root)
    manager = appdata.UserDataDirectory("owned")
    with pytest.raises(ValueError, match="outside"):
        manager.Omit(outside)


def test_recursive_cleanup_is_disabled(monkeypatch, tmp_path):
    monkeypatch.setattr(appdata, "get_config_dir", lambda **_: tmp_path)
    manager = appdata.UserDataDirectory("owned")
    with pytest.raises(RuntimeError, match="removed for safety"):
        manager.Clean()


def test_directory_creation_and_compatibility_file_helpers(monkeypatch, tmp_path):
    config = tmp_path / "config"
    cache = tmp_path / "cache"
    monkeypatch.setattr(appdata, "user_config_path", lambda *_, **__: config)
    monkeypatch.setattr(appdata, "user_cache_path", lambda *_, **__: cache)
    assert appdata.get_config_dir(create=True).is_dir()
    assert appdata.get_cache_dir(create=True).is_dir()
    assert appdata.find_default_user_data_dir() == str(config)

    manager = appdata.UserDataDirectory("owned")
    directory = Path(manager.Dir())
    assert manager.Exists(exists_only=True)
    created = Path(manager.DirFile("token", "json"))
    assert created.is_file()
    assert manager.Exists() == str(directory)
    created.unlink()
    manager.Omit(directory)
    assert not directory.exists()


def test_compatibility_wrapper_rejects_unsafe_inputs(monkeypatch, tmp_path):
    monkeypatch.setattr(appdata, "get_config_dir", lambda **_: tmp_path)
    with pytest.raises(ValueError, match="Automatic"):
        appdata.UserDataDirectory("owned", auto_remove=True)
    with pytest.raises(ValueError, match="component"):
        appdata.UserDataDirectory("../escape")
    manager = appdata.UserDataDirectory("owned")
    with pytest.raises(ValueError, match="filename"):
        manager.DirFile("../escape", ".txt")


def test_private_directory_rejects_existing_file(tmp_path):
    existing = tmp_path / "file"
    existing.write_text("data", encoding="utf-8")
    with pytest.raises(FileExistsError):
        appdata.ensure_private_directory(existing)
