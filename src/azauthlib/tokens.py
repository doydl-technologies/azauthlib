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

"""Secure MSAL token-cache persistence and token time helpers."""

from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path
from typing import Any

from msal import SerializableTokenCache
from msal_extensions import FilePersistence, PersistedTokenCache, build_encrypted_persistence

from .appdata import ensure_private_directory


class TokenCacheSecurityError(RuntimeError):
    """Raised when encrypted cache persistence is unavailable."""


def resolve_token_path(path: str | os.PathLike[str] | None, *, default=None) -> str | None:
    """Resolve a cache filename without selecting arbitrary files from a directory."""
    selected = path if path is not None else default
    if selected is None:
        return None
    raw = os.fspath(selected)
    candidate = Path(raw).expanduser()
    if candidate.exists() and candidate.is_dir() or raw.endswith((os.sep, "/")):
        candidate = candidate / "msal-cache.bin"
    return str(candidate.resolve())


def load_token_cache(token_path, *, allow_plaintext: bool = False) -> PersistedTokenCache:
    """Create an encrypted, locked persistent cache.

    Plaintext fallback is disabled unless the caller explicitly opts in.
    """
    resolved = resolve_token_path(token_path)
    if not resolved:
        raise ValueError("A token cache path is required")
    cache_path = Path(resolved)
    ensure_private_directory(cache_path.parent)
    try:
        persistence = build_encrypted_persistence(str(cache_path))
    except Exception as exc:
        if not allow_plaintext:
            raise TokenCacheSecurityError(
                "Encrypted token persistence is unavailable. Configure an OS credential "
                "store or explicitly opt in to plaintext cache persistence."
            ) from exc
        persistence = FilePersistence(str(cache_path))
    return PersistedTokenCache(persistence)


def save_token_cache(cache: Any, cache_path=None) -> None:
    """Compatibility helper; secure persisted caches save themselves."""
    del cache_path
    if isinstance(cache, PersistedTokenCache):
        return
    if isinstance(cache, SerializableTokenCache):
        raise TokenCacheSecurityError(
            "Refusing to persist an unencrypted SerializableTokenCache; use load_token_cache()"
        )
    raise TypeError("cache must be an MSAL token cache")


def is_valid_JWT(token: str) -> bool:
    """Return whether *token* has the three base64url segments of a JWT."""
    return isinstance(token, str) and bool(
        re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token)
    )


def tokentime_fmt(timestamp, start_timestamp=None) -> str | None:
    """Format an epoch timestamp or a duration relative to ``start_timestamp``."""
    if timestamp is None or timestamp == "Expired":
        return None
    if not isinstance(timestamp, (int, float)):
        return None
    if start_timestamp is not None:
        value = dt.datetime.fromtimestamp(start_timestamp, tz=dt.timezone.utc) + dt.timedelta(
            seconds=timestamp
        )
    else:
        value = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
    return value.isoformat()


__all__ = [
    "TokenCacheSecurityError",
    "is_valid_JWT",
    "load_token_cache",
    "resolve_token_path",
    "save_token_cache",
    "tokentime_fmt",
]
