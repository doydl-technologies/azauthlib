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

"""Read certificates and sign assertions with Windows CNG keys."""

from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import re
import sys
import time
import uuid
from contextlib import contextmanager
from ctypes import wintypes
from functools import lru_cache

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from .certificates import MAX_CERTIFICATE_BYTES, CertificateError, certificate_metadata

_STORE_LOCATIONS = {"CurrentUser": 0x10000, "LocalMachine": 0x20000}
_SYSTEM_STORE_PROVIDER_W = 10
_OPEN_EXISTING_READ_ONLY = 0x4000 | 0x8000
_CERT_ENCODING = 0x00010001  # X509_ASN_ENCODING | PKCS_7_ASN_ENCODING
_FIND_SHA1_HASH = 0x10000
_ACQUIRE_CNG_SILENT = 0x40000 | 0x40 | 0x8 | 0x4  # CNG only, silent, no healing, compare key
_CNG_KEY_SPEC = 0xFFFFFFFF
_SIGN_PSS_SILENT = 0x8 | 0x40


class _CertContext(ctypes.Structure):
    _fields_ = [
        ("encoding", wintypes.DWORD),
        ("encoded", ctypes.c_void_p),
        ("size", wintypes.DWORD),
        ("info", ctypes.c_void_p),
        ("store", wintypes.HANDLE),
    ]


class _Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.c_void_p)]


class _PssPadding(ctypes.Structure):
    _fields_ = [("algorithm", wintypes.LPCWSTR), ("salt_size", wintypes.ULONG)]


@lru_cache(maxsize=1)
def _windows_apis():
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    cng = ctypes.WinDLL("ncrypt")
    ptr, dword, boolean = ctypes.c_void_p, wintypes.DWORD, wintypes.BOOL
    context = ctypes.POINTER(_CertContext)
    crypt.CertOpenStore.argtypes = [ptr, dword, ptr, dword, wintypes.LPCWSTR]
    crypt.CertOpenStore.restype = ptr
    crypt.CertCloseStore.argtypes = [ptr, dword]
    crypt.CertCloseStore.restype = boolean
    crypt.CertFindCertificateInStore.argtypes = [
        ptr,
        dword,
        dword,
        dword,
        ctypes.POINTER(_Blob),
        context,
    ]
    crypt.CertFindCertificateInStore.restype = context
    crypt.CertFreeCertificateContext.argtypes = [context]
    crypt.CertFreeCertificateContext.restype = boolean
    crypt.CryptAcquireCertificatePrivateKey.argtypes = [
        context,
        dword,
        ptr,
        ctypes.POINTER(ptr),
        ctypes.POINTER(dword),
        ctypes.POINTER(boolean),
    ]
    crypt.CryptAcquireCertificatePrivateKey.restype = boolean
    cng.NCryptSignHash.argtypes = [
        ptr,
        ctypes.POINTER(_PssPadding),
        ctypes.c_char_p,
        dword,
        ptr,
        dword,
        ctypes.POINTER(dword),
        dword,
    ]
    cng.NCryptSignHash.restype = wintypes.LONG
    cng.NCryptFreeObject.argtypes = [ptr]
    cng.NCryptFreeObject.restype = wintypes.LONG
    return crypt, cng


def require_windows():
    if sys.platform != "win32":
        raise CertificateError("Windows certificate store authentication requires Windows.")


def _selector(spec):
    require_windows()
    location = spec.get("store_location", "CurrentUser")
    if not isinstance(location, str) or location not in _STORE_LOCATIONS:
        raise CertificateError("Choose the Current User or Local Machine Personal store.")
    raw_thumbprint = spec.get("thumbprint")
    thumbprint = (
        re.sub(r"[\s\u200e\u200f]", "", raw_thumbprint) if isinstance(raw_thumbprint, str) else ""
    )
    if not re.fullmatch(r"[0-9a-fA-F]{40}", thumbprint):
        raise CertificateError("Enter the certificate's 40-digit Windows thumbprint.")
    return location, thumbprint.upper()


