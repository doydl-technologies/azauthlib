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

import base64
import hashlib
import json
import os
import tempfile
import uuid
from contextlib import suppress
from pathlib import Path

import keyring
from dotenv import dotenv_values

from ._configure import get_settings
from .appdata import ensure_private_directory
from .certificates import ImportedCertificate, import_certificate

KEYRING_SERVICE = "azauthlib"
AUTH_METHODS = frozenset({"interactive", "device_code", "client_credentials", "client_certificate"})
CERTIFICATE_SERVICE = KEYRING_SERVICE + ".certificate-passwords"


def _certificate_config(values):
    encoded = values.get("CERTIFICATE_CONFIG")
    if not encoded:
        return None
    try:
        spec = json.loads(base64.b64decode(encoded, validate=True))
        allowed = {
            "format",
            "key_path",
            "certificate_path",
            "fingerprint",
            "subject",
            "not_after",
            "password_ref",
        }
        if (
            not isinstance(spec, dict)
            or set(spec) - allowed
            or not all(isinstance(v, str) for v in spec.values())
        ):
            raise ValueError
        return spec
    except (ValueError, TypeError):
        raise CredentialStoreError("The saved certificate configuration is invalid.") from None


def _certificate_account(target, client_id, tenant_id):
    identity = json.dumps([str(Path(target).resolve()), client_id, tenant_id]).encode("utf-8")
    return "profile:" + hashlib.sha256(identity).hexdigest() + ":"


def certificate_password(spec, *, path=None, profile=None, client_id=None, tenant_id=None):
    """Resolve a password only within this profile/application credential namespace."""
    if not spec or not spec.get("password_ref"):
        return None
    target = Path(path or get_settings(profile).env_path).expanduser().resolve()
    prefix = _certificate_account(target, client_id, tenant_id)
    reference = spec["password_ref"]
    if not reference.startswith(prefix):
        raise CredentialStoreError(
            "Certificate password belongs to a different profile or application."
        )
    try:
        password = keyring.get_password(CERTIFICATE_SERVICE, reference)
    except Exception:
        raise CredentialStoreError(
            "Unable to read the certificate password from secure storage."
        ) from None
    if password is None:
        raise CredentialStoreError(
            "No certificate password was found. Edit and validate the connection again."
        )
    return password


class CredentialStoreError(RuntimeError):
    """Raised when credentials cannot be stored securely."""


def _public_config_value(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in normalized):
        raise ValueError(f"{name} contains invalid control characters")
    return normalized


def load_credentials(path=None, *, profile=None) -> dict[str, str | dict | None]:
    """Load credentials from one exact file, environment, and the OS keyring."""
    if path is not None and profile is not None:
        raise ValueError("path and profile cannot be used together")
    selected = Path(path or get_settings(profile).env_path).expanduser().resolve()
    file_values = dotenv_values(selected) if selected.is_file() else {}
    client_id = os.getenv("CLIENT_ID") or file_values.get("CLIENT_ID")
    tenant_id = os.getenv("TENANT_ID") or file_values.get("TENANT_ID")
    if file_values.get("AUTH_METHOD") == "client_certificate":
        spec = _certificate_config(file_values)
        return {
            "client_id": client_id,
            "tenant_id": tenant_id,
            "client_secret": None,  # nosec B105 # No secret in certificate configurations.
            "authority": os.getenv("AZURE_AUTHORITY") or file_values.get("AZURE_AUTHORITY"),
            "auth_method": "client_certificate",
            "certificate": spec,
            "certificate_password": certificate_password(
                spec,
                path=selected,
                client_id=client_id,
                tenant_id=tenant_id,
            ),
        }
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


def load_public_configuration(*, profile=None) -> dict[str, str | dict | None]:
    """Load non-secret values for a profile without accessing the OS keyring."""

    selected = get_settings(profile).env_path.expanduser().resolve()
    file_values = dotenv_values(selected) if selected.is_file() else {}
    auth_method = file_values.get("AUTH_METHOD") or "interactive"
    if auth_method not in AUTH_METHODS:
        auth_method = "interactive"
    result = {
        "client_id": file_values.get("CLIENT_ID"),
        "tenant_id": file_values.get("TENANT_ID"),
        "authority": file_values.get("AZURE_AUTHORITY"),
        "auth_method": auth_method,
    }
    if auth_method == "client_certificate":
        result["certificate"] = _certificate_config(file_values)
    return result


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
    certificate: dict | ImportedCertificate | None = None,
    certificate_password_value: str | None = None,
    remember_certificate_password: bool = False,
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
    previous_values = dotenv_values(target) if target.is_file() else {}
    previous_certificate = _certificate_config(previous_values)
    new_reference = None
    if auth_method == "client_certificate":
        # GUI imports arrive prevalidated by its worker; API callers use the same validator.
        if isinstance(certificate, ImportedCertificate):
            certificate = certificate.public
        else:
            certificate = import_certificate(certificate, certificate_password_value).public
        if not certificate or certificate.get("format") not in ("pfx", "pem"):
            raise ValueError("A validated PFX/P12 or PEM certificate is required")
        allowed = {"format", "key_path", "certificate_path", "fingerprint", "subject", "not_after"}
        certificate = {k: v for k, v in certificate.items() if k in allowed}
        if not all(isinstance(value, str) for value in certificate.values()):
            raise ValueError("Invalid certificate metadata")
        if remember_certificate_password and certificate_password_value:
            new_reference = _certificate_account(target, client_id, tenant_id) + uuid.uuid4().hex
            try:
                keyring.set_password(CERTIFICATE_SERVICE, new_reference, certificate_password_value)
            except Exception:
                raise CredentialStoreError(
                    "Unable to store the certificate password securely."
                ) from None
            certificate["password_ref"] = new_reference
    if client_secret and auth_method != "client_certificate":
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
    if auth_method == "client_certificate":
        encoded = base64.b64encode(
            json.dumps(certificate, ensure_ascii=True).encode("utf-8")
        ).decode("ascii")
        lines.append(f"CERTIFICATE_CONFIG={encoded}")
    temporary_name = None
    try:
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", dir=target.parent, text=True
        )
        if os.name != "nt":
            os.chmod(temporary_name, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(lines) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, target)
    except Exception:
        if temporary_name:
            with suppress(FileNotFoundError):
                os.unlink(temporary_name)
        if new_reference:
            with suppress(Exception):
                keyring.delete_password(CERTIFICATE_SERVICE, new_reference)
        raise
    if previous_certificate and previous_certificate.get("password_ref"):
        prefix = _certificate_account(
            target, previous_values.get("CLIENT_ID"), previous_values.get("TENANT_ID")
        )
        reference = previous_certificate["password_ref"]
        if reference.startswith(prefix) and reference != new_reference:
            with suppress(Exception):
                keyring.delete_password(CERTIFICATE_SERVICE, reference)
    return target


__all__ = [
    "AUTH_METHODS",
    "CredentialStoreError",
    "has_stored_secret",
    "load_credentials",
    "load_public_configuration",
    "save_configuration",
]
