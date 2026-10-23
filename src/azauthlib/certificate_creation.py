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

"""Password-protected self-signed credentials, created only on explicit request."""

from __future__ import annotations

import hmac
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from .certificates import CertificateError


class CertificateCreationCancelled(CertificateError):
    pass


def validate_creation(name, format, days, password, confirmation, output_folder):
    """Validate fields without filesystem, keyring, key generation, or network I/O."""
    errors = {}
    name = name.strip()
    if (
        not name
        or len(name.encode("utf-8")) > 64
        or any(ord(c) < 32 or ord(c) == 127 for c in name)
    ):
        errors["name"] = "Use a certificate name of 1-64 UTF-8 bytes without control characters."
    if format not in ("pfx", "pem"):
        errors["format"] = "Choose PFX/P12 or PEM."
    now = datetime.now(timezone.utc)
    maximum = (datetime.max.replace(tzinfo=timezone.utc) - now).days
    text = str(days).strip()
    expires = None
    if not text.isascii() or not text.isdecimal() or len(text) > 7 or not 1 <= int(text) <= maximum:
        errors["days"] = f"Enter a whole number from 1 to {maximum} days."
    else:
        expires = (now + timedelta(days=int(text))).isoformat(timespec="seconds")
    if (
        not password.strip()
        or not 4 <= len(password) <= 511
        or len(password.encode("utf-8")) > 511
        or any(c in password for c in "\x00\r\n")
    ):
        errors["password"] = "Use 4-511 characters and at most 511 UTF-8 bytes."  # nosec B105 # noqa: S105 -- validation message
    if not hmac.compare_digest(password.encode("utf-8"), confirmation.encode("utf-8")):
        errors["confirmation"] = "The passwords do not match."
    try:
        folder = Path(output_folder).expanduser()
        if (
            not output_folder.strip()
            or not folder.is_absolute()
            or any(c in output_folder for c in "\x00\r\n")
        ):
            raise ValueError
    except (TypeError, ValueError):
        errors["folder"] = "Choose an absolute output-folder path."
    return {**errors, "valid": not errors, "expires": expires or ""}


def _protect_windows_directory(path):
    """Protect the new folder before writing keys, including on Python <3.13."""
    import ctypes
    from ctypes import wintypes

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    convert = advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW
    convert.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
    ]
    convert.restype = wintypes.BOOL
    apply = advapi.SetFileSecurityW
    apply.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
    apply.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    descriptor = ctypes.c_void_p()
    # Protected DACL: owner, SYSTEM and administrators only; inherit to children.
    sddl = "D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)"
    if not convert(sddl, 1, ctypes.byref(descriptor), None):
        raise OSError("Unable to prepare private folder permissions")
    try:
        if not apply(str(path), 0x80000004, descriptor):
            raise OSError("Unable to apply private folder permissions")
    finally:
        kernel.LocalFree(descriptor)


def create_certificate(
    *, name, format="pfx", days="90", password, confirmation, output_folder, cancel=None
):
    """Generate RSA-3072/SHA-256 and export only encrypted private-key files.

    Never overwrites a file or imports into OS certificate stores. On cancellation
    or failure, roll back only files exclusively created by this invocation.
    """
    validation = validate_creation(name, format, days, password, confirmation, str(output_folder))
    if not validation["valid"]:
        raise CertificateError("Correct the certificate creation fields before continuing.")

    def check_cancel():
        if cancel is not None and cancel.is_set():
            raise CertificateCreationCancelled("Certificate creation cancelled.")

    folder = None
    created = []
    try:
        check_cancel()
        key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        check_cancel()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name.strip())])
        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=int(str(days).strip())))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(key, hashes.SHA256())
        )
        encryption = serialization.BestAvailableEncryption(password.encode("utf-8"))
        if format == "pfx":
            private = pkcs12.serialize_key_and_certificates(
                name.strip().encode("utf-8"), key, certificate, None, encryption
            )
        else:
            private = key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, encryption
            )
        check_cancel()
        parent = Path(output_folder).expanduser().resolve()
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        folder = Path(tempfile.mkdtemp(prefix="certificate-", dir=parent))
        if os.name == "nt":
            _protect_windows_directory(folder)
        else:
            folder.chmod(0o700)

        def write(filename, data):
            check_cancel()
            path = folder / filename
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created.append(path)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            return str(path)

        private_path = write(
            "azauthlib.private.pfx" if format == "pfx" else "azauthlib.private.pem", private
        )
        public_pem = write(
            "azauthlib.public.pem", certificate.public_bytes(serialization.Encoding.PEM)
        )
        public_cer = write(
            "azauthlib.public.cer", certificate.public_bytes(serialization.Encoding.DER)
        )
        check_cancel()
        return {
            "format": format,
            "key_path": private_path,
            "certificate_path": public_pem if format == "pem" else "",
            "public_pem": public_pem,
            "public_cer": public_cer,
            "folder": str(folder),
            "days": int(str(days).strip()),
            "not_after": certificate.not_valid_after_utc.isoformat(),
        }
    except Exception as exc:
        cleanup_failed = False
        for path in reversed(created):
            try:
                path.unlink()
            except OSError:
                cleanup_failed = True
        if folder is not None and not cleanup_failed:
            try:
                folder.rmdir()
            except OSError:
                cleanup_failed = True
        if cleanup_failed:
            raise CertificateError(
                "Creation did not finish. Check the protected output folder for partial files: "
                f"{folder}"
            ) from None
        if isinstance(exc, CertificateCreationCancelled):
            raise
        raise CertificateError(
            "Certificate creation failed. Check the output location and its permissions, "
            "then try again."
        ) from None
