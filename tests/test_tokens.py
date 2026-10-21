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

"""Tests for secure token persistence and token utilities."""

import pytest
from msal import SerializableTokenCache

from azauthlib import tokens


def test_resolve_directory_uses_deterministic_filename(tmp_path):
    (tmp_path / "unrelated.json").write_text("{}", encoding="utf-8")
    assert tokens.resolve_token_path(tmp_path) == str((tmp_path / "msal-cache.bin").resolve())


def test_resolve_new_file_path_keeps_requested_name(tmp_path):
    requested = tmp_path / "new" / "custom.cache"
    assert tokens.resolve_token_path(requested) == str(requested.resolve())


def test_encryption_failure_is_closed_by_default(monkeypatch, tmp_path):
    def unavailable(_):
        raise RuntimeError("no backend")

    monkeypatch.setattr(tokens, "build_encrypted_persistence", unavailable)
    with pytest.raises(tokens.TokenCacheSecurityError, match="Encrypted token persistence"):
        tokens.load_token_cache(tmp_path / "cache.bin")


def test_plaintext_requires_explicit_opt_in(monkeypatch, tmp_path):
    monkeypatch.setattr(
        tokens, "build_encrypted_persistence", lambda _: (_ for _ in ()).throw(RuntimeError())
    )
    cache = tokens.load_token_cache(tmp_path / "cache.bin", allow_plaintext=True)
    assert cache is not None


def test_unencrypted_serializable_cache_is_not_written(tmp_path):
    with pytest.raises(tokens.TokenCacheSecurityError, match="Refusing"):
        tokens.save_token_cache(SerializableTokenCache(), tmp_path / "cache.json")


def test_jwt_shape_validation():
    assert tokens.is_valid_JWT("aaa.bbb.ccc")
    assert not tokens.is_valid_JWT("not-a-jwt")


def test_token_time_is_utc_isoformat():
    assert tokens.tokentime_fmt(0) == "1970-01-01T00:00:00+00:00"
    assert tokens.tokentime_fmt(60, start_timestamp=0) == "1970-01-01T00:01:00+00:00"
    assert tokens.tokentime_fmt(None) is None
    assert tokens.tokentime_fmt("invalid") is None


def test_cache_and_path_type_validation():
    assert tokens.resolve_token_path(None) is None
    with pytest.raises(ValueError, match="required"):
        tokens.load_token_cache(None)
    with pytest.raises(TypeError, match="MSAL token cache"):
        tokens.save_token_cache(object())
