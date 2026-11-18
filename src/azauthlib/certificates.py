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

"""Local certificate imports. Private material stays in memory, never in configuration."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12

MAX_CERTIFICATE_BYTES = 4 * 1024 * 1024
CERTIFICATE_FORMATS = ("pfx", "pem", "windows_store")


class CertificateError(ValueError):
    """A safe, user-facing import error (never include parser exception text)."""


def read_certificate_file(path):
    try:
        source = Path(path).expanduser()
        if not source.is_file():
            raise CertificateError("Choose an existing, readable local certificate/key file.")
        with source.open("rb") as stream:
            data = stream.read(MAX_CERTIFICATE_BYTES + 1)
        if not data or len(data) > MAX_CERTIFICATE_BYTES:
            raise CertificateError("Certificate/key files must be nonempty and at most 4 MiB.")
        return data
    except (OSError, TypeError, ValueError) as exc:
        if isinstance(exc, CertificateError):
            raise
        raise CertificateError("Unable to read the selected certificate/key file.") from None


def file_identity(spec):
    """Hash actual files, not just paths, to detect replacement and rotation."""
    paths = [spec.get("key_path", "")]
    if spec.get("format") == "pem":
        paths.append(spec.get("certificate_path", ""))
    return [hashlib.sha256(read_certificate_file(path)).hexdigest() for path in paths]


def certificate_identity(spec):
    """Identify the current certificate source for connection-test history."""
    if spec.get("format") == "windows_store":
        from .windows_certificates import store_certificate_identity

        return store_certificate_identity(spec)
    return file_identity(spec)


@dataclass(repr=False)
class ImportedCertificate:
    public: dict
    credential: dict = field(repr=False)
    identity: list[str] = field(repr=False)


def import_certificate(spec, password=None, *, verify_fingerprint=True):
    """Validate a certificate source and return public metadata and its identity.

    The unencrypted key is serialized only in memory. No subprocesses, temporary
    key files, store writes, or network access are involved.
    """
    if not isinstance(spec, dict) or spec.get("format") not in CERTIFICATE_FORMATS:
        raise CertificateError("Choose PFX/P12, PEM, or Windows certificate store.")
    if spec["format"] == "windows_store":
        from .windows_certificates import validate_store_certificate

        if password:
            raise CertificateError("Windows manages access to this key; omit the file password.")
        public = validate_store_certificate(spec, verify_fingerprint=verify_fingerprint)
        return ImportedCertificate(public, {}, [public["fingerprint"]])
    data = read_certificate_file(spec.get("key_path", ""))
    identities = [hashlib.sha256(data).hexdigest()]
    encoded_password = password.encode("utf-8") if password else None
    try:
        if spec["format"] == "pfx":
            key, certificate, _chain = pkcs12.load_key_and_certificates(data, encoded_password)
        else:
            cert_data = read_certificate_file(spec.get("certificate_path", ""))
            identities.append(hashlib.sha256(cert_data).hexdigest())
            # Supplying a password for an unencrypted key is an input mistake.
            key = serialization.load_pem_private_key(data, password=encoded_password)
            certificate = (
                x509.load_pem_x509_certificate(cert_data)
                if b"-----BEGIN CERTIFICATE-----" in cert_data
                else x509.load_der_x509_certificate(cert_data)
            )
    except CertificateError:
        raise
    except Exception:
        raise CertificateError(
            "Cannot unlock or parse these files. Check the format, private-key file and password."
        ) from None
    if key is None or certificate is None:
        raise CertificateError(
            "A certificate and its private key are required; a public CER alone is insufficient."
        )
    if not isinstance(key, rsa.RSAPrivateKey) or key.key_size < 2048:
        raise CertificateError("Use an RSA private key of at least 2048 bits for Microsoft Entra.")
    encoding = serialization.Encoding.DER
    public_format = serialization.PublicFormat.SubjectPublicKeyInfo
    if key.public_key().public_bytes(
        encoding, public_format
    ) != certificate.public_key().public_bytes(encoding, public_format):
        raise CertificateError("The private key does not match the selected public certificate.")
    metadata = certificate_metadata(certificate)
    if (
        verify_fingerprint
        and spec.get("fingerprint")
        and spec["fingerprint"] != metadata["fingerprint"]
    ):
        raise CertificateError(
            "The certificate file has changed. Edit and validate this connection again."
        )
    public = {
        "format": spec["format"],
        "key_path": str(Path(spec["key_path"]).expanduser().resolve()),
        "certificate_path": str(Path(spec["certificate_path"]).expanduser().resolve())
        if spec["format"] == "pem"
        else "",
        **metadata,
    }
    credential = {
        "private_key": key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode("ascii"),
        # MSAL >=1.35 derives SHA-256 automatically; do not supply SHA-1 thumbprint.
        "public_certificate": certificate.public_bytes(serialization.Encoding.PEM).decode("ascii"),
    }
    return ImportedCertificate(public, credential, identities)


def certificate_metadata(certificate):
    key = certificate.public_key()
    if not isinstance(key, rsa.RSAPublicKey) or key.key_size < 2048:
        raise CertificateError("Use an RSA private key of at least 2048 bits for Microsoft Entra.")
    now = datetime.now(timezone.utc)
    if now < certificate.not_valid_before_utc:
        raise CertificateError(
            "This certificate is not valid yet. Check its start date and your clock."
        )
    if now >= certificate.not_valid_after_utc:
        raise CertificateError("This certificate has expired. Import a renewed certificate.")
    try:
        if not certificate.extensions.get_extension_for_class(
            x509.KeyUsage
        ).value.digital_signature:
            raise CertificateError("This certificate does not allow digital signatures.")
    except x509.ExtensionNotFound:
        pass
    return {
        "fingerprint": certificate.fingerprint(hashes.SHA256()).hex().upper(),
        "subject": certificate.subject.rfc4514_string(),
        "not_after": certificate.not_valid_after_utc.isoformat(),
    }


def create_certificate_client(factory, spec, password, **options):
    """Supply MSAL with either a file credential or a fresh Windows-signed assertion."""
    if not spec or spec.get("format") != "windows_store":
        return factory(client_credential=import_certificate(spec, password).credential, **options)

    from .windows_certificates import require_windows, sign_client_assertion

    require_windows()
    if password:
        raise CertificateError("Windows manages access to this key; omit the file password.")

    # Bind the assertion to the token endpoint discovered by MSAL, including tenant aliases.
    def assertion():
        return sign_client_assertion(spec, options["client_id"], app.authority.token_endpoint)

    # A no-argument callback cannot switch audiences for regional token requests.
    app = factory(client_credential={"client_assertion": assertion}, azure_region=False, **options)
    return app