@contextmanager
def _open_certificate(spec, *, verify_fingerprint=True):
    location, thumbprint = _selector(spec)
    crypt, cng = _windows_apis()
    store = crypt.CertOpenStore(
        _SYSTEM_STORE_PROVIDER_W,
        0,
        None,
        _STORE_LOCATIONS[location] | _OPEN_EXISTING_READ_ONLY,
        "MY",
    )
    if not store:
        raise CertificateError(f"Cannot open the {location} Windows Personal certificate store.")
    try:
        thumbprint_buffer = ctypes.create_string_buffer(bytes.fromhex(thumbprint), 20)
        blob = _Blob(20, ctypes.addressof(thumbprint_buffer))
        context = crypt.CertFindCertificateInStore(
            store, _CERT_ENCODING, 0, _FIND_SHA1_HASH, ctypes.byref(blob), None
        )
        if not context:
            raise CertificateError(f"Certificate not found in the {location} Personal store.")
        try:
            encoded = context.contents
            if not encoded.encoded or not 0 < encoded.size <= MAX_CERTIFICATE_BYTES:
                raise CertificateError("Invalid certificate data in the Windows store.")
            der = ctypes.string_at(encoded.encoded, encoded.size)
            try:
                certificate = x509.load_der_x509_certificate(der)
            except ValueError:
                raise CertificateError("Cannot read the selected Windows certificate.") from None
            metadata = certificate_metadata(certificate)
            if verify_fingerprint and spec.get("fingerprint") not in (
                None,
                "",
                metadata["fingerprint"],
            ):
                raise CertificateError("The Windows certificate has changed. Validate it again.")
            yield (
                certificate,
                {
                    "format": "windows_store",
                    "store_location": location,
                    "thumbprint": thumbprint,
                    **metadata,
                },
                crypt,
                cng,
                context,
            )
        finally:
            crypt.CertFreeCertificateContext(context)
    finally:
        crypt.CertCloseStore(store, 0)


@contextmanager
def _open_signing_key(spec, *, verify_fingerprint=True):
    with _open_certificate(spec, verify_fingerprint=verify_fingerprint) as (
        certificate,
        public,
        crypt,
        cng,
        context,
    ):
        handle, key_spec, caller_free = ctypes.c_void_p(), wintypes.DWORD(), wintypes.BOOL()
        if not crypt.CryptAcquireCertificatePrivateKey(
            context,
            _ACQUIRE_CNG_SILENT,
            None,
            ctypes.byref(handle),
            ctypes.byref(key_spec),
            ctypes.byref(caller_free),
        ):
            raise CertificateError(
                "Cannot access the certificate's CNG private key. Check that the key "
                "exists and that this Windows account can use it without a prompt."
            )
        # Keep the certificate context alive even when it owns the key handle.
        try:
            if key_spec.value != _CNG_KEY_SPEC:
                raise CertificateError("The certificate must use a Windows CNG private key.")
            yield certificate, public, cng, handle
        finally:
            if caller_free.value:
                cng.NCryptFreeObject(handle)


def store_certificate_identity(spec):
    """Read the public fingerprint for connection-test history without using the key."""
    with _open_certificate(spec) as (_, public, _, _, _):
        return [public["fingerprint"]]


def _sign(cng, handle, certificate, data):
    public_key = certificate.public_key()
    sha256 = hashes.SHA256()
    pss = _PssPadding("SHA256", sha256.digest_size)
    digest = hashlib.sha256(data).digest()
    signature_size = (public_key.key_size + 7) // 8
    signature = ctypes.create_string_buffer(signature_size)
    written = wintypes.DWORD()
    status = cng.NCryptSignHash(
        handle,
        ctypes.byref(pss),
        digest,
        len(digest),
        signature,
        signature_size,
        ctypes.byref(written),
        _SIGN_PSS_SILENT,
    )
    if status or written.value != signature_size:
        raise CertificateError(
            "Windows could not sign with this key. Use a CNG RSA key that supports RSA-PSS."
        )
    try:
        public_key.verify(
            signature.raw, data, padding.PSS(mgf=padding.MGF1(sha256), salt_length=32), sha256
        )
    except InvalidSignature:
        raise CertificateError("The Windows private key does not match the certificate.") from None
    return signature.raw


def validate_store_certificate(spec, *, verify_fingerprint=True):
    with _open_signing_key(spec, verify_fingerprint=verify_fingerprint) as (
        certificate,
        public,
        cng,
        handle,
    ):
        _sign(cng, handle, certificate, b"azauthlib Windows certificate validation")
    return public


def _base64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def sign_client_assertion(spec, client_id, audience):
    """Create a fresh Microsoft Entra PS256 client assertion using the OS key."""
    with _open_signing_key(spec) as (certificate, public, cng, handle):
        now = int(time.time())
        header = {
            "alg": "PS256",
            "typ": "JWT",
            "x5t#S256": _base64url(bytes.fromhex(public["fingerprint"])).decode("ascii"),
        }
        claims = {
            "aud": audience,
            "iss": client_id,
            "sub": client_id,
            "iat": now,
            "nbf": now,
            "exp": now + 300,
            "jti": str(uuid.uuid4()),
        }
        payload = b".".join(
            _base64url(json.dumps(part, separators=(",", ":")).encode("utf-8"))
            for part in (header, claims)
        )
        signature = _sign(cng, handle, certificate, payload)
    return (payload + b"." + _base64url(signature)).decode("ascii")
