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

"""Exact-path configuration loading and OS-backed secret storage."""

from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from pathlib import Path

import keyring
from dotenv import dotenv_values

from ._configure import get_settings
from .appdata import ensure_private_directory

KEYRING_SERVICE = "azauthlib"
AUTH_METHODS = frozenset({"interactive", "device_code", "client_credentials"})


class CredentialStoreError(RuntimeError):
    """Raised when credentials cannot be stored securely."""


def _public_config_value(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in normalized):
        raise ValueError(f"{name} contains invalid control characters")
    return normalized


def load_credentials(path=None, *, profile=None) -> dict[str, str | None]:
    """Load credentials from one exact file, environment, and the OS keyring."""
    if path is not None and profile is not None:
        raise ValueError("path and profile cannot be used together")
    selected = Path(path or get_settings(profile).env_path).expanduser().resolve()
    file_values = dotenv_values(selected) if selected.is_file() else {}
    client_id = os.getenv("CLIENT_ID") or file_values.get("CLIENT_ID")
    tenant_id = os.getenv("TENANT_ID") or file_values.get("TENANT_ID")
    secret = os.getenv("CLIENT_SECRET")
    if secret is None and client_id:
        try:
            secret = keyring.get_password(KEYRING_SERVICE, client_id)
        except Exception as exc:
            raise CredentialStoreError(
                "Unable to read the client secret from the OS keyring"
            ) from exc
    return {
        "client_id": client_id,
        "tenant_id": tenant_id,
        "client_secret": secret,
        "authority": os.getenv("AZURE_AUTHORITY") or file_values.get("AZURE_AUTHORITY"),
        "auth_method": file_values.get("AUTH_METHOD") or "interactive",
    }


def load_public_configuration(*, profile=None) -> dict[str, str | None]:
    """Load non-secret values for a profile without accessing the OS keyring."""

    selected = get_settings(profile).env_path.expanduser().resolve()
    file_values = dotenv_values(selected) if selected.is_file() else {}
    auth_method = file_values.get("AUTH_METHOD") or "interactive"
    if auth_method not in AUTH_METHODS:
        auth_method = "interactive"
    return {
        "client_id": file_values.get("CLIENT_ID"),
        "tenant_id": file_values.get("TENANT_ID"),
        "authority": file_values.get("AZURE_AUTHORITY"),
        "auth_method": auth_method,
    }


def has_stored_secret(client_id: str | None) -> bool:
    """Return whether the OS credential manager contains a secret for a client ID."""

    if not client_id:
        return False
    try:
        return keyring.get_password(KEYRING_SERVICE, client_id) is not None
    except Exception as exc:
        raise CredentialStoreError("Unable to read the client secret from the OS keyring") from exc


def save_configuration(
    *,
    client_id: str,
    tenant_id: str,
    client_secret: str | None = None,
    authority: str | None = None,
    path=None,
    profile=None,
    auth_method: str | None = None,
) -> Path:
    """Write non-secret configuration and store the secret in the OS keyring."""
    client_id = _public_config_value("client_id", client_id)
    tenant_id = _public_config_value("tenant_id", tenant_id)
    if authority is not None:
        authority = _public_config_value("authority", authority)
    if path is not None and profile is not None:
        raise ValueError("path and profile cannot be used together")
    if auth_method is not None and auth_method not in AUTH_METHODS:
        raise ValueError("auth_method is unsupported")
    target = Path(path or get_settings(profile).env_path).expanduser().resolve()
    ensure_private_directory(target.parent)
    if client_secret:
        try:
            keyring.set_password(KEYRING_SERVICE, client_id, client_secret)
        except Exception as exc:
            raise CredentialStoreError(
                "Unable to store the client secret in the OS keyring"
            ) from exc
    lines = [
        "# azauthlib public application configuration",
        f"CLIENT_ID={client_id}",
        f"TENANT_ID={tenant_id}",
    ]
    if authority:
        lines.append(f"AZURE_AUTHORITY={authority}")
    if auth_method:
        lines.append(f"AUTH_METHOD={auth_method}")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent, text=True)
    try:
        if os.name != "nt":
            os.chmod(temporary_name, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(lines) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, target)
    except Exception:
        with suppress(FileNotFoundError):
            os.unlink(temporary_name)
        raise
    return target


__all__ = [
    "AUTH_METHODS",
    "CredentialStoreError",
    "has_stored_secret",
    "load_credentials",
    "load_public_configuration",
    "save_configuration",
]
